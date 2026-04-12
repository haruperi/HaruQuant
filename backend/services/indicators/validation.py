"""Input validation helpers for deterministic indicator services."""

from __future__ import annotations

from collections.abc import Iterable

import pandas as pd


def require_dataframe(data: pd.DataFrame) -> pd.DataFrame:
    """Require a non-empty pandas DataFrame for indicator computation."""

    if not isinstance(data, pd.DataFrame):
        raise TypeError("Indicator input must be a pandas DataFrame")
    if data.empty:
        raise ValueError("Indicator input must not be empty")
    return data


def require_columns(data: pd.DataFrame, columns: Iterable[str]) -> None:
    """Require columns to be present before computing an indicator."""

    required = set(columns)
    missing = required - set(data.columns)
    if missing:
        raise ValueError(f"Missing required columns: {missing}")


def require_positive_int(value: int, *, name: str) -> None:
    """Require positive integer periods/windows for lookback-based indicators."""

    if not isinstance(value, int):
        raise TypeError(f"{name} must be an integer")
    if value <= 0:
        raise ValueError(f"{name} must be positive")


def require_positive_float(value: float, *, name: str) -> None:
    """Require positive floating parameters such as Bollinger standard deviations."""

    if not isinstance(value, (int, float)):
        raise TypeError(f"{name} must be numeric")
    if float(value) <= 0:
        raise ValueError(f"{name} must be positive")


__all__ = [
    "require_columns",
    "require_dataframe",
    "require_positive_float",
    "require_positive_int",
]
