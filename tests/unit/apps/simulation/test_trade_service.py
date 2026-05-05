from __future__ import annotations

from types import SimpleNamespace

import pytest
from fastapi import HTTPException

from haruquant.simulation import trade_service


class DummyActive:
    def __init__(self) -> None:
        self.symbols = ["EURUSD"]
        self.config = {"mode": "manual"}
        self.trade_requests: list[dict] = []
        self.pending_requests: list[dict] = []
        self.preview_requests: list[tuple[str, float]] = []

    def risk_limits_enforced(self) -> bool:
        return True

    def evaluate_pre_trade_governance(self, symbol: str, signed_volume: float):
        return SimpleNamespace(decision="ACCEPT", symbol=symbol, signed_volume=signed_volume)

    def execute_trade(self, payload: dict):
        self.trade_requests.append(payload)
        return {"ticket": 1}

    def place_pending_order(self, payload: dict):
        self.pending_requests.append(payload)
        return {"ticket": 2}

    def get_governance_report(self):
        return {"decision": "ACCEPT"}

    def build_manual_trade_review(self, symbol: str, signed_volume: float):
        self.preview_requests.append((symbol, signed_volume))
        return {"symbol": symbol, "signed_volume": signed_volume}


def test_execute_trade_returns_refreshed_payload(monkeypatch):
    active = DummyActive()

    monkeypatch.setattr(
        trade_service,
        "build_session_state_response",
        lambda arg: {
            "positions": [{"id": 1}],
            "orders": [{"id": 2}],
            "risk_snapshot": {"var": 1.0},
            "risk_scorecard": {"overall": 80.0},
            "recommendations": {"items": []},
        },
    )
    monkeypatch.setattr(
        trade_service,
        "_serialize_governance_report",
        lambda report: {"decision": getattr(report, "decision", None)},
    )

    payload = trade_service.execute_trade(
        active,
        {"side": "buy", "volume": 0.2, "manual_review_accepted": False},
    )

    assert active.trade_requests == [{"side": "buy", "volume": 0.2, "manual_review_accepted": False}]
    assert payload["trade"] == {"ticket": 1}
    assert payload["governance"] == {"decision": "ACCEPT"}
    assert payload["positions"] == [{"id": 1}]


def test_preview_trade_uses_signed_volume():
    active = DummyActive()

    payload = trade_service.preview_trade(active, {"symbol": "GBPUSD", "side": "sell", "volume": 0.4})

    assert payload == {"symbol": "GBPUSD", "signed_volume": -0.4}
    assert active.preview_requests == [("GBPUSD", -0.4)]


def test_evaluate_trade_governance_rejects_breach(monkeypatch):
    active = DummyActive()
    active.evaluate_pre_trade_governance = lambda **_: SimpleNamespace(decision="REJECT")
    monkeypatch.setattr(
        trade_service,
        "_serialize_governance_report",
        lambda report: {"decision": getattr(report, "decision", None)},
    )

    with pytest.raises(HTTPException) as exc:
        trade_service._evaluate_trade_governance(
            active,
            symbol="EURUSD",
            signed_volume=0.1,
            allow_manual_override=False,
        )

    assert exc.value.status_code == 409
    assert exc.value.detail == {
        "type": "governance_reject",
        "governance": {"decision": "REJECT"},
    }
