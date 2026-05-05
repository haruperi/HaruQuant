from __future__ import annotations

import sqlite3
from pathlib import Path

import pytest

from data.database import GovernanceRepository, apply_pending_migrations, default_migrations_dir
from data.database.sqlite.database_operations import DatabaseManager
from haruquant.strategy import StrategyStorage
from haruquant.strategy import (
    StrategyCatalogCreateRequest,
    StrategyCatalogService,
    StrategyCatalogUpdateRequest,
    governance_strategy_id,
)
from haruquant.strategy import (
    StrategyPermissionError,
    StrategyRuntimePermissionService,
)


STRATEGY_CODE = """
from haruquant.strategy import BaseStrategy


class StoredDemoStrategy(BaseStrategy):
    def on_init(self):
        pass

    def on_bar(self, data):
        data["entry_signal"] = 0
        data["exit_signal"] = 0
        data["pending_signal"] = 0
        data["cancel_pending_signal"] = 0
        data["price"] = float("nan")
        return data
"""


def _service(tmp_path: Path) -> tuple[StrategyCatalogService, DatabaseManager, GovernanceRepository]:
    db_path = tmp_path / "haruquant.db"
    db = DatabaseManager(db_path=str(db_path))
    db.initialize_database()
    apply_pending_migrations(db_path, default_migrations_dir())
    user_id = db.create_user(
        email="haruperi@example.com",
        username="haruperi",
        password="password",
        full_name="Haru Peri",
    )
    assert user_id == 1
    governance = GovernanceRepository(db_path)
    service = StrategyCatalogService(
        db_manager=db,
        strategy_storage=StrategyStorage(base_dir=str(tmp_path / "strategies")),
        governance_repository=governance,
    )
    return service, db, governance


def test_create_strategy_writes_db_file_metadata_and_governance(tmp_path: Path) -> None:
    service, db, governance = _service(tmp_path)

    strategy = service.create_strategy(
        StrategyCatalogCreateRequest(
            name="EMA Cross",
            description="Demo",
            category="trend",
            code=STRATEGY_CODE,
            parameters={"fast": 12, "slow": 26},
            symbol="EURUSD",
            timeframe="H1",
        ),
        user_id=1,
    )

    assert strategy["id"] == 1
    assert strategy["active_version"] == "1.0.0"
    assert strategy["governance_strategy_id"] == "strategy:1:1"
    assert strategy["lifecycle_state"] == "RESEARCH"
    assert strategy["strategy_family"] == "trend"
    assert Path(strategy["active_file_path"]).exists()
    assert "strategy_1_ema_cross" in strategy["active_file_path"]

    versions = db.get_strategy_versions(1)
    assert len(versions) == 1
    metadata_path = Path(versions[0]["file_path"]).parent / "metadata.json"
    assert metadata_path.exists()

    record = governance.get_strategy("strategy:1:1")
    assert record is not None
    assert record.strategy_name == "EMA Cross"
    assert record.strategy_family == "trend"
    assert record.parameter_hash


def test_update_strategy_code_creates_new_version_and_preserves_loading(tmp_path: Path) -> None:
    service, db, _ = _service(tmp_path)
    service.create_strategy(
        StrategyCatalogCreateRequest(name="Mean Reversion", category="custom", code=STRATEGY_CODE),
        user_id=1,
    )

    updated = service.update_strategy(
        1,
        StrategyCatalogUpdateRequest(
            name="Mean Reversion Renamed",
            code=STRATEGY_CODE.replace("StoredDemoStrategy", "StoredDemoStrategyV2"),
            parameters={"window": 20},
            changelog="rename and update",
        ),
        user_id=1,
    )

    assert updated["name"] == "Mean Reversion Renamed"
    assert updated["active_version"] == "1.0.1"
    versions = db.get_strategy_versions(1)
    assert [item["version"] for item in versions] == ["1.0.1", "1.0.0"]

    active = service.get_version_code(strategy_id=1, version_id=versions[0]["id"], user_id=1)
    assert "StoredDemoStrategyV2" in active["code"]


def test_runtime_permissions_block_live_until_promoted(tmp_path: Path) -> None:
    service, db, governance = _service(tmp_path)
    service.create_strategy(
        StrategyCatalogCreateRequest(name="Research Only", code=STRATEGY_CODE),
        user_id=1,
    )
    permissions = StrategyRuntimePermissionService(db_manager=db, governance_repository=governance)

    permissions.assert_strategy_allowed(strategy_id=1, context="backtest")
    with pytest.raises(StrategyPermissionError):
        permissions.assert_strategy_allowed(strategy_id=1, context="live")

    governance.update_strategy_lifecycle_state(
        strategy_id=governance_strategy_id(1, 1),
        lifecycle_state="LIVE_LIMITED",
    )
    permissions.assert_strategy_allowed(strategy_id=1, context="live")


def test_schema_manager_adds_reconciliation_columns(tmp_path: Path) -> None:
    db = DatabaseManager(db_path=str(tmp_path / "haruquant.db"))
    db.initialize_database()
    with sqlite3.connect(db.db_path) as connection:
        columns = {
            row[1]
            for row in connection.execute("PRAGMA table_info(strategies)").fetchall()
        }
    assert {"governance_strategy_id", "artifact_root", "strategy_family"} <= columns
