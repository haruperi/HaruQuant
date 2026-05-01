"""Simple moving average indicator."""

import pandas as pd

from backend.common.logger import logger
from backend.services.indicators.validation import (
    require_columns,
    require_dataframe,
    require_positive_int,
)


def sma(data: pd.DataFrame, window: int, price_col: str = "close") -> pd.DataFrame:
    """Compute the simple moving average (SMA) over a fixed window.

    SMA smooths price data by averaging the last ``window`` observations of
    ``price_col`` with equal weights. It is commonly used to filter noise,
    define trend direction, and generate cross-over signals when paired with
    other moving averages.

    Calculation steps:
        1. Apply rolling mean with the specified window.

    Args:
        data: DataFrame containing the necessary market data.
        window: Lookback window size for the average.
        price_col: Column name to use for calculations (default: "close").

    Returns:
        DataFrame with the new SMA column appended.
        Example column name: `sma_{window}`

    Raises:
        ValueError: If parameters are invalid or required columns are missing.
        TypeError: If input types are incorrect.
    """
    require_dataframe(data)
    require_positive_int(window, name="window")
    require_columns(data, (price_col,))

    logger.debug(f"Calculating SMA with window={window} on column '{price_col}'")
    result = data.copy()
    
    col_name = f"sma_{window}"
    result[col_name] = (
        result[price_col].rolling(window=window, min_periods=window).mean()
    )
    
    logger.success(f"SMA calculation complete: {col_name}")
    return result
