from __future__ import annotations

from types import SimpleNamespace

from fastapi import FastAPI
from fastapi.testclient import TestClient

from backend_retiring.api.routes import simulator


class DummyDb:
    def __init__(self, owned: bool = True) -> None:
        self.owned = owned
        self.updated: list[tuple[int, dict]] = []

    def get_simulation_session(self, session_id: int):
        if not self.owned:
            return None
        return {"session_id": session_id, "user_id": 7, "config": {}}

    def list_simulation_sessions(self, user_id: int):
        return [{"session_id": 1, "user_id": user_id}]

    def get_paused_simulation_sessions(self, user_id: int):
        return [{"session_id": 2, "user_id": user_id}]

    def create_simulation_session(self, user_id: int, config: dict):
        return 12

    def update_simulation_session(self, session_id: int, **kwargs):
        self.updated.append((session_id, kwargs))

    def get_mt5_credentials(self, user_id: int):
        return {"login": 123, "server": "demo"}


class DummyActiveSessions:
    def __init__(self, active=None) -> None:
        self.active = active
        self.put_calls: list[tuple[int, object]] = []
        self.remove_calls: list[int] = []

    def get(self, session_id: int):
        return self.active

    def put(self, session_id: int, active) -> None:
        self.put_calls.append((session_id, active))
        self.active = active

    def remove(self, session_id: int):
        self.remove_calls.append(session_id)
        active = self.active
        self.active = None
        return active


class DummyCoordinator:
    def __init__(self, active_sessions: DummyActiveSessions, db_manager: DummyDb) -> None:
        self.active_sessions = active_sessions
        self.db_manager = db_manager

    def get_owned_metadata(self, session_id: int, user_id: int):
        session = self.db_manager.get_simulation_session(session_id)
        if not session or session.get("user_id") != user_id:
            raise simulator.HTTPException(status_code=404, detail="Session not found")
        return SimpleNamespace(as_record=lambda: dict(session))

    def require_runtime(self, session_id: int):
        active = self.active_sessions.get(session_id)
        if not active:
            raise simulator.HTTPException(status_code=400, detail="Session is not running")
        return active

    def attach_runtime(self, session_id: int, active) -> None:
        self.active_sessions.put(session_id, active)

    def get_runtime(self, session_id: int, *, renew: bool = True):
        return self.active_sessions.get(session_id)

    def release_runtime(self, session_id: int):
        return self.active_sessions.remove(session_id)


def _make_client(monkeypatch, *, db_manager, active=None):
    app = FastAPI()
    app.include_router(simulator.router, prefix="/api/simulator")
    sessions = DummyActiveSessions(active)
    coordinator = DummyCoordinator(sessions, db_manager)
    monkeypatch.setattr(simulator, "db_manager", db_manager)
    monkeypatch.setattr(simulator, "active_sessions", sessions)
    monkeypatch.setattr(simulator, "session_coordinator", coordinator)
    monkeypatch.setattr(simulator, "get_user_id_from_token", lambda authorization: 7)
    return TestClient(app), sessions


def test_get_session_returns_404_for_unowned_session(monkeypatch):
    client, _ = _make_client(monkeypatch, db_manager=DummyDb(owned=False))

    response = client.get("/api/simulator/12", headers={"Authorization": "Bearer test"})

    assert response.status_code == 404
    assert response.json() == {"detail": "Session not found"}


def test_get_positions_returns_400_when_session_not_running(monkeypatch):
    client, _ = _make_client(monkeypatch, db_manager=DummyDb(), active=None)

    response = client.get("/api/simulator/12/positions", headers={"Authorization": "Bearer test"})

    assert response.status_code == 400
    assert response.json() == {"detail": "Session is not running"}


def test_execute_trade_route_delegates_to_trade_service(monkeypatch):
    active = SimpleNamespace()
    client, _ = _make_client(monkeypatch, db_manager=DummyDb(), active=active)

    monkeypatch.setattr(
        simulator,
        "execute_trade_runtime",
        lambda runtime, payload: {
            "runtime_ok": runtime is active,
            "side": payload["side"],
            "volume": payload["volume"],
        },
    )

    response = client.post(
        "/api/simulator/12/trade",
        headers={"Authorization": "Bearer test"},
        json={"side": "buy", "volume": 0.3},
    )

    assert response.status_code == 200
    assert response.json() == {"runtime_ok": True, "side": "buy", "volume": 0.3}


def test_get_positions_route_returns_account_and_state_payload(monkeypatch):
    active = SimpleNamespace(
        simulator=SimpleNamespace(
            _account_data=SimpleNamespace(
                balance=1000.0,
                equity=1010.0,
                margin=10.0,
                profit=10.0,
                margin_free=1000.0,
                margin_level=10100.0,
            )
        )
    )
    client, _ = _make_client(monkeypatch, db_manager=DummyDb(), active=active)

    monkeypatch.setattr(
        simulator,
        "build_session_state_response",
        lambda runtime: {
            "positions": [{"id": 1}],
            "orders": [{"id": 2}],
            "market": [{"symbol": "EURUSD"}],
            "risk_snapshot": {"var": 1.0},
            "risk_scorecard": {"overall": 80.0},
            "recommendations": {"items": []},
            "governance": {"decision": "ACCEPT"},
        },
    )

    response = client.get("/api/simulator/12/positions", headers={"Authorization": "Bearer test"})

    assert response.status_code == 200
    assert response.json()["positions"] == [{"id": 1}]
    assert response.json()["account"]["equity"] == 1010.0


def test_start_route_creates_session_and_registers_active(monkeypatch):
    db = DummyDb()

    class FakeSession:
        def __init__(self, session_id: int, config: dict, db):
            self.session_id = session_id
            self.config = config
            self.db = db
            self.total_bars = 25
            self.current_bar_index = 3
            self.symbol_digits = 5
            self.risk_run_id = 77
            self.engine = SimpleNamespace(
                account_info=lambda: {"leverage": 400},
                client=SimpleNamespace(account_info=lambda: None),
            )

        def load_historical_bars(self):
            return None

        def apply_mt5_account_defaults(self):
            return None

        def refresh_risk_state(self):
            return None

        def ensure_risk_run(self):
            return 77

        def visible_total_steps(self):
            return 22

    monkeypatch.setattr(simulator, "SimulatorSession", FakeSession)
    client, sessions = _make_client(monkeypatch, db_manager=db, active=None)

    response = client.post(
        "/api/simulator/start",
        headers={"Authorization": "Bearer test"},
        json={"symbol": "EURUSD", "timeframe": "M1"},
    )

    assert response.status_code == 200
    assert response.json()["session_id"] == 12
    assert response.json()["total_bars"] == 22
    assert sessions.put_calls and sessions.put_calls[0][0] == 12
    assert db.updated and db.updated[0][0] == 12


def test_advance_route_returns_progress_payload(monkeypatch):
    active = SimpleNamespace(
        advance_frames=lambda count: [{"index": 1}] * count,
        simulator=SimpleNamespace(
            monitor_positions=lambda: {"totals": True},
            monitor_account=lambda totals: None,
        ),
        visible_current_step=lambda: 4,
        visible_total_steps=lambda: 10,
        symbol_digits=5,
        current_bar_index=4,
        total_bars=10,
        get_market_snapshots=lambda: [{"symbol": "EURUSD"}],
        get_risk_summary=lambda: {"var": 1.0},
        get_risk_score_summary=lambda: {"overall": 80.0},
        get_recommendation_summary=lambda: {"items": []},
        get_governance_report=lambda: {"decision": "ACCEPT"},
    )
    client, _ = _make_client(monkeypatch, db_manager=DummyDb(), active=active)
    monkeypatch.setattr(simulator, "collect_positions_orders", lambda runtime: ([{"id": 1}], []))
    monkeypatch.setattr(simulator, "refresh_session_risk_state", lambda runtime: None)

    response = client.post(
        "/api/simulator/12/advance",
        headers={"Authorization": "Bearer test"},
        json={"count": 2},
    )

    assert response.status_code == 200
    assert response.json()["current_index"] == 4
    assert response.json()["positions"] == [{"id": 1}]
    assert len(response.json()["bars"]) == 2


def test_resume_route_delegates_to_session_service(monkeypatch):
    client, _ = _make_client(monkeypatch, db_manager=DummyDb(), active=None)
    monkeypatch.setattr(
        simulator,
        "resume_or_restore_session",
        lambda **kwargs: {"session_id": kwargs["session_id"], "status": "running"},
    )

    response = client.post("/api/simulator/12/resume", headers={"Authorization": "Bearer test"})

    assert response.status_code == 200
    assert response.json() == {"session_id": 12, "status": "running"}


def test_stop_and_save_route_delegates_to_session_service(monkeypatch):
    client, _ = _make_client(monkeypatch, db_manager=DummyDb(), active=SimpleNamespace())
    monkeypatch.setattr(
        simulator,
        "stop_and_save_session_runtime",
        lambda **kwargs: {
            "session_id": kwargs["session_id"],
            "status": "saved",
            "backtest_id": 91,
            "risk_run_id": 13,
            "risk_snapshot_id": 14,
        },
    )

    response = client.post(
        "/api/simulator/12/stop-and-save",
        headers={"Authorization": "Bearer test"},
    )

    assert response.status_code == 200
    assert response.json()["backtest_id"] == 91
