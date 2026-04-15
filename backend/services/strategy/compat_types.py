"""Small compatibility types for migrated legacy strategy artifacts."""

from __future__ import annotations

from enum import IntEnum


class PositionType(IntEnum):
    """Legacy buy/sell position enum used by older saved strategy code."""

    BUY = 0
    SELL = 1


PositionTyp = PositionType


__all__ = ["PositionType", "PositionTyp"]

