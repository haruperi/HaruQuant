"""
Timeframe Management - OHLCV Resampling and Multi-Timeframe Resolution.

This module provides comprehensive timeframe management functionality including:
- OHLCV data resampling between timeframes (M1→M5→H1→D1)
- Multi-timeframe resolution and conversion
- Aggregated bar generation for live trading
- Timeframe validation and utilities
"""

from datetime import datetime, timedelta
from pathlib import Path
from typing import Callable, Dict, Optional, Union, cast

import pandas as pd

from apps.logger import logger
from apps.utils.data_validator import DataValidator

# Cache for loaded data to avoid repeated reads
_DATA_CACHE: Dict[str, pd.DataFrame] = {}


def clear_data_cache() -> None:
    """Clear the data cache."""
    global _DATA_CACHE
    _DATA_CACHE.clear()
    logger.info("Data cache cleared")


def get_cached_data(key: str, loader_func: Callable[[], pd.DataFrame]) -> pd.DataFrame:
    """
    Get data from cache or load it using the provided loader function.

    Args:
        key: Unique cache key
        loader_func: Function that returns a DataFrame if data is not in cache

    Returns:
        The loaded DataFrame
    """
    if key in _DATA_CACHE:
        logger.debug(f"Cache hit for {key}")
        return _DATA_CACHE[key].copy()  # Return copy to prevent mutation of cached data

    logger.debug(f"Cache miss for {key}, loading data...")
    data = loader_func()
    _DATA_CACHE[key] = data
    return data.copy()


def get_data_dir() -> Path:
    """Get path to data directory.

    Returns:
        Path to data directory (project_root/data)

    Example:
        >>> data_dir = get_data_dir()
        >>> print(data_dir / "dukascopy")
    """
    return Path(__file__).resolve().parents[2] / "data"


def load_parquet(file_path: Union[str, Path]) -> pd.DataFrame:
    """
    Load parquet file with caching.

    Args:
        file_path: Path to parquet file

    Returns:
        Loaded DataFrame
    """
    path = Path(file_path)
    if not path.exists():
        raise FileNotFoundError(f"File not found: {path}")

    # Use absolute path as cache key to avoid ambiguity
    key = str(path.resolve())

    def _loader():
        return pd.read_parquet(path)

    return get_cached_data(key, _loader)


def load_dukascopy(  # noqa: C901
    symbol: str,
    timeframe: Optional[str] = "H1",
    start_date: Optional[str] = None,
    end_date: Optional[str] = None,
    count: Optional[int] = None,
    cache: bool = True,
) -> pd.DataFrame:
    """Download Dukascopy data from Dukascopy API.

    Args:
        symbol: Trading symbol (e.g., 'EURUSD')
        start_date: Start date string (YYYY-MM-DD)
        end_date: End date string (YYYY-MM-DD)
        timeframe: Timeframe string (default: 'H1')
        count: Number of bars to retrieve (alternative to date range)
        cache: Whether to cache loaded data in memory

    Returns:
        DataFrame with prepared backtest data

    Raises:
        FileNotFoundError: If data file not found
    """
    from apps.dukascopy import INTERVAL_MIN_1, OFFER_SIDE_BID, fetch

    logger.info(f"Attempting to download {symbol} from Dukascopy...")

    # Handle count-based retrieval
    if count is not None:
        # Estimate date range based on count
        # Rough estimate: 1 bar per minute for M1, adjust for other timeframes
        e_date = datetime.now()
        # Estimate days needed (assuming ~1440 M1 bars per day)
        days_needed = max(int(count / 1440) + 30, 365)  # Add buffer
        s_date = e_date - timedelta(days=days_needed)
        logger.info(
            f"Count mode: fetching {count} bars, estimated date range: {s_date.date()} to {e_date.date()}"
        )
    else:
        # Ensure start_date is provided for download
        if not start_date:
            # Default to 1 year ago if not specified
            s_date = datetime.now() - timedelta(days=365)
            logger.info(
                f"No start_date provided. Defaulting to 1 year ago: {s_date.date()}"
            )
        else:
            s_date = datetime.strptime(start_date, "%Y-%m-%d")

        if not end_date:
            e_date = datetime.now()
        else:
            e_date = datetime.strptime(end_date, "%Y-%m-%d")

    # Format symbol for Dukascopy (e.g. EURUSD -> EUR/USD)
    # Simple heuristic: if len is 6 and no slash, insert slash in middle
    # Only if it looks like a currency pair
    dukas_symbol = symbol
    if len(symbol) == 6 and "/" not in symbol:
        dukas_symbol = f"{symbol[:3]}/{symbol[3:]}"

    logger.info(f"Downloading {dukas_symbol} from {s_date} to {e_date}...")

    def _load() -> pd.DataFrame:
        try:
            # Fetch data (M1 Bid)
            df = fetch(
                instrument=dukas_symbol,
                interval=INTERVAL_MIN_1,  # Defaulting to M1 for now based on signature default
                offer_side=OFFER_SIDE_BID,
                start=s_date,
                end=e_date,
            )

            if df.empty:
                raise ValueError(f"No data returned from Dukascopy for {dukas_symbol}")

            # Adjust timezone to UTC+2 with DST (Eastern European Time)
            # 'Europe/Athens' follows EET/EEST (UTC+2 / UTC+3)
            try:
                # Ensure index is timezone-aware (fetch returns UTC)
                dt_index = cast(pd.DatetimeIndex, df.index)
                if dt_index.tz is None:
                    dt_index = dt_index.tz_localize("UTC")

                # Convert and then remove timezone info
                df.index = dt_index.tz_convert("Europe/Athens").tz_localize(None)

                logger.debug("Converted data to Europe/Athens time (EET/EEST)")
            except Exception as e:
                logger.error(f"Failed to convert timezone: {e}")
                # Continue with original time if conversion fails (or raise?)
                # For consistency with user request, we should probably warn strongly or fail.

            # If count was specified, take only the last N bars
            if count is not None:
                df = df.tail(count)
                logger.info(f"Trimmed to last {count} bars")

            # Use the dataframe we just downloaded
            return DataValidator.prepare_data(df)

        except Exception as e:
            logger.error(f"Failed to download Dukascopy data: {e}")
            raise FileNotFoundError(f"Dukascopy data for {symbol} download failed: {e}")

    if cache:
        cache_key = (
            f"dukascopy:{dukas_symbol}:{timeframe}:"
            f"{s_date.isoformat()}:{e_date.isoformat()}:{count}"
        )
        return get_cached_data(cache_key, _load)

    return _load()


def load_mt5(  # noqa: C901
    symbol: str,
    timeframe: str = "H1",
    start_date: Optional[Union[str, datetime]] = None,
    end_date: Optional[Union[str, datetime]] = None,
    count: Optional[int] = 0,
    user_id: int = 1,  # Default to admin user
    mt5_login: Optional[int] = None,
) -> Optional[pd.DataFrame]:
    """Load data from MT5 connection.

    Requires MT5 connection configuration in settings/config.ini or database.
    Falls back to Dukascopy data if MT5 connection fails.

    Args:
        symbol: Trading symbol (e.g., 'EURUSD')
        timeframe: MT5 timeframe ('M1', 'M5', 'M15', 'M30', 'H1', 'H4', 'D1')
        count: Number of bars (if dates not specified)
        start_date: Start date (datetime object or string 'YYYY-MM-DD')
        end_date: End date (datetime object or string 'YYYY-MM-DD')
        user_id: User ID to fetch credentials for (default=1)
        mt5_login: Optional specific MT5 account login to use

    Returns:
        DataFrame ready for backtesting
    """
    try:
        from apps.mt5.client import MT5Client
        from apps.sqlite.users import UserManager

        # Convert string dates to datetime objects if needed
        if isinstance(start_date, str):
            start_date = datetime.strptime(start_date, "%Y-%m-%d")
        if isinstance(end_date, str):
            end_date = datetime.strptime(end_date, "%Y-%m-%d")
        if start_date and not end_date:
            end_date = datetime.now()

        creds = None
        user_manager = UserManager()
        if mt5_login:
            creds = user_manager.get_mt5_credentials_by_login(user_id, mt5_login)
        else:
            creds = user_manager.get_mt5_credentials(user_id=user_id)

        if not creds:
            raise ValueError("No MT5 credentials available")

        # Connect
        logger.info(
            f"Connecting to MT5 for user {user_id} (account: {creds.get('login')})..."
        )
        client = MT5Client()

        if not client.connect(
            creds["path"], creds["login"], creds["password"], creds["server"]
        ):
            logger.error(
                "Failed to connect to MT5. Please ensure MT5 terminal is running."
            )
            client.shutdown()
            return None

        # Fetch data
        logger.info(
            f"Fetching {symbol} {timeframe} data from MT5... from {start_date} to {end_date} or last {count} bars"
        )
        if start_date and end_date:
            bars = client.get_bars(
                symbol=symbol,
                timeframe=timeframe,
                date_from=start_date,
                date_to=end_date,
            )
        else:
            effective_count = count if count and count > 0 else 1000
            bars = client.get_bars(
                symbol=symbol, timeframe=timeframe, count=effective_count
            )

        client.shutdown()

        # Check if data was retrieved
        if bars is None:
            logger.error(f"No data retrieved from MT5 for {symbol}")
            return None

        # Convert to DataFrame if it's a list
        if isinstance(bars, list):
            bars = pd.DataFrame(bars)

        if bars.empty:
            logger.error(f"No data retrieved from MT5 for {symbol}")
            return None

        logger.success(f"Loaded {len(bars):,} bars from MT5")

        return DataValidator.prepare_data(bars)

    except Exception as e:
        logger.warning(f"MT5 connection failed: {e}")
        logger.info("Falling back to Dukascopy data...")

        # Fallback to Dukascopy
        # Convert datetime to string for load_dukascopy
        def to_datestr(dt):
            if isinstance(dt, datetime):
                return dt.strftime("%Y-%m-%d")
            elif isinstance(dt, str):
                return dt  # assume already in correct format
            return None

        start_str = to_datestr(start_date)
        end_str = to_datestr(end_date)

        if not start_str and not end_str and (not count or count <= 0):
            end_str = datetime.now().strftime("%Y-%m-%d")
            start_str = (datetime.now() - timedelta(days=30)).strftime("%Y-%m-%d")

        duka_data = load_dukascopy(
            symbol=symbol,
            start_date=start_str,
            end_date=end_str,
            count=count if count and count > 0 else None,
            timeframe="M1",
        )

        if timeframe and timeframe.upper() != "M1":
            from apps.utils.data_manipulator import TimeframeManager

            manager = TimeframeManager()
            resampled = manager.resample(
                duka_data, target_timeframe=timeframe, source_timeframe="M1"
            )
            return DataValidator.prepare_data(resampled)

        return duka_data


def main() -> None:
    """Run example testing script."""
    # df = load_parquet("data/dukascopy/AUDJPY.parquet")
    df = load_mt5(
        "GBPUSD",
        timeframe="M1",
        start_date=datetime(2025, 1, 1),
        end_date=datetime(2025, 10, 31),
    )
    # df = load_dukascopy("GBPUSD", start_date="2025-01-01", end_date="2025-10-31")
    print(df)


if __name__ == "__main__":
    main()
