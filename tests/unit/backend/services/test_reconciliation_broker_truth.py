from __future__ import annotations

from backend.mcp.mt5_mcp import MT5ReadOnlyTools
from services.execution.reconciliation import BrokerTruthFetcher


class FakeBrokerReadGateway:
    def account_info(self):
        return {"login": 12345, "equity": 10000.0}

    def positions_get(self):
        return (
            {
                "ticket": 501,
                "symbol": "EURUSD",
                "comment": "client_001",
            },
        )

    def orders_get(self):
        return (
            {
                "ticket": 401,
                "symbol": "EURUSD",
                "external_id": "client_001",
            },
            {
                "ticket": 402,
                "symbol": "GBPUSD",
                "comment": "other",
            },
        )

    def symbol_info(self, symbol: str):
        return {"symbol": symbol}

    def get_ticks(self, symbol: str, count: int = 100, as_dataframe: bool = True):
        return []


def test_broker_truth_fetcher_matches_open_order_and_position_by_client_order_id() -> None:
    fetcher = BrokerTruthFetcher(MT5ReadOnlyTools(gateway=FakeBrokerReadGateway()))

    snapshot = fetcher.fetch_for_client_order_id("client_001")

    assert snapshot.account_state["login"] == 12345
    assert snapshot.matched_order is not None
    assert snapshot.matched_order["ticket"] == 401
    assert snapshot.matched_position is not None
    assert snapshot.matched_position["ticket"] == 501


def test_broker_truth_fetcher_reuses_supplied_account_state_and_returns_absent_match() -> None:
    fetcher = BrokerTruthFetcher(MT5ReadOnlyTools(gateway=FakeBrokerReadGateway()))

    snapshot = fetcher.fetch_for_client_order_id(
        "missing_client_order",
        account_state={"login": 99999, "equity": 5000.0},
    )

    assert snapshot.account_state["login"] == 99999
    assert snapshot.matched_order is None
    assert snapshot.matched_position is None
