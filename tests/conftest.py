from __future__ import annotations

from pathlib import Path

import pytest

from apps.api.routes import edge as edge_routes
from apps.sqlite import SQLiteDatabase
from tests.fixtures.edge_lab_scenarios import ScenarioDataSource, build_edge_lab_scenario_registry


def pytest_configure(config):
    if getattr(config.option, "basetemp", None):
        return
    base = Path(__file__).resolve().parent / "_tmp_pytest"
    base.mkdir(parents=True, exist_ok=True)
    config.option.basetemp = str(base)


@pytest.fixture
def edge_lab_scenario_registry():
    return build_edge_lab_scenario_registry()


@pytest.fixture
def isolated_edge_lab_env(tmp_path, monkeypatch, edge_lab_scenario_registry):
    db_path = tmp_path / "edge_lab_test.db"
    db = SQLiteDatabase(db_path=str(db_path))
    assert db.initialize_database()

    data_source = ScenarioDataSource(edge_lab_scenario_registry)

    monkeypatch.setattr(edge_routes, "db_manager", db)
    monkeypatch.setattr(
        edge_routes,
        "_create_data_source",
        lambda data_source_name, user_id, start_date, end_date, number_of_bars, string_dates=(None, None): data_source,
    )

    return {
      "db": db,
      "data_source": data_source,
      "registry": edge_lab_scenario_registry,
    }
