"""Accumulation/Distribution indicator."""

import pandas as pd

from apps.utils.logger import logger


def accumulation_distribution(data: pd.DataFrame) -> pd.DataFrame:
    """Compute the Accumulation/Distribution Line (ADL) volume flow indicator.

    ADL tracks whether volume is flowing into (accumulating) or out of
    (distributing) a symbol by weighting volume with the close's position within
    the high-low range of each bar. Positive multipliers signal buying pressure,
    negative multipliers signal selling pressure, and cumulative sums highlight
    confirmation or divergence versus price. The resulting series is appended as
    ``adl``.

    Args:
        data: DataFrame containing OHLCV data with volume.

    Returns:
        DataFrame with added ``adl`` column.

    Raises:
        ValueError: If required columns are missing or lengths mismatch.
    """
    required = {"high", "low", "close", "volume"}
    if not required.issubset(set(data.columns)):
        logger.error("Accumulation/Distribution requires high, low, close, volume")
        missing = required - set(data.columns)
        raise ValueError(f"Missing required columns: {missing}")

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

    logger.success("Accumulation/Distribution calculation complete")
    return result

