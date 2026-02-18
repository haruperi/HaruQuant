"""Strategy adapter and signal router for canonical intent flow."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any, Callable, Optional
from uuid import uuid4

import pandas as pd

from apps.strategy.base import BaseStrategy, SignalIntent, StrategyEvent


def _utc_now() -> datetime:
    return datetime.now(timezone.utc)


def _event(
    *,
    event_type: str,
    strategy: BaseStrategy,
    symbol: str,
    payload: dict[str, Any],
    run_id: str = "",
    trace_id: str = "",
    correlation_id: str = "",
) -> StrategyEvent:
    now = _utc_now()
    return {
        "event_id": f"evt-{uuid4().hex}",
        "event_type": event_type,  # type: ignore[typeddict-item]
        "symbol": symbol,
        "strategy_id": strategy.strategy_id,
        "event_ts": now,
        "recv_ts": now,
        "payload": payload,
        "run_id": run_id,
        "trace_id": trace_id,
        "correlation_id": correlation_id,
    }


@dataclass
class StrategyAdapter:
    """Lightweight adapter for strategy lifecycle + intent normalization."""

    strategy: BaseStrategy

    def on_bar(self, data: pd.DataFrame) -> pd.DataFrame:
        return self.strategy.on_bar(data)

    def on_tick(self, data: pd.DataFrame) -> pd.DataFrame:
        return self.strategy.on_tick(data)

    def build_signal_intent(
        self,
        data: pd.DataFrame,
        index: int,
        *,
        symbol: Optional[str] = None,
    ) -> Optional[SignalIntent]:
        signal = self.strategy.get_signal(data, index)
        if signal is None:
            return None

        raw_entry = int(signal.get("entry_signal", 0) or 0)
        raw_exit = int(signal.get("exit_signal", 0) or 0)
        if raw_exit != 0:
            action = "EXIT"
        elif raw_entry > 0:
            action = "BUY"
        elif raw_entry < 0:
            action = "SELL"
        else:
            action = "HOLD"

        resolved_symbol = str(symbol or self.strategy.symbol)
        price_obj = signal.get("price")
        price = float(price_obj) if isinstance(price_obj, (int, float)) else None

        features = signal.get("features")
        tags = signal.get("tags")
        metadata = signal.get("metadata")
        confidence_obj = signal.get("confidence")

        intent: SignalIntent = {
            "action": action,
            "qty": float(signal.get("volume", 0.0) or 0.0),
            "order_type": str(signal.get("order_type", "MARKET")).upper(),  # type: ignore[typeddict-item]
            "price": price,
            "time_in_force": str(signal.get("time_in_force", "GTC")).upper(),  # type: ignore[typeddict-item]
            "strategy_id": self.strategy.strategy_id,
            "symbol": resolved_symbol,
            "reason": str(signal.get("reason", "")),
            "confidence": float(confidence_obj) if isinstance(confidence_obj, (int, float)) else 0.0,
            "features": dict(features) if isinstance(features, dict) else {},
            "tags": {str(k): str(v) for k, v in tags.items()} if isinstance(tags, dict) else {},
            "metadata": dict(metadata) if isinstance(metadata, dict) else {},
        }
        return intent

    def event_for_signal(self, intent: SignalIntent, *, run_id: str = "", trace_id: str = "", correlation_id: str = "") -> StrategyEvent:
        return _event(
            event_type="bar",
            strategy=self.strategy,
            symbol=str(intent["symbol"]),
            payload={"signal_intent": dict(intent)},
            run_id=run_id,
            trace_id=trace_id,
            correlation_id=correlation_id,
        )


@dataclass
class SignalRouter:
    """Validate and forward canonical signal intents."""

    handler: Callable[[SignalIntent], Any]

    def route(self, intent: SignalIntent) -> Any:
        action = str(intent.get("action", "")).upper()
        if action not in {"BUY", "SELL", "EXIT", "REDUCE", "HOLD"}:
            raise ValueError(f"invalid action: {action}")
        order_type = str(intent.get("order_type", "")).upper()
        if order_type not in {"MARKET", "LIMIT", "STOP", "STOP_LIMIT"}:
            raise ValueError(f"invalid order_type: {order_type}")
        tif = str(intent.get("time_in_force", "")).upper()
        if tif not in {"GTC", "IOC", "FOK", "DAY"}:
            raise ValueError(f"invalid time_in_force: {tif}")
        qty = float(intent.get("qty", 0.0) or 0.0)
        if qty < 0:
            raise ValueError("qty must be >= 0")
        return self.handler(intent)
