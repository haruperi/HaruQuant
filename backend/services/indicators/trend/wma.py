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
    The output column is appended as ``wma_{window}`` without altering the input.
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
    result[f"wma_{window}"] = weighted_sum
    logger.success("WMA calculation complete")
    return result

