"""Exponential moving average indicator."""

import pandas as pd

from backend.common.logger import logger
from backend.services.indicators.validation import (
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
    support/resistance references. The resulting column is appended as
    ``ema_{span}`` and the input DataFrame is left unchanged.
    """
    require_dataframe(data)
    require_positive_int(span, name="span")
    require_columns(data, (price_col,))

    logger.debug(f"Calculating EMA with span={span} on column '{price_col}'")
    result = data.copy()
    result[f"ema_{span}"] = (
        result[price_col].ewm(span=span, adjust=adjust, min_periods=span).mean()
    )
    logger.success("EMA calculation complete")
    return result

