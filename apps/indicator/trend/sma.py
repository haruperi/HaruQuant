"""Simple moving average indicator."""

import pandas as pd

from apps.utils.logger import logger


def sma(data: pd.DataFrame, window: int, price_col: str = "close") -> pd.DataFrame:
    """Compute the simple moving average (SMA) over a fixed window.

    SMA smooths price data by averaging the last ``window`` observations of
    ``price_col`` with equal weights. It is commonly used to filter noise,
    define trend direction, and generate cross-over signals when paired with
    other moving averages. The result is appended as ``sma_{window}`` without
    mutating the input.
    """
    if window <= 0:
        logger.error("SMA window must be positive")
        raise ValueError("Window must be positive")

    if price_col not in data.columns:
        logger.error("SMA price column missing")
        raise ValueError(f"Price column '{price_col}' is required")

    logger.debug(f"Calculating SMA with window={window} on column '{price_col}'")
    result = data.copy()
    result[f"sma_{window}"] = (
        result[price_col].rolling(window=window, min_periods=window).mean()
    )
    logger.success("SMA calculation complete")
    return result

