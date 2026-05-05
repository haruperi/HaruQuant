"""MT5 MCP tool adapters."""

from __future__ import annotations

from dataclasses import asdict, dataclass, is_dataclass
from datetime import UTC, datetime
from typing import Any, Protocol

from haruquant.utils import Clock
from haruquant.utils import evaluate_freshness
from backend.mcp.mt5_mcp.client import MT5Client

from .models import MCPToolSpec


class MT5ReadGateway(Protocol):
    """Minimal read gateway required by the MCP tool adapters."""

    def account_info(self) -> Any: ...

    def positions_get(self) -> Any: ...

    def orders_get(self) -> Any: ...

    def symbol_info(self, symbol: str) -> Any: ...

    def get_ticks(self, symbol: str, count: int = 100, as_dataframe: bool = True) -> Any: ...


class MT5TradeGateway(MT5ReadGateway, Protocol):
    """Gateway extended with mutating broker operations."""

    def order_send(self, request: dict[str, Any]) -> Any: ...


@dataclass(frozen=True)
class LegacyMT5GatewayAdapter:
    """Compatibility adapter exposing the legacy MT5 client through the MCP gateway shape."""

    client: MT5Client

    def account_info(self) -> Any:
        return self.client.account_info()

    def positions_get(self) -> Any:
        return self.client.positions_get()

    def orders_get(self) -> Any:
        return self.client.orders_get()

    def symbol_info(self, symbol: str) -> Any:
        return self.client.symbol_info(symbol)

    def get_ticks(self, symbol: str, count: int = 100, as_dataframe: bool = True) -> Any:
        return self.client.get_ticks(symbol, count=count, as_dataframe=as_dataframe)

    def order_send(self, request: dict[str, Any]) -> Any:
        return self.client.order_send(request)


def _normalize_mt5_record(record: Any) -> dict[str, Any]:
    if record is None:
        return {}
    if isinstance(record, dict):
        return record
    if hasattr(record, "_asdict"):
        return record._asdict()
    if is_dataclass(record):
        return asdict(record)
    if hasattr(record, "__dict__"):
        return {
            key: value
            for key, value in vars(record).items()
            if not key.startswith("_")
        }
    return {"value": record}


@dataclass(frozen=True)
class MT5ReadOnlyTools:
    """Read-only MT5 MCP tool facade."""

    gateway: MT5ReadGateway

    def get_account_info(self) -> dict[str, Any]:
        return _normalize_mt5_record(self.gateway.account_info())

    def list_positions(self) -> list[dict[str, Any]]:
        positions = self.gateway.positions_get() or ()
        return [_normalize_mt5_record(position) for position in positions]

    def list_orders(self) -> list[dict[str, Any]]:
        orders = self.gateway.orders_get() or ()
        return [_normalize_mt5_record(order) for order in orders]

    def get_symbol_info(self, symbol: str) -> dict[str, Any]:
        payload = _normalize_mt5_record(self.gateway.symbol_info(symbol))
        payload["symbol"] = symbol
        return payload

    def get_ticks(self, symbol: str, count: int = 100) -> dict[str, Any]:
        ticks = self.gateway.get_ticks(symbol, count=count, as_dataframe=False) or []
        return {
            "symbol": symbol,
            "count": len(ticks),
            "ticks": ticks,
            "fetched_at": datetime.now(UTC).isoformat().replace("+00:00", "Z"),
        }


@dataclass(frozen=True)
class MT5MutatingTools:
    """Side-effecting MT5 MCP tool facade."""

    gateway: MT5TradeGateway

    def place_order(self, request: dict[str, Any]) -> Any:
        return self.gateway.order_send(request)

    def modify_position(self, request: dict[str, Any]) -> Any:
        return self.gateway.order_send(request)

    def partial_close(self, request: dict[str, Any]) -> Any:
        return self.gateway.order_send(request)

    def full_close(self, request: dict[str, Any]) -> Any:
        return self.gateway.order_send(request)

    def cancel_order(self, request: dict[str, Any]) -> Any:
        return self.gateway.order_send(request)


def reject_stale_execution_inputs(
    *,
    observed_at: datetime,
    max_age_seconds: int,
    clock: Clock | None = None,
) -> None:
    """Fail closed when execution-critical MT5 tool inputs are stale."""

    freshness = evaluate_freshness(
        observed_at,
        max_age_seconds=max_age_seconds,
        clock=clock,
    )
    if freshness.is_stale:
        raise ValueError("stale execution-critical inputs")


def default_mt5_gateway() -> MT5Client:
    """Create the default MT5 gateway adapter."""

    return MT5Client()


READ_ONLY_TOOL_SPECS: tuple[MCPToolSpec, ...] = (
    MCPToolSpec("get_account_info", "read", "Read broker account state."),
    MCPToolSpec("list_positions", "read", "List open broker positions."),
    MCPToolSpec("list_orders", "read", "List open broker orders."),
    MCPToolSpec("get_symbol_info", "read", "Read symbol metadata from broker."),
    MCPToolSpec("get_ticks", "read", "Fetch recent broker tick data."),
)

MUTATING_TOOL_SPECS: tuple[MCPToolSpec, ...] = (
    MCPToolSpec("place_order", "write", "Submit broker order request."),
    MCPToolSpec("modify_position", "write", "Modify broker position stops or limits."),
    MCPToolSpec("partial_close", "write", "Partially close broker position."),
    MCPToolSpec("full_close", "write", "Fully close broker position."),
    MCPToolSpec("cancel_order", "write", "Cancel broker pending order."),
)


__all__ = [
    "MT5MutatingTools",
    "MT5ReadOnlyTools",
    "LegacyMT5GatewayAdapter",
    "MUTATING_TOOL_SPECS",
    "READ_ONLY_TOOL_SPECS",
    "default_mt5_gateway",
    "reject_stale_execution_inputs",
]
