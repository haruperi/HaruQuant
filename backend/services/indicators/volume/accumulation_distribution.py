"""Accumulation/Distribution indicator."""

import pandas as pd

from backend.common.logger import logger
from backend.services.indicators.validation import require_columns, require_dataframe


def accumulation_distribution(data: pd.DataFrame) -> pd.DataFrame:
    """Compute the Accumulation/Distribution Line (ADL) volume flow indicator.

    ADL tracks whether volume is flowing into (accumulating) or out of
    (distributing) a symbol by weighting volume with the close's position within
    the high-low range of each bar. Positive multipliers signal buying pressure,
    negative multipliers signal selling pressure, and cumulative sums highlight
    confirmation or divergence versus price.

    Calculation steps:
        1. Calculate Money Flow Multiplier = [(Close - Low) - (High - Close)] / (High - Low).
        2. Calculate Money Flow Volume = Multiplier * Volume.
        3. Accumulate Money Flow Volume to get the ADL.

    Args:
        data: DataFrame containing OHLCV data with volume.

    Returns:
        DataFrame with added ``adl`` column.

    Raises:
        ValueError: If required columns are missing or lengths mismatch.
    """
    require_dataframe(data)
    require_columns(data, ("high", "low", "close", "volume"))

    logger.debug("Calculating Accumulation/Distribution Line")
    price_range = (data["high"] - data["low"]).replace(0, pd.NA)
    money_flow_multiplier = (
        (data["close"] - data["low"]) - (data["high"] - data["close"])
    ) / price_range
    money_flow_multiplier = money_flow_multiplier.fillna(0)

    money_flow_volume = money_flow_multiplier * data["volume"]
    adl = money_flow_volume.cumsum().astype(float)

    result = data.copy()
    result["adl"] = adl

    logger.success("Accumulation/Distribution calculation complete: adl")
    return result
