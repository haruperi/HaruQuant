"""Bollinger Bands indicator."""

import pandas as pd

from backend.common.logger import logger


def bbands(
    data: pd.DataFrame, period: int = 20, std_dev: float = 2.0, price_col: str = "close"
) -> pd.DataFrame:
    """Compute Bollinger Bands volatility indicator.

    Bollinger Bands consist of a moving average (middle band) and two bands
    positioned at a specified number of standard deviations above and below it.
    They help identify periods of high or low volatility and potential
    overbought/oversold conditions.

    The indicator produces three bands:
        - Upper band = SMA(period) + (std_dev * standard deviation)
        - Middle band = SMA(period)
        - Lower band = SMA(period) - (std_dev * standard deviation)

    Args:
        data: DataFrame containing OHLCV data.
        period: Lookback period for moving average (default: 20).
        std_dev: Number of standard deviations for bands (default: 2.0).
        price_col: Column name for prices (default: "close").

    Returns:
        DataFrame with three added columns:
            - ``bb_upper_{period}_{std_dev}``
            - ``bb_middle_{period}_{std_dev}``
            - ``bb_lower_{period}_{std_dev}``

    Raises:
        ValueError: If period is not positive or price column missing.
    """
    if period <= 0:
        logger.error("BBands period must be positive")
        raise ValueError("Period must be positive")

    if price_col not in data.columns:
        logger.error("BBands price column missing")
        raise ValueError(f"Price column '{price_col}' is required")

    logger.debug(
        f"Calculating Bollinger Bands with period={period}, std_dev={std_dev} on column '{price_col}'"
    )

    result = data.copy()
    prices = result[price_col]

    # Calculate middle band (SMA)
    middle = prices.rolling(window=period, min_periods=period).mean()

    # Calculate standard deviation
    rolling_std = prices.rolling(window=period, min_periods=period).std()

    # Calculate upper and lower bands
    upper = middle + (std_dev * rolling_std)
    lower = middle - (std_dev * rolling_std)

    # Add columns to result
    suffix = f"{period}_{int(std_dev) if std_dev == int(std_dev) else std_dev}"
    result[f"bb_upper_{suffix}"] = upper.astype(float)
    result[f"bb_middle_{suffix}"] = middle.astype(float)
    result[f"bb_lower_{suffix}"] = lower.astype(float)

    logger.success("Bollinger Bands calculation complete")
    return result

