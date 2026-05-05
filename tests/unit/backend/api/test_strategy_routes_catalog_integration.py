from __future__ import annotations

from pathlib import Path

from fastapi import FastAPI
from fastapi.testclient import TestClient

from backend.api.routes import strategies
from backend.data.database import GovernanceRepository, apply_pending_migrations, default_migrations_dir
from backend.data.database.sqlite.database_operations import DatabaseManager
from services.strategy import StrategyStorage
from services.strategy.catalog import StrategyCatalogService


STRATEGY_CODE = """
from services.strategy import BaseStrategy


class ApiCreatedStrategy(BaseStrategy):
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
        email="api@example.com",
        username="api_user",
        password="password",
    )
    service = StrategyCatalogService(
        db_manager=db,
        strategy_storage=StrategyStorage(base_dir=str(tmp_path / "strategies")),
        governance_repository=GovernanceRepository(db_path),
    )

    strategies.db_manager = db
    strategies.catalog_service = service
    app = FastAPI()
    app.include_router(strategies.router, prefix="/api/strategies")
    return TestClient(app)


def test_strategy_api_create_list_and_get_version_code(tmp_path: Path) -> None:
    client = _client(tmp_path)

    created = client.post(
        "/api/strategies/",
        json={
            "name": "API Strategy",
            "description": "created through route",
            "category": "custom",
            "code": STRATEGY_CODE,
            "parameters": {"window": 14},
        },
    )

    assert created.status_code == 201
    strategy = created.json()
    assert strategy["governance_strategy_id"] == "strategy:1:1"
    assert strategy["lifecycle_state"] == "RESEARCH"
    assert strategy["active_version"] == "1.0.0"

    listed = client.get("/api/strategies/")
    assert listed.status_code == 200
    assert listed.json()[0]["name"] == "API Strategy"

    code = client.get(f"/api/strategies/1/versions/{strategy['active_version_id']}/code")
    assert code.status_code == 200
    assert "ApiCreatedStrategy" in code.json()["code"]
    assert code.json()["parameters"] == {"window": 14}

