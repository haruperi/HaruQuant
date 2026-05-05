from __future__ import annotations

from pathlib import Path

from fastapi import FastAPI
from fastapi.testclient import TestClient

from backend.api.routes import operator_strategies
from backend.data.database import GovernanceRepository, apply_pending_migrations, default_migrations_dir
from backend.data.database.sqlite.database_operations import DatabaseManager
from services.strategy import StrategyStorage
from services.strategy.catalog import StrategyCatalogCreateRequest, StrategyCatalogService


STRATEGY_CODE = """
from services.strategy import BaseStrategy


class OperatorRouteStrategy(BaseStrategy):
    def on_init(self):
        pass

    def on_bar(self, data):
        return data
"""


def _client(tmp_path: Path) -> TestClient:
    db_path = tmp_path / "haruquant.db"
    db = DatabaseManager(db_path=str(db_path))
    db.initialize_database()
    apply_pending_migrations(db_path, default_migrations_dir())
    db.create_user(
        email="operator@example.com",
        username="operator_user",
        password="password",
    )
    governance = GovernanceRepository(db_path)
    service = StrategyCatalogService(
        db_manager=db,
        strategy_storage=StrategyStorage(base_dir=str(tmp_path / "strategies")),
        governance_repository=governance,
    )
    service.create_strategy(
        StrategyCatalogCreateRequest(
            name="Operator Strategy",
            category="custom",
            code=STRATEGY_CODE,
        ),
        user_id=1,
    )

    operator_strategies.db_manager = db
    operator_strategies.governance_repository = governance
    app = FastAPI()
    app.include_router(operator_strategies.router, prefix="/api/operator")
    return TestClient(app)


def test_operator_lists_strategy_lifecycle_metadata(tmp_path: Path) -> None:
    client = _client(tmp_path)

    response = client.get("/api/operator/strategies")

    assert response.status_code == 200
    payload = response.json()
    assert len(payload) == 1
    assert payload[0]["governance_strategy_id"] == "strategy:1:1"
    assert payload[0]["lifecycle_state"] == "RESEARCH"
    assert payload[0]["code_hash"]


def test_operator_updates_strategy_lifecycle_with_transition_validation(tmp_path: Path) -> None:
    client = _client(tmp_path)

    response = client.post(
        "/api/operator/strategies/strategy%3A1%3A1/lifecycle",
        json={"lifecycle_state": "BACKTEST_QUALIFIED"},
    )

    assert response.status_code == 200
    assert response.json()["lifecycle_state"] == "BACKTEST_QUALIFIED"

    invalid = client.post(
        "/api/operator/strategies/strategy%3A1%3A1/lifecycle",
        json={"lifecycle_state": "LIVE_PRODUCTION"},
    )
    assert invalid.status_code == 400

