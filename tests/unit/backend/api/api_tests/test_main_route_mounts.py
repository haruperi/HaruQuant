from __future__ import annotations

from fastapi.testclient import TestClient

from backend_retiring.api.main import app
from backend_retiring.api import main
from data.database.sqlite import database_operations
from backend_retiring.api import scheduler


def test_main_app_includes_simulator_and_backtest_routes():
    paths = {route.path for route in app.routes}

    assert "/api/simulator/start" in paths
    assert "/api/simulator/{session_id}/positions" in paths
    assert "/api/backtest/" in paths


def test_main_startup_cleans_stale_simulation_leases(monkeypatch):
    calls: list[str] = []

    class DummyDb:
        def initialize_database(self):
            calls.append("init-db")

    monkeypatch.setattr(database_operations, "DatabaseManager", lambda: DummyDb())
    monkeypatch.setattr(main.simulator, "cleanup_stale_simulation_leases", lambda: calls.append("cleanup"))
    monkeypatch.setattr(scheduler, "start_scheduler", lambda: calls.append("start-scheduler"))
    monkeypatch.setattr(scheduler, "shutdown_scheduler", lambda: calls.append("shutdown-scheduler"))

    with TestClient(main.app) as client:
        response = client.get("/api/health")

    assert response.status_code == 200
    assert calls[:3] == ["init-db", "cleanup", "start-scheduler"]
    assert calls[-1] == "shutdown-scheduler"
