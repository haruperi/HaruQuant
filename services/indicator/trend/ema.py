"""Exponential moving average indicator."""

import pandas as pd

from services.utils.logger import logger
from services.indicator.validation import (
    require_columns,
    require_dataframe,
    require_positive_int,
)


def ema(
    data: pd.DataFrame, span: int, price_col: str = "close", adjust: bool = False
) -> pd.DataFrame:
    """Compute the exponential moving average (EMA) with exponential weighting.

    EMA smooths price data using exponentially decaying weights so recent values
    influence the average more than older ones. Compared to SMA, EMA reacts
    faster to price changes, making it popular for crossover systems and dynamic
    support/resistance references.

    Calculation steps:
        1. Apply EWM mean with the specified span.
        2. Adjust for bias if requested.

    Args:
        data: DataFrame containing the necessary market data.
        span: Lookback span for the exponential weighting (alpha = 2 / (span + 1)).
        price_col: Column name to use for calculations (default: "close").
        adjust: Whether to divide by decaying adjustment factor in beginning periods.

    Returns:
        DataFrame with the new EMA column appended.
        Example column name: `ema_{span}`

    Raises:
        ValueError: If parameters are invalid or required columns are missing.
        TypeError: If input types are incorrect.
    """
    require_dataframe(data)
    require_positive_int(span, name="span")
    require_columns(data, (price_col,))

    logger.debug(f"Calculating EMA with span={span} on column '{price_col}'")
    result = data.copy()
    
    col_name = f"ema_{span}"
    result[col_name] = (
        result[price_col].ewm(span=span, adjust=adjust, min_periods=span).mean()
    )
    
    logger.success(f"EMA calculation complete: {col_name}")
    return result
