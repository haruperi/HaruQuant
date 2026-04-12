"""Strategy adapter and signal router utilities."""

from __future__ import annotations

from typing import Callable, Iterable, Optional

import pandas as pd

from backend.services.strategy.base import BaseStrategy, SignalDict, SignalIntent


SignalHandler = Callable[[SignalIntent], object]


class StrategyAdapter:
    """Normalize `BaseStrategy` output into canonical `SignalIntent` payloads."""

    def __init__(
        self,
        strategy: BaseStrategy,
        *,
        default_qty: float = 1.0,
        order_type: str = "MARKET",
        time_in_force: str = "GTC",
    ) -> None:
        self.strategy = strategy
        self.default_qty = float(default_qty)
        self.order_type = order_type
        self.time_in_force = time_in_force

    def on_bar(self, data: pd.DataFrame) -> pd.DataFrame:
        """Delegate bar processing to the wrapped strategy."""
        return self.strategy.on_bar(data)

    def build_signal_intent(
        self,
        data: pd.DataFrame,
        index: int,
        *,
        features: Optional[dict[str, object]] = None,
        tags: Optional[Iterable[str]] = None,
        metadata: Optional[dict[str, object]] = None,
    ) -> Optional[SignalIntent]:
        """Build a canonical intent from a strategy signal row."""
        signal = self.strategy.get_signal(data, index)
        if signal is None:
            return None

        action = self._action_from_signal(signal)
        return {
            "action": action,
            "qty": self.default_qty,
            "order_type": self.order_type,  # type: ignore[typeddict-item]
            "price": signal.get("price"),
            "time_in_force": self.time_in_force,  # type: ignore[typeddict-item]
            "strategy_id": self.strategy.strategy_id,
            "symbol": self.strategy.symbol,
            "reason": signal.get("reason"),
            "features": dict(features or {}),
            "confidence": None,
            "tags": list(tags or ()),
            "metadata": dict(metadata or {}),
            "timestamp": signal.get("time"),
        }

    @staticmethod
    def _action_from_signal(signal: SignalDict) -> str:
        entry = int(signal.get("entry_signal") or 0)
        exit_signal = int(signal.get("exit_signal") or 0)
        if entry > 0:
            return "BUY"
        if entry < 0:
            return "SELL"
        if exit_signal:
            return "EXIT"
        return "HOLD"


class SignalRouter:
    """Validate and forward canonical signal intents to a handler."""

    _allowed_actions = {"BUY", "SELL", "EXIT", "REDUCE", "HOLD"}
    _allowed_order_types = {"MARKET", "LIMIT", "STOP", "STOP_LIMIT"}
    _allowed_tif = {"GTC", "IOC", "FOK", "DAY"}

    def __init__(self, handler: SignalHandler) -> None:
        self.handler = handler

    def route(self, intent: SignalIntent) -> object:
        """Validate an intent and pass it to the configured handler."""
        self.validate(intent)
        return self.handler(intent)

    def validate(self, intent: SignalIntent) -> None:
        """Raise ValueError when an intent violates the canonical shape."""
        if intent.get("action") not in self._allowed_actions:
            raise ValueError(f"unsupported signal action: {intent.get('action')}")
        if intent.get("order_type") not in self._allowed_order_types:
            raise ValueError(f"unsupported order_type: {intent.get('order_type')}")
        if intent.get("time_in_force") not in self._allowed_tif:
            raise ValueError(f"unsupported time_in_force: {intent.get('time_in_force')}")
        if not intent.get("strategy_id"):
            raise ValueError("strategy_id is required")
        if not intent.get("symbol"):
            raise ValueError("symbol is required")
