"""Relative Strength Index (RSI) indicator."""

import pandas as pd

from apps.logger import logger


def rsi(data: pd.DataFrame, period: int = 14, price_col: str = "close") -> pd.DataFrame:
    """Compute the Relative Strength Index (RSI) momentum oscillator.

    RSI compares the magnitude of recent gains to recent losses over a fixed lookback
    to gauge the speed and change of price movements. Values oscillate between 0 and
    100, where readings above 70 often signal overbought conditions and readings
    below 30 often signal oversold conditions. This implementation uses an
    exponentially smoothed average of gains and losses over ``period`` bars.

    Calculation steps:
        1. Compute price changes of ``price_col``.
        2. Separate positive (gains) and negative (losses) moves.
        3. Smooth gains and losses with an EWMA using alpha=1/period.
        4. Compute RS = avg_gain / avg_loss and convert to RSI = 100 - 100/(1 + RS).
        5. Fill initial values with a neutral 50 and guard divide-by-zero cases.

    The resulting column is appended as ``rsi_{period}`` and leaves the input intact.

    Args:
        data: DataFrame containing OHLCV data.
        period: Lookback period for smoothing (default: 14).
        price_col: Column name for prices to compute RSI on (default: "close").

    Returns:
        DataFrame with added RSI column named ``rsi_{period}``.

    Raises:
        ValueError: If period is not positive or price column missing.
    """
    if period <= 0:
        logger.error("RSI period must be positive")
        raise ValueError("Period must be positive")

    if price_col not in data.columns:
        logger.error("RSI price column missing")
        raise ValueError(f"Price column '{price_col}' is required")

    logger.debug(f"Calculating RSI with period={period} on column '{price_col}'")
    close = data[price_col]
    delta = close.diff()
    gain = delta.clip(lower=0)
    loss = -delta.clip(upper=0)

    avg_gain = gain.ewm(alpha=1 / period, adjust=False, min_periods=period).mean()
    avg_loss = loss.ewm(alpha=1 / period, adjust=False, min_periods=period).mean()

    rs = avg_gain.divide(avg_loss.replace(0, pd.NA))
    rsi_values = 100 - (100 / (1 + rs))

    rsi_values = rsi_values.fillna(50.0)
    rsi_values = rsi_values.mask(avg_loss == 0, 100.0)
    rsi_values = rsi_values.mask(avg_gain == 0, 0.0)

    result = data.copy()
    result[f"rsi_{period}"] = rsi_values.astype(float)

    logger.success("RSI calculation complete")
    return result
