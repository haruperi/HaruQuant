"""Exponential moving average indicator."""

import pandas as pd

from apps.logger import logger


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
    if span <= 0:
        logger.error("EMA span must be positive")
        raise ValueError("Span must be positive")

    if price_col not in data.columns:
        logger.error("EMA price column missing")
        raise ValueError(f"Price column '{price_col}' is required")

    logger.debug(f"Calculating EMA with span={span} on column '{price_col}'")
    result = data.copy()
    result[f"ema_{span}"] = (
        result[price_col].ewm(span=span, adjust=adjust, min_periods=span).mean()
    )
    logger.success("EMA calculation complete")
    return result
