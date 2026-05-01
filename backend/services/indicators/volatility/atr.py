"""Average True Range (ATR) indicator."""

import pandas as pd

from backend.common.logger import logger
from backend.services.indicators.validation import (
    require_columns,
    require_dataframe,
    require_positive_int,
)


def atr(data: pd.DataFrame, period: int = 14) -> pd.DataFrame:
    """Calculate the Average True Range (ATR) volatility measure.

    ATR captures the average range of price movement, accounting for gaps,
    by taking the greatest of:
        - current high minus current low
        - absolute high minus previous close
        - absolute low minus previous close
    Those true range values are then exponentially smoothed over ``period``
    bars. Higher ATR indicates higher volatility.

    Calculation steps:
        1. Calculate True Range (TR) as max(high-low, |high-prev_close|, |low-prev_close|).
        2. Smooth TR using EWMA with alpha=1/period.

    Args:
        data: DataFrame containing OHLCV data.
        period: Lookback period (default: 14).

    Returns:
        DataFrame with added ATR column named ``atr_{period}``.

    Raises:
        ValueError: If period is not positive or required columns are missing.
    """
    require_dataframe(data)
    require_positive_int(period, name="period")
    require_columns(data, ("high", "low", "close"))

    logger.debug(f"Calculating ATR with period={period}")
    prev_close = data["close"].shift(1)
    high_low = data["high"] - data["low"]
    high_close = (data["high"] - prev_close).abs()
    low_close = (data["low"] - prev_close).abs()

    true_range = pd.concat([high_low, high_close, low_close], axis=1).max(axis=1)
    atr_values = true_range.ewm(
        alpha=1 / period, adjust=False, min_periods=period
    ).mean()

    result = data.copy()
    col_name = f"atr_{period}"
    result[col_name] = atr_values.astype(float)

    logger.success(f"ATR calculation complete: {col_name}")
    return result
