from __future__ import annotations

from dataclasses import dataclass

from backend.mcp.mt5_mcp import MT5MutatingTools, MT5ReadOnlyTools


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
