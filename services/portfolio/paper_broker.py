"""Deterministic paper broker for live-like execution simulation."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any

from agents._shared.persistence import utc_stamp, write_json_artifact


@dataclass
class PaperBrokerConfig:
    starting_balance: float = 100000.0
    leverage: float = 50.0
    default_spread: float = 0.0
    default_slippage: float = 0.0
    default_commission: float = 0.0
    default_swap: float = 0.0
    partial_fills_enabled: bool = False
    margin_call_enabled: bool = True
    margin_call_level: float = 0.5


@dataclass
class PaperOrderRequest:
    symbol: str
    side: str
    order_type: str = "market"
    size: float = 0.01
    price: float = 1.0


@dataclass
class PaperOrderResult:
    paper_order_id: str
    status: str
    symbol: str
    side: str
    order_type: str
    requested_size: float
    fill_price: float | None
    commission: float = 0.0
    swap: float = 0.0
    realized_pnl: float = 0.0
    unrealized_pnl: float = 0.0
    equity: float = 0.0
    margin_used: float = 0.0
    rejection_reason: str | None = None
    created_at: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())


@dataclass
class PaperPosition:
    symbol: str
    side: str
    size: float
    entry_price: float
    unrealized_pnl: float = 0.0


@dataclass
class PaperAccountState:
    balance: float
    equity: float
    margin_used: float
    realized_pnl: float
    unrealized_pnl: float
    open_positions: int
    pending_orders: int


@dataclass
class PaperBroker:
    config: PaperBrokerConfig = field(default_factory=PaperBrokerConfig)
    equity: float | None = None
    balance: float | None = None
    margin_used: float = 0.0
    positions: list[PaperPosition] = field(default_factory=list)
    pending_orders: list[dict[str, Any]] = field(default_factory=list)
    execution_logs: list[dict[str, Any]] = field(default_factory=list)

    def __post_init__(self) -> None:
        if self.balance is None:
            self.balance = self.config.starting_balance
        if self.equity is None:
            self.equity = self.config.starting_balance

    def place_order(self, *, symbol: str, side: str, order_type: str, size: float, price: float, spread: float = 0.0, slippage: float = 0.0, commission: float = 0.0, swap: float = 0.0) -> dict[str, Any]:
        if size <= 0:
            return self._reject(symbol, side, order_type, size, "non_positive_size")
        if side not in {"buy", "sell"}:
            return self._reject(symbol, side, order_type, size, "invalid_side")
        if order_type in {"limit", "stop"}:
            pending = {"paper_order_id": f"paper-pending-{len(self.pending_orders) + 1}", "status": "pending", "symbol": symbol, "side": side, "order_type": order_type, "size": size, "price": price}
            self.pending_orders.append(pending)
            return pending
        if order_type != "market":
            return self._reject(symbol, side, order_type, size, "unsupported_order_type")
        fill_price = price + spread / 2 + slippage if side == "buy" else price - spread / 2 - slippage
        self.balance = float(self.balance or 0.0) - commission - swap
        self.equity = float(self.equity or 0.0) - commission - swap
        self.margin_used += abs(size * fill_price) / max(self.config.leverage, 1.0)
        if self.config.margin_call_enabled and self.margin_used > max(float(self.equity), 0.0) * self.config.margin_call_level:
            return self._reject(symbol, side, order_type, size, "margin_call_threshold")
        self.positions.append(PaperPosition(symbol=symbol, side=side, size=size, entry_price=fill_price))
        receipt = PaperOrderResult(
            paper_order_id=f"paper-{len(self.execution_logs) + 1}",
            status="filled",
            symbol=symbol,
            side=side,
            order_type=order_type,
            requested_size=size,
            fill_price=fill_price,
            commission=commission,
            swap=swap,
            realized_pnl=-(commission + swap),
            unrealized_pnl=sum(pos.unrealized_pnl for pos in self.positions),
            equity=float(self.equity),
            margin_used=self.margin_used,
        ).__dict__
        receipt["audit_uri"] = write_json_artifact("reports/logs/paper_execution", f"{receipt['paper_order_id']}-{utc_stamp()}.json", receipt)
        self.execution_logs.append(receipt)
        return receipt

    def process_pending_orders(self, *, market_price: float) -> list[dict[str, Any]]:
        filled, remaining = [], []
        for order in self.pending_orders:
            hit_limit = order["order_type"] == "limit" and ((order["side"] == "buy" and market_price <= order["price"]) or (order["side"] == "sell" and market_price >= order["price"]))
            hit_stop = order["order_type"] == "stop" and ((order["side"] == "buy" and market_price >= order["price"]) or (order["side"] == "sell" and market_price <= order["price"]))
            if hit_limit or hit_stop:
                filled.append(self.place_order(symbol=order["symbol"], side=order["side"], order_type="market", size=order["size"], price=market_price))
            else:
                remaining.append(order)
        self.pending_orders = remaining
        return filled

    def account_snapshot(self) -> dict[str, Any]:
        return PaperAccountState(
            balance=float(self.balance or 0.0),
            equity=float(self.equity or 0.0),
            margin_used=self.margin_used,
            realized_pnl=float(self.balance or 0.0) - self.config.starting_balance,
            unrealized_pnl=sum(position.unrealized_pnl for position in self.positions),
            open_positions=len(self.positions),
            pending_orders=len(self.pending_orders),
        ).__dict__

    def _reject(self, symbol: str, side: str, order_type: str, size: float, reason: str) -> dict[str, Any]:
        receipt = PaperOrderResult(f"paper-rejected-{len(self.execution_logs) + 1}", "rejected", symbol, side, order_type, size, None, rejection_reason=reason, equity=float(self.equity or 0.0), margin_used=self.margin_used).__dict__
        receipt["audit_uri"] = write_json_artifact("reports/logs/paper_execution", f"{receipt['paper_order_id']}-{utc_stamp()}.json", receipt)
        self.execution_logs.append(receipt)
        return receipt
