"""Average True Range (ATR) indicator."""

import pandas as pd

from apps.logger import logger


def atr(data: pd.DataFrame, period: int = 14) -> pd.DataFrame:
    """Calculate the Average True Range (ATR) volatility measure.

    ATR captures the average range of price movement, accounting for gaps,
    by taking the greatest of:
        - current high minus current low
        - absolute high minus previous close
        - absolute low minus previous close
    Those true range values are then exponentially smoothed over ``period``
    bars. Higher ATR indicates higher volatility. The resulting column is
    appended as ``atr_{period}`` while leaving the input unchanged.

    Args:
        data: DataFrame containing OHLCV data.
        period: Lookback period (default: 14).

    Returns:
        DataFrame with added ATR column named ``atr_{period}``.

    Raises:
        ValueError: If period is not positive or required columns are missing.
    """
    required = {"high", "low", "close"}
    if period <= 0:
        logger.error("ATR period must be positive")
        raise ValueError("Period must be positive")

    if not required.issubset(set(data.columns)):
        logger.error("ATR requires high, low, and close columns")
        missing = required - set(data.columns)
        raise ValueError(f"Missing required columns: {missing}")

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
    result[f"atr_{period}"] = atr_values.astype(float)

    logger.success("ATR calculation complete")
    return result
