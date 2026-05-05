"""Paper broker for safe execution simulation."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any

from agents._persistence import utc_stamp, write_json_artifact


@dataclass
class PaperPosition:
    symbol: str
    side: str
    size: float
    entry_price: float
    unrealized_pnl: float = 0.0


@dataclass
class PaperBroker:
    equity: float = 100000.0
    balance: float = 100000.0
    margin_used: float = 0.0
    positions: list[PaperPosition] = field(default_factory=list)
    execution_logs: list[dict[str, Any]] = field(default_factory=list)

    def place_order(
        self,
        *,
        symbol: str,
        side: str,
        order_type: str,
        size: float,
        price: float,
        spread: float = 0.0,
        slippage: float = 0.0,
        commission: float = 0.0,
        swap: float = 0.0,
    ) -> dict[str, Any]:
        fill_price = price + spread / 2 + slippage if side == "buy" else price - spread / 2 - slippage
        realized_cost = commission + swap
        self.balance -= realized_cost
        self.equity -= realized_cost
        self.margin_used += abs(size * fill_price) * 0.02
        position = PaperPosition(symbol=symbol, side=side, size=size, entry_price=fill_price)
        self.positions.append(position)
        receipt = {
            "paper_order_id": f"paper-{len(self.execution_logs) + 1}",
            "symbol": symbol,
            "side": side,
            "order_type": order_type,
            "requested_size": size,
            "fill_price": fill_price,
            "commission": commission,
            "swap": swap,
            "realized_pnl": -realized_cost,
            "unrealized_pnl": sum(pos.unrealized_pnl for pos in self.positions),
            "equity": self.equity,
            "margin_used": self.margin_used,
            "created_at": datetime.now(timezone.utc).isoformat(),
        }
        self.execution_logs.append(receipt)
        write_json_artifact("reports/logs/paper_execution", f"{receipt['paper_order_id']}-{utc_stamp()}.json", receipt)
        return receipt

    def account_snapshot(self) -> dict[str, Any]:
        return {
            "balance": self.balance,
            "equity": self.equity,
            "margin_used": self.margin_used,
            "open_positions": len(self.positions),
            "realized_pnl": self.balance - 100000.0,
            "unrealized_pnl": sum(position.unrealized_pnl for position in self.positions),
        }


__all__ = ["PaperBroker", "PaperPosition"]
