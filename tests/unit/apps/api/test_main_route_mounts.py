from __future__ import annotations

from apps.api.main import app


def test_main_app_includes_simulator_and_backtest_routes():
    paths = {route.path for route in app.routes}

    assert "/api/simulator/start" in paths
    assert "/api/simulator/{session_id}/positions" in paths
    assert "/api/backtest/" in paths
