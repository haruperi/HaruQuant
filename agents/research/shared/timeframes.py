"""Timeframe validation helpers for research agents."""

from __future__ import annotations

SUPPORTED_TIMEFRAMES = {"M1", "M5", "M15", "M30", "H1", "H4", "D1", "W1"}


def normalize_timeframes(value: str | list[str] | tuple[str, ...] | None) -> list[str]:
    if value is None:
        return ["H1"]
    items = [value] if isinstance(value, str) else list(value)
    normalized = [item.upper() for item in items if item]
    return normalized or ["H1"]


def invalid_timeframes(value: list[str]) -> list[str]:
    return [item for item in value if item not in SUPPORTED_TIMEFRAMES]
