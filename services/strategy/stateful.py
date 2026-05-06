"""Stateful strategy contracts for portfolio-aware execution logic."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Literal, Mapping, Protocol

import pandas as pd

TradeActionType = Literal[
    "OPEN",
    "CLOSE",
    "REDUCE",
    "INCREASE",
    "MODIFY_SL",
    "MODIFY_TP",
    "MOVE_TO_BREAKEVEN",
    "TRAIL_STOP",
    "PLACE_PENDING",
    "CANCEL_ORDER",
    "CLOSE_GROUP",
    "HOLD",
]

TradeSide = Literal["BUY", "SELL"]
OrderType = Literal["MARKET", "LIMIT", "STOP", "STOP_LIMIT"]
TimeInForce = Literal["GTC", "IOC", "FOK", "DAY"]


@dataclass(slots=True)
class PositionSnapshot:
    """Read-only position view passed into stateful strategy decisions."""

    ticket: int | str
    symbol: str
    side: TradeSide
    volume: float
    open_price: float
    current_price: float | None = None
    stop_loss: float | None = None
    take_profit: float | None = None
    profit_loss: float = 0.0
    opened_at: Any = None
    strategy_id: str | None = None
    setup_id: str | None = None
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass(slots=True)
class OrderSnapshot:
    """Read-only pending/open order view passed into stateful strategies."""

    ticket: int | str
    symbol: str
    side: TradeSide
    order_type: OrderType
    volume: float
    price: float
    stop_loss: float | None = None
    take_profit: float | None = None
    status: str | None = None
    created_at: Any = None
    expires_at: Any = None
    strategy_id: str | None = None
    setup_id: str | None = None
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass(slots=True)
class TradeSnapshot:
    """Read-only completed trade view for lifecycle-aware strategies."""

    trade_id: int | str
    symbol: str
    side: TradeSide
    volume: float
    open_price: float
    close_price: float | None = None
    profit_loss: float = 0.0
    opened_at: Any = None
    closed_at: Any = None
    exit_reason: str | None = None
    strategy_id: str | None = None
    setup_id: str | None = None
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass(slots=True)
class StrategyRuntimeState:
    """Mutable per-strategy state persisted by the runtime between events."""

    strategy_id: str
    variables: dict[str, Any] = field(default_factory=dict)
    counters: dict[str, int] = field(default_factory=dict)
    flags: dict[str, bool] = field(default_factory=dict)
    last_event_at: Any = None
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass(slots=True)
class StrategyContext:
    """Portfolio-aware strategy decision context for one market/runtime event."""

    strategy_id: str
    symbol: str
    timestamp: Any = None
    event_type: str = "BAR"
    current_bar: pd.Series | Mapping[str, Any] | None = None
    current_tick: Mapping[str, Any] | None = None
    market_data: pd.DataFrame | None = None
    account: Mapping[str, Any] = field(default_factory=dict)
    positions: list[PositionSnapshot] = field(default_factory=list)
    orders: list[OrderSnapshot] = field(default_factory=list)
    closed_trades: list[TradeSnapshot] = field(default_factory=list)
    runtime_state: StrategyRuntimeState | None = None
    features: dict[str, Any] = field(default_factory=dict)
    metadata: dict[str, Any] = field(default_factory=dict)

    def positions_for_symbol(self, symbol: str | None = None) -> list[PositionSnapshot]:
        """Return open positions matching a symbol, defaulting to this context symbol."""
        target = str(symbol or self.symbol)
        return [position for position in self.positions if position.symbol == target]

    def orders_for_symbol(self, symbol: str | None = None) -> list[OrderSnapshot]:
        """Return pending/open orders matching a symbol, defaulting to this context symbol."""
        target = str(symbol or self.symbol)
        return [order for order in self.orders if order.symbol == target]


@dataclass(slots=True)
class TradeAction:
    """A portfolio-aware instruction emitted by a stateful strategy."""

    action_type: TradeActionType
    symbol: str
    side: TradeSide | None = None
    volume: float | None = None
    order_type: OrderType = "MARKET"
    price: float | None = None
    stop_loss: float | None = None
    take_profit: float | None = None
    time_in_force: TimeInForce = "GTC"
    ticket: int | str | None = None
    setup_id: str | None = None
    group_id: str | None = None
    strategy_id: str | None = None
    reason: str | None = None
    tags: list[str] = field(default_factory=list)
    metadata: dict[str, Any] = field(default_factory=dict)

    @classmethod
    def hold(
        cls,
        *,
        symbol: str,
        strategy_id: str | None = None,
        reason: str | None = None,
    ) -> "TradeAction":
        """Create an explicit no-op action for audit trails."""
        return cls(
            action_type="HOLD",
            symbol=str(symbol),
            strategy_id=strategy_id,
            reason=reason,
        )


class StatefulStrategyProtocol(Protocol):
    """Structural protocol for strategies that consume portfolio state."""

    requires_portfolio_state: bool

    def on_event(self, context: StrategyContext) -> list[TradeAction]:
        """Return trade actions for the current market/runtime event."""
        ...

    def on_order_update(self, event: Mapping[str, Any]) -> None:
        """Handle order lifecycle updates."""
        ...

    def on_trade_update(self, event: Mapping[str, Any]) -> None:
        """Handle trade lifecycle updates."""
        ...


class StatefulStrategyMixin:
    """Optional mixin for strategies that need account, order, and position state."""

    requires_portfolio_state = True

    def on_event(self, context: StrategyContext) -> list[TradeAction]:
        """Return trade actions for the current market/runtime event."""
        return []

    def on_order_update(self, event: Mapping[str, Any]) -> None:
        """Handle order lifecycle updates when the runtime provides them."""
        _ = event

    def on_trade_update(self, event: Mapping[str, Any]) -> None:
        """Handle trade lifecycle updates when the runtime provides them."""
        _ = event


__all__ = [
    "OrderSnapshot",
    "OrderType",
    "PositionSnapshot",
    "StatefulStrategyMixin",
    "StatefulStrategyProtocol",
    "StrategyContext",
    "StrategyRuntimeState",
    "TimeInForce",
    "TradeAction",
    "TradeActionType",
    "TradeSide",
    "TradeSnapshot",
]
