"""CSV data source utilities."""

from __future__ import annotations

from pathlib import Path
from typing import Any, Callable, Dict, Optional, Union

import pandas as pd

from services.utils.logger import logger

_DATA_CACHE: Dict[str, pd.DataFrame] = {}


class CSVDataSource:
    """CSV-based data source implementing the DataSource protocol.

    Loads OHLCV data from a local CSV file and slices it by bar position
    range to match the ``DataSource.fetch_data`` interface expected by
    ``prepare_ohlcvs_dataset()`` and other research-pipeline utilities.

    The CSV may contain any mix of date/time columns; the loader auto-detects
    the first datetime-like column and uses it as the index. Remaining columns
    are matched case-insensitively to OHLCV names.

    Example::

        source = CSVDataSource("eurusd_h1.csv")
        df = source.fetch_data("EURUSD", "H1", start_pos=0, end_pos=500)
    """

    _DATETIME_HINTS = ("date", "time", "timestamp", "datetime", "ts")
    _COLUMN_MAP = {
        "open": "open",
        "high": "high",
        "low": "low",
        "close": "close",
        "volume": "volume",
        "tick_volume": "volume",
        "tickvolume": "volume",
        "spread": "spread",
    }

    def __init__(
        self,
        filepath: Union[str, Path],
        *,
        date_column: Optional[str] = None,
        cache: bool = True,
        **read_csv_kwargs: Any,
    ) -> None:
        """Initialize the CSV data source.

        Args:
            filepath: Path to the CSV file.
            date_column: Name of the date/time column. If ``None``, the first
                column whose name is in ``_DATETIME_HINTS`` is used.
            cache: Whether to cache the loaded DataFrame in memory.
            **read_csv_kwargs: Extra keyword arguments forwarded to
                ``pd.read_csv()`` (e.g. ``sep``, ``parse_dates``).
        """
        self._filepath = Path(filepath)
        self._date_column = date_column
        self._cache = cache
        self._read_csv_kwargs = read_csv_kwargs
        self._loaded: Optional[pd.DataFrame] = None

    def _detect_date_column(self, columns: list[str]) -> Optional[str]:
        """Return the first column name that looks like a datetime field."""
        hints = set(self._DATETIME_HINTS)
        for col in columns:
            if col.lower() in hints:
                return col
        return None

    def _load(self) -> pd.DataFrame:
        """Load and normalize the CSV into a DataFrame with DatetimeIndex."""
        if not self._filepath.exists():
            raise FileNotFoundError(f"CSV file not found: {self._filepath}")

        kwargs: Dict[str, Any] = dict(self._read_csv_kwargs)
        df = pd.read_csv(self._filepath, **kwargs)

        if df.empty:
            raise ValueError(f"CSV file is empty: {self._filepath}")

        # Normalize column names for detection
        df.columns = [str(c).strip().lower() for c in df.columns]

        # Resolve date column
        date_col = self._date_column
        if date_col is not None:
            date_col = date_col.lower()
        else:
            date_col = self._detect_date_column(list(df.columns))

        if date_col is None:
            raise ValueError(
                f"No date/time column detected in {self._filepath}. "
                f"Provide one via date_column= or ensure a column named "
                f"{'/'.join(self._DATETIME_HINTS)} exists."
            )

        df[date_col] = pd.to_datetime(df[date_col])
        df = df.set_index(date_col).sort_index()

        # Rename OHLCV columns to canonical lowercase
        rename_map: Dict[str, str] = {}
        for col in df.columns:
            canonical = self._COLUMN_MAP.get(col.lower())
            if canonical is not None:
                rename_map[col] = canonical

        if rename_map:
            df = df.rename(columns=rename_map)

        # Ensure numeric columns
        numeric_cols = {"open", "high", "low", "close", "volume", "spread"}
        for col in set(df.columns) & numeric_cols:
            df[col] = pd.to_numeric(df[col], errors="coerce")

        return df

    def _get_cached_or_load(self) -> pd.DataFrame:
        """Load from cache or disk."""
        if self._loaded is not None:
            return self._loaded

        if self._cache:
            key = f"csv:{self._filepath.resolve()}"
            if key in _DATA_CACHE:
                return _DATA_CACHE[key].copy()

        df = self._load()

        if self._cache:
            key = f"csv:{self._filepath.resolve()}"
            _DATA_CACHE[key] = df

        self._loaded = df
        return df.copy()

    # -- DataSource protocol -------------------------------------------------

    def fetch_data(
        self,
        symbol: str,
        timeframe: str,
        start_pos: int,
        end_pos: int,
    ) -> Optional[pd.DataFrame]:
        """Fetch OHLCV data sliced to the requested bar-position range.

        Args:
            symbol: Trading symbol (used for logging; data comes from CSV).
            timeframe: Timeframe string (used for logging).
            start_pos: Start bar index (inclusive).
            end_pos: End bar index (exclusive).

        Returns:
            DataFrame with OHLCV columns and DatetimeIndex, sliced to the
            requested position range. Returns ``None`` if the range is invalid.
        """
        logger.info(
            f"CSVDataSource: loading {symbol} {timeframe} "
            f"from {self._filepath} (bars {start_pos}-{end_pos})"
        )

        df = self._get_cached_or_load()

        if start_pos < 0 or end_pos > len(df) or start_pos >= end_pos:
            logger.warning(
                f"CSVDataSource: invalid position range [{start_pos}:{end_pos}] "
                f"for data with {len(df)} rows"
            )
            return None

        sliced = df.iloc[start_pos:end_pos]

        logger.info(
            f"CSVDataSource: returning {len(sliced)} bars for {symbol} "
            f"({sliced.index[0]} to {sliced.index[-1]})"
        )
        return sliced

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
