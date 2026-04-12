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
    other moving averages. The result is appended as ``sma_{window}`` without
    mutating the input.
    """
    require_dataframe(data)
    require_positive_int(window, name="window")
    require_columns(data, (price_col,))

    logger.debug(f"Calculating SMA with window={window} on column '{price_col}'")
    result = data.copy()
    result[f"sma_{window}"] = (
        result[price_col].rolling(window=window, min_periods=window).mean()
    )
    logger.success("SMA calculation complete")
    return result

