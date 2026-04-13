"""Shared helpers for baseline strategies."""

from __future__ import annotations

from typing import Any

import pandas as pd


SIGNAL_COLUMNS = (
    "entry_signal",
    "exit_signal",
    "pending_signal",
    "cancel_pending_signal",
    "pending_signal_2",
    "cancel_pending_signal_2",
)


def initialize_signal_columns(data: pd.DataFrame) -> pd.DataFrame:
    """Add the standard signal columns expected by strategy adapters."""
    result = data.copy()
    for column in SIGNAL_COLUMNS:
        result[column] = 0
    result["price"] = pd.NA
    result["price_2"] = pd.NA
    result["signal_reason"] = ""
    result["signal_confidence"] = pd.NA
    return result


def price_at(row: pd.Series, price_col: str) -> float | None:
    """Return the row price as float when available."""
    value: Any = row.get(price_col)
    if pd.isna(value):
        return None
    return float(value)
