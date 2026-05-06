"""Small compatibility types for migrated legacy strategy artifacts."""

from __future__ import annotations

from enum import IntEnum

from services.strategy.stateful import (
    OrderSnapshot,
    PositionSnapshot,
    StatefulStrategyMixin,
    StrategyContext,
    StrategyRuntimeState,
    TradeAction,
    TradeSnapshot,
)


class PositionType(IntEnum):
    """Legacy buy/sell position enum used by older saved strategy code."""

    BUY = 0
    SELL = 1


PositionTyp = PositionType


__all__ = [
    "OrderSnapshot",
    "PositionSnapshot",
    "PositionType",
    "PositionTyp",
    "StatefulStrategyMixin",
    "StrategyContext",
    "StrategyRuntimeState",
    "TradeAction",
    "TradeSnapshot",
]
