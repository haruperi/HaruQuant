from __future__ import annotations

from dataclasses import dataclass

from datetime import datetime, timezone

import pytest

from apps.core import FixedClock
from backend.mcp.mt5_mcp import (
    LegacyMT5GatewayAdapter,
    MT5MutatingTools,
    MT5ReadOnlyTools,
    MT5ToolAuthorizationError,
    MT5ToolAuthorizer,
    normalize_broker_response,
    reject_stale_execution_inputs,
)


@dataclass(frozen=True)
class DummyRecord:
    ticket: int
    symbol: str


class FakeReadGateway:
    def account_info(self):
        return {"login": 12345, "server": "demo"}

    def positions_get(self):
        return (DummyRecord(ticket=1, symbol="EURUSD"),)

    def orders_get(self):
        return (DummyRecord(ticket=2, symbol="GBPUSD"),)

    def symbol_info(self, symbol: str):
        return {"digits": 5, "point": 0.00001, "symbol": symbol}

    def get_ticks(self, symbol: str, count: int = 100, as_dataframe: bool = True):
        return [{"symbol": symbol, "bid": 1.1, "ask": 1.1002}][:count]


class FakeTradeGateway(FakeReadGateway):
    def __init__(self) -> None:
        self.requests: list[dict[str, object]] = []

    def order_send(self, request: dict[str, object]):
        self.requests.append(request)
        return {"retcode": 10009, "request": request}


class FakeLegacyClient(FakeTradeGateway):
    pass


def test_mt5_read_only_tools_normalize_account_positions_orders_and_ticks() -> None:
    tools = MT5ReadOnlyTools(gateway=FakeReadGateway())

    account = tools.get_account_info()
    positions = tools.list_positions()
    orders = tools.list_orders()
    symbol = tools.get_symbol_info("EURUSD")
    ticks = tools.get_ticks("EURUSD", count=1)

    assert account["login"] == 12345
    assert positions[0]["ticket"] == 1
    assert orders[0]["ticket"] == 2
    assert symbol["symbol"] == "EURUSD"
    assert ticks["symbol"] == "EURUSD"
    assert ticks["count"] == 1


def test_mt5_mutating_tools_forward_requests_to_order_send() -> None:
    gateway = FakeTradeGateway()
    tools = MT5MutatingTools(gateway=gateway)
    request = {"action": "deal", "symbol": "EURUSD", "volume": 0.1}

    place_result = tools.place_order(request)
    modify_result = tools.modify_position(request)
    partial_close_result = tools.partial_close(request)
    full_close_result = tools.full_close(request)
    cancel_result = tools.cancel_order(request)

    assert len(gateway.requests) == 5
    assert place_result["retcode"] == 10009
    assert modify_result["request"]["symbol"] == "EURUSD"
    assert partial_close_result["request"]["volume"] == 0.1
    assert full_close_result["request"]["action"] == "deal"
    assert cancel_result["request"]["symbol"] == "EURUSD"


def test_legacy_mt5_gateway_adapter_exposes_expected_gateway_shape() -> None:
    gateway = LegacyMT5GatewayAdapter(client=FakeLegacyClient())  # type: ignore[arg-type]

    assert gateway.account_info()["login"] == 12345
    assert gateway.positions_get()[0].ticket == 1
    assert gateway.orders_get()[0].ticket == 2
    assert gateway.symbol_info("EURUSD")["symbol"] == "EURUSD"
    assert gateway.get_ticks("EURUSD", count=1, as_dataframe=False)[0]["symbol"] == "EURUSD"
    assert gateway.order_send({"action": "deal"})["retcode"] == 10009


def test_reject_stale_execution_inputs_blocks_expired_request() -> None:
    observed_at = datetime(2026, 4, 9, 10, 0, tzinfo=timezone.utc)

    with pytest.raises(ValueError, match="stale execution-critical inputs"):
        reject_stale_execution_inputs(
            observed_at=observed_at,
            max_age_seconds=5,
            clock=FixedClock(datetime(2026, 4, 9, 10, 0, 6, tzinfo=timezone.utc)),
        )


def test_normalize_broker_response_maps_retcode_to_stable_receipt() -> None:
    receipt = normalize_broker_response(
        {
            "retcode": 10009,
            "order": 123,
            "deal": 456,
            "comment": "done",
            "request": {"symbol": "EURUSD"},
        }
    )

    assert receipt["status"] == "accepted"
    assert receipt["order_id"] == 123
    assert receipt["deal_id"] == 456
    assert receipt["comment"] == "done"
    assert receipt["request_echo"]["symbol"] == "EURUSD"


def test_mt5_tool_authorizer_blocks_unauthorized_mutating_tool_access() -> None:
    authorizer = MT5ToolAuthorizer()

    with pytest.raises(MT5ToolAuthorizationError):
        authorizer.authorize(tool_name="place_order", role="viewer")
