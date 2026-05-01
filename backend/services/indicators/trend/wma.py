"""Weighted moving average indicator."""

import numpy as np
import pandas as pd

from backend.common.logger import logger
from backend.services.indicators.validation import (
    require_columns,
    require_dataframe,
    require_positive_int,
)


def wma(data: pd.DataFrame, window: int, price_col: str = "close") -> pd.DataFrame:
    """Compute the weighted moving average (WMA) with linearly increasing weights.

    WMA assigns larger weights to more recent prices within the ``window`` while
    still considering all observations in the window. This creates a smoother yet
    responsive trend estimate that sits between SMA (slowest) and EMA (fastest).

    Calculation steps:
        1. Generate linearly increasing weights from 1 to window.
        2. Apply rolling weighted average using dot product.

    Args:
        data: DataFrame containing the necessary market data.
        window: Lookback window size for the average.
        price_col: Column name to use for calculations (default: "close").

    Returns:
        DataFrame with the new WMA column appended.
        Example column name: `wma_{window}`

    Raises:
        ValueError: If parameters are invalid or required columns are missing.
        TypeError: If input types are incorrect.
    """
    require_dataframe(data)
    require_positive_int(window, name="window")
    require_columns(data, (price_col,))

    logger.debug(f"Calculating WMA with window={window} on column '{price_col}'")
    weights = np.arange(1, window + 1)
    weighted_sum = (
        data[price_col]
        .rolling(window=window, min_periods=window)
        .apply(lambda x: np.dot(x, weights) / weights.sum(), raw=True)
    )

    result = data.copy()
    col_name = f"wma_{window}"
    result[col_name] = weighted_sum
    
    logger.success(f"WMA calculation complete: {col_name}")
    return result
