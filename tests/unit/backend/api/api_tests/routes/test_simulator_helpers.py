from __future__ import annotations

from types import SimpleNamespace

from haruquant.simulation import route_support


class DummyActive:
    def __init__(self) -> None:
        self.simulator = SimpleNamespace(
            _account_data=SimpleNamespace(
                balance=1000.0,
                equity=1010.0,
                margin=10.0,
                profit=10.0,
                margin_free=1000.0,
                margin_level=10100.0,
            ),
            monitor_positions=self._monitor_positions,
            monitor_account=self._monitor_account,
        )
        self.calls: list[str] = []

    def _monitor_positions(self):
        self.calls.append("monitor_positions")
        return {"totals": True}

    def _monitor_account(self, totals):
        assert totals == {"totals": True}
        self.calls.append("monitor_account")
        return None

    def refresh_risk_state(self):
        self.calls.append("refresh_risk_state")

    def get_market_snapshots(self):
        return [{"symbol": "EURUSD"}]

    def get_risk_summary(self):
        return {"var": 1.0}

    def get_risk_score_summary(self):
        return {"overall": 80.0}

    def get_recommendation_summary(self):
        return {"actions": []}

    def get_governance_report(self):
        return {"decision": "ACCEPT"}


def test_build_session_state_response_refreshes_before_reading_payload(monkeypatch):
    active = DummyActive()

    def fake_collect_positions_orders(arg):
        assert arg is active
        active.calls.append("collect_positions_orders")
        return ([{"id": 1}], [{"id": 2}])

    monkeypatch.setattr(route_support, "collect_positions_orders", fake_collect_positions_orders)

    payload = route_support.build_session_state_response(active)

    assert active.calls == [
        "monitor_positions",
        "monitor_account",
        "refresh_risk_state",
        "collect_positions_orders",
    ]
    assert payload["positions"] == [{"id": 1}]
    assert payload["orders"] == [{"id": 2}]
    assert payload["risk_snapshot"] == {"var": 1.0}
    assert payload["governance"] == {"decision": "ACCEPT"}
