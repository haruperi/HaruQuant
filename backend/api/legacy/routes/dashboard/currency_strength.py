"""Currency Strength API Routes.

Provides real-time multi-timeframe currency strength analysis from MT5 market data.
Optimized for short-term trading with M5, H1, and H4 timeframes.
Parallel fetching for improved performance.
"""

from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime
from typing import Annotated, Any, Dict, List, Optional

import pandas as pd
from fastapi import APIRouter, Header, HTTPException, status
from pydantic import BaseModel, Field

from backend.api.legacy.auth_utils import verify_token
from backend.api.legacy.routes.dashboard.broker import client as global_mt5_client
from backend.api.legacy.routes.dashboard.broker import get_last_credentials
from apps.indicator.custom import (
    CURRENCY_PAIRS,
    MAJOR_CURRENCIES,
    currency_strength_indicator,
)
from backend.common.logger import logger
from apps.sqlite.database_operations import DatabaseManager

router = APIRouter()
db_manager = DatabaseManager()


class CurrencyStrengthResponse(BaseModel):
    """Response model for individual currency strength."""

    currency: str = Field(..., description="Currency code (e.g., EUR, USD)")
    strength: float = Field(..., description="Strength score (-100 to +100)")
    rank: int = Field(..., description="Ranking (1 = strongest)")
    trend: str = Field(..., description="Trend classification")
    confidence: int = Field(..., description="Confidence level (0-100)")
    updated_at: str = Field(..., description="Last update timestamp")


class CurrencyPairSignalResponse(BaseModel):
    """Response model for currency pair trading signal."""

    pair: str = Field(..., description="Currency pair (e.g., EURUSD)")
    base: str = Field(..., description="Base currency")
    quote: str = Field(..., description="Quote currency")
    base_strength: float = Field(..., description="Base currency strength")
    quote_strength: float = Field(..., description="Quote currency strength")
    pair_strength: float = Field(..., description="Combined pair strength")
    recommendation: str = Field(..., description="Trading recommendation")
    tf1_change: Optional[float] = Field(None, description="Timeframe 1 change %")
    tf2_change: Optional[float] = Field(None, description="Timeframe 2 change %")
    tf3_change: Optional[float] = Field(None, description="Timeframe 3 change %")


class CurrencyStrengthDataResponse(BaseModel):
    """Complete currency strength analysis response."""

    currencies: List[CurrencyStrengthResponse]
    strong_pairs: List[CurrencyPairSignalResponse]
    weak_pairs: List[CurrencyPairSignalResponse]
    last_updated: str
    tf1_label: str = Field(..., description="Label for timeframe 1")
    tf2_label: str = Field(..., description="Label for timeframe 2")
    tf3_label: str = Field(..., description="Label for timeframe 3")


def _classify_trend(strength: float) -> str:
    """Classify currency strength into trend categories.

    Args:
        strength: Strength value (percentage)

    Returns:
        Trend classification string
    """
    if strength > 0.5:
        return "strong_buy"
    elif strength > 0.2:
        return "buy"
    elif strength < -0.5:
        return "strong_sell"
    elif strength < -0.2:
        return "sell"
    else:
        return "neutral"


def _calculate_confidence(pair_count: int, total_pairs: int = 28) -> int:
    """Calculate confidence level based on data availability.

    Args:
        pair_count: Number of pairs successfully fetched with all timeframes
        total_pairs: Total number of currency pairs

    Returns:
        Confidence percentage (0-100)
    """
    # Base confidence on data coverage
    # Higher confidence now since we're using proper multi-timeframe alignment
    coverage = (pair_count / total_pairs) * 100
    # Cap at 95% to account for potential data quality issues
    return min(int(coverage * 0.95), 95)


def _calculate_percentage_change(data: Any) -> Optional[float]:
    """Calculate percentage change from first to last close price.

    Args:
        data: DataFrame with OHLCV data

    Returns:
        Percentage change, or None if insufficient data
    """
    if data is None or data.empty or len(data) < 2:
        return None

    try:
        first_close = float(data.iloc[0]["close"])
        last_close = float(data.iloc[-1]["close"])

        if first_close == 0:
            return None

        return ((last_close - first_close) / first_close) * 100
    except (KeyError, IndexError, ValueError, ZeroDivisionError):
        return None


def _ensure_mt5_connection() -> None:
    """Ensure MT5 client is connected, auto-reconnect if needed."""
    if not global_mt5_client.is_connected():
        logger.warning("MT5 client not connected. Attempting auto-reconnect...")
        last_creds = get_last_credentials()

        if not (
            last_creds.get("login")
            and last_creds.get("password")
            and last_creds.get("server")
        ):
            logger.error(
                "MT5 client not connected and no credentials available for auto-reconnect"
            )
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail="MT5 terminal not connected. Please visit the broker page to connect.",
            )

        try:
            logger.info(
                f"Auto-reconnecting to MT5 (server: {last_creds['server']}, login: {last_creds['login']})"
            )
            global_mt5_client.connect(
                path=last_creds.get("path", ""),
                login=last_creds["login"],
                password=last_creds["password"],
                server=last_creds["server"],
            )

            if not global_mt5_client.is_connected():
                logger.error("Auto-reconnect failed - connection not established")
                raise HTTPException(
                    status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                    detail="MT5 auto-reconnect failed. Please check broker connection.",
                )
            logger.success("Auto-reconnect successful!")
        except Exception as e:
            logger.error(f"Auto-reconnect failed: {e}")
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail=f"MT5 auto-reconnect failed: {str(e)}",
            )


def _fetch_pair_data_parallel(
    pairs_count: int,
    timeframes_to_fetch: list,
    bars_per_timeframe: dict,
) -> tuple[Dict[str, Any], Dict[str, Dict[str, Any]], int]:
    """Fetch multi-timeframe data for currency pairs in parallel."""
    pair_data: Dict[str, Any] = {}
    pair_timeframe_data: Dict[str, Dict[str, Any]] = {}
    successful_fetches = 0
    max_workers = min(pairs_count, 10)

    with ThreadPoolExecutor(max_workers=max_workers) as executor:
        future_to_symbol = {
            executor.submit(
                _fetch_symbol_data, symbol, timeframes_to_fetch, bars_per_timeframe
            ): symbol
            for symbol in CURRENCY_PAIRS[:pairs_count]
        }

        for future in as_completed(future_to_symbol):
            symbol = future_to_symbol[future]
            try:
                symbol_name, combined_df, timeframe_data = future.result()
                if combined_df is not None and timeframe_data != {}:
                    pair_data[symbol_name] = combined_df
                    pair_timeframe_data[symbol_name] = timeframe_data
                    successful_fetches += 1
            except Exception as e:
                logger.warning(f"✗ {symbol}: Error processing result - {str(e)}")
                continue

    if not pair_data:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Failed to fetch market data from MT5. Please try again.",
        )

    return pair_data, pair_timeframe_data, successful_fetches


def _fetch_missing_pairs(
    missing_pairs: set,
    timeframes_to_fetch: list,
    bars_per_timeframe: dict,
    pair_timeframe_data: Dict[str, Dict[str, Any]],
) -> None:
    """Fetch timeframe data for missing recommended pairs in parallel."""
    if not missing_pairs:
        return

    logger.info(
        f"Fetching timeframe data for {len(missing_pairs)} additional recommended pairs (parallel)..."
    )
    max_workers = min(len(missing_pairs), 5)

    with ThreadPoolExecutor(max_workers=max_workers) as executor:
        future_to_symbol = {
            executor.submit(
                _fetch_symbol_data, symbol, timeframes_to_fetch, bars_per_timeframe
            ): symbol
            for symbol in missing_pairs
        }

        for future in as_completed(future_to_symbol):
            symbol = future_to_symbol[future]
            try:
                symbol_name, combined_df, timeframe_data = future.result()
                if timeframe_data and len(timeframe_data) > 0:
                    pair_timeframe_data[symbol_name] = timeframe_data
                    logger.debug(f"✓ {symbol_name}: Fetched additional timeframe data")
            except Exception as e:
                logger.warning(
                    f"✗ {symbol}: Failed to fetch additional data - {str(e)}"
                )


def _format_currency_responses(
    result: dict,
    confidence: float,
    current_time: str,
) -> List[CurrencyStrengthResponse]:
    """Format currency strength data into response objects."""
    currencies = []
    latest_strengths = result["latest_strengths"]
    latest_ranks = result["latest_ranks"]

    for currency in MAJOR_CURRENCIES:
        if currency in latest_strengths:
            currencies.append(
                CurrencyStrengthResponse(
                    currency=currency,
                    strength=latest_strengths[currency],
                    rank=latest_ranks[currency],
                    trend=_classify_trend(latest_strengths[currency]),
                    confidence=int(confidence),  # Convert float to int
                    updated_at=current_time,
                )
            )
    return currencies


def _format_pair_signals(
    pair_list: list,
    pair_timeframe_data: Dict[str, Dict[str, Any]],
    recommendation: str,
    current_time: str,
    confidence: float,
    tf1: str,
    tf2: str,
    tf3: str,
) -> List[CurrencyPairSignalResponse]:
    """Format pair signals into response objects."""
    signals = []
    for pair_info in pair_list:
        symbol = pair_info["pair"]

        # Calculate percentage changes for this pair using selected timeframes
        tf1_change = None
        tf2_change = None
        tf3_change = None

        if symbol in pair_timeframe_data:
            tf_data = pair_timeframe_data[symbol]
            tf1_change = _calculate_percentage_change(tf_data.get(tf1))
            tf2_change = _calculate_percentage_change(tf_data.get(tf2))
            tf3_change = _calculate_percentage_change(tf_data.get(tf3))

        signals.append(
            CurrencyPairSignalResponse(
                pair=symbol,
                base=pair_info["base"],
                quote=pair_info["quote"],
                base_strength=pair_info["base_strength"],
                quote_strength=pair_info["quote_strength"],
                pair_strength=pair_info["strength"],
                recommendation=recommendation,
                tf1_change=tf1_change,
                tf2_change=tf2_change,
                tf3_change=tf3_change,
            )
        )
    return signals


def _fetch_symbol_data(
    symbol: str,
    timeframes: List[str],
    bars_per_timeframe: Dict[str, int],
) -> tuple[str, Optional[pd.DataFrame], Dict[str, Any]]:
    """Fetch multi-timeframe data for a single symbol (thread worker function).

    Args:
        symbol: Currency pair symbol (e.g., "EURUSD")
        timeframes: List of timeframes to fetch [tf1, tf2, tf3]
        bars_per_timeframe: Dict mapping timeframe to number of bars to fetch

    Returns:
        Tuple of (symbol, combined_dataframe, timeframe_data_dict)
        - symbol: The currency pair symbol
        - combined_dataframe: MultiIndex DataFrame with all timeframes aligned, or None if failed
        - timeframe_data_dict: Dict of individual timeframe DataFrames for percentage calculations
    """
    try:
        timeframe_dfs = {}
        timeframe_data = {}
        all_fetched = True

        for tf in timeframes:
            try:
                data = global_mt5_client.get_bars(
                    symbol=symbol,
                    timeframe=tf,
                    count=bars_per_timeframe[tf],
                )

                if data is not None and not data.empty:
                    # Ensure 'time' is the index
                    if "time" in data.columns:
                        data = data.set_index("time")

                    timeframe_dfs[tf] = data
                    timeframe_data[tf] = data
                    logger.debug(f"  {symbol} {tf}: {len(data)} bars fetched")
                else:
                    logger.warning(f"  {symbol} {tf}: No data available")
                    all_fetched = False
                    break
            except Exception as e:
                logger.warning(f"  {symbol} {tf}: {str(e)}")
                all_fetched = False
                break

        # Only return data if all timeframes were successfully fetched
        if all_fetched and len(timeframe_dfs) == len(timeframes):
            # Combine into MultiIndex DataFrame for proper alignment
            combined_df = pd.concat(timeframe_dfs, names=["timeframe", "time"])
            # Swap levels so time is first, timeframe is second
            combined_df = combined_df.swaplevel(0, 1)

            logger.debug(f"✓ {symbol}: Multi-timeframe data combined and aligned")
            return (symbol, combined_df, timeframe_data)
        else:
            logger.warning(f"✗ {symbol}: Incomplete multi-timeframe data")
            return (symbol, None, {})

    except Exception as e:
        logger.warning(f"✗ {symbol}: {str(e)}")
        return (symbol, None, {})


@router.get("/currency-strength", response_model=CurrencyStrengthDataResponse)
async def get_currency_strength(
    authorization: Annotated[Optional[str], Header()] = None,
    pairs_count: int = 15,
    tf1: str = "M1",  # Lowest timeframe (default: short-term scalping)
    tf2: str = "M5",  # Middle timeframe
    tf3: str = "H1",  # Highest timeframe
) -> CurrencyStrengthDataResponse:
    """
    Get real-time multi-timeframe currency strength analysis from MT5 data.

    This endpoint implements Ray Dalio's interconnected market methodology with
    proper timeframe alignment. Supports multiple trading styles:

    - Short-Term (M1, M5, H1): Scalping & Ultra Short-Term Trading
    - Mid-Term (M5, H1, H4): Day Trading
    - Long-Term (H1, H4, D1): Swing Trading

    Process:
    1. Fetches tf1, tf2, and tf3 data for major currency pairs from MT5
    2. Aligns all timeframes to tf1 (lowest) timeline using forward-fill
    3. Calculates weighted currency strength (tf1: 20%, tf2: 30%, tf3: 50%)
    4. Identifies top trading opportunities (strong/weak pairs)
    5. Returns formatted data for dashboard display

    At any point in time, the strength calculation uses:
    - Current tf1 bar data
    - Most recent tf2 bar (forward-filled)
    - Most recent tf3 bar (forward-filled)

    This ensures accurate strength values for any trading style and backtesting.

    Args:
        authorization: Bearer token for authentication
        pairs_count: Number of pairs to fetch (default: 15, max: 28)
        tf1: Lowest timeframe (default: M1 for ultra short-term)
        tf2: Middle timeframe (default: M5)
        tf3: Highest timeframe (default: H1)

    Returns:
        CurrencyStrengthDataResponse with:
        - Individual currency strengths (properly aligned multi-timeframe)
        - Top strong/weak pair opportunities
        - Percentage changes for H1, H4, D1 (fixed display timeframes)
        - Confidence score based on data coverage

    Raises:
        HTTPException: If MT5 connection fails or no data available
    """
    # Authenticate user (optional - can work without auth)
    if authorization and authorization.startswith("Bearer "):
        token = authorization.replace("Bearer ", "")
        try:
            verify_token(token, db_manager)
        except Exception as e:
            logger.warning(f"Token verification failed: {e}")

    # Validate pairs_count
    pairs_count = max(1, min(pairs_count, len(CURRENCY_PAIRS)))

    # Check MT5 connection and auto-reconnect if needed
    _ensure_mt5_connection()

    try:
        # Validate and prepare timeframes
        timeframes_to_fetch = [tf1, tf2, tf3]
        logger.info(f"Using timeframes: {timeframes_to_fetch}")

        # Fetch data for currency pairs using parallel execution
        logger.info(
            f"Fetching multi-timeframe data for {pairs_count} currency pairs (parallel)..."
        )
        bars_per_timeframe = {tf1: 100, tf2: 100, tf3: 100}

        pair_data, pair_timeframe_data, successful_fetches = _fetch_pair_data_parallel(
            pairs_count, timeframes_to_fetch, bars_per_timeframe
        )

        logger.info(
            f"Successfully fetched {successful_fetches}/{pairs_count} pairs with multi-timeframe alignment"
        )

        # Calculate currency strength with proper multi-timeframe weights
        # Weights: tf1 (lowest) = 20%, tf2 (middle) = 30%, tf3 (highest) = 50%
        timeframe_weights = {tf1: 0.2, tf2: 0.3, tf3: 0.5}
        logger.info(
            f"Calculating multi-timeframe currency strength with weights: {timeframe_weights}"
        )
        result = currency_strength_indicator(
            pair_data=pair_data,
            timeframe_weights=timeframe_weights,
            include_pairs=True,
            n_top_pairs=10,
        )

        # Calculate confidence based on data coverage
        confidence = _calculate_confidence(successful_fetches, pairs_count)
        current_time = datetime.now().isoformat()

        # Collect all recommended pairs from results
        recommended_pairs = set()
        for pair_info in result.get("strong_pairs", []):
            recommended_pairs.add(pair_info["pair"])
        for pair_info in result.get("weak_pairs", []):
            recommended_pairs.add(pair_info["pair"])

        # Fetch timeframe data for any missing recommended pairs
        missing_pairs = recommended_pairs - set(pair_timeframe_data.keys())
        _fetch_missing_pairs(
            missing_pairs, timeframes_to_fetch, bars_per_timeframe, pair_timeframe_data
        )

        # Format currency strength data
        currencies = _format_currency_responses(result, confidence, current_time)

        # Format strong pairs (LONG opportunities)
        strong_pairs = _format_pair_signals(
            result.get("strong_pairs", []),
            pair_timeframe_data,
            "LONG",
            current_time,
            confidence,
            tf1,
            tf2,
            tf3,
        )

        # Format weak pairs (SHORT opportunities)
        weak_pairs = _format_pair_signals(
            result.get("weak_pairs", []),
            pair_timeframe_data,
            "SHORT",
            current_time,
            confidence,
            tf1,
            tf2,
            tf3,
        )

        logger.success(
            f"Currency strength analysis complete: {len(currencies)} currencies, "
            f"{len(strong_pairs)} strong pairs, {len(weak_pairs)} weak pairs"
        )

        return CurrencyStrengthDataResponse(
            currencies=currencies,
            strong_pairs=strong_pairs,
            weak_pairs=weak_pairs,
            last_updated=current_time,
            tf1_label=tf1,
            tf2_label=tf2,
            tf3_label=tf3,
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error calculating currency strength: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to calculate currency strength: {str(e)}",
        )

