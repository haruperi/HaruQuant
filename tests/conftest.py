from __future__ import annotations

from pathlib import Path
import shutil
import sys
import uuid

import pytest

from backend.api.legacy.routes import edge as edge_routes
from backend.db.sqlite import SQLiteDatabase
from tests.fixtures.edge_lab_scenarios import ScenarioDataSource, build_edge_lab_scenario_registry


def pytest_configure(config):
    sys.dont_write_bytecode = True

    # Pytest's Windows temp-path plugin is intermittently unreadable in this
    # environment during fixture setup/session cleanup. The tests below only
    # need disposable directories, so we neutralize that cleanup hook and
    # provide our own repo-owned tmp_path fixture.
    try:
        import _pytest.pathlib
        import _pytest.tmpdir

        _pytest.pathlib.cleanup_dead_symlinks = lambda root: None
        _pytest.tmpdir.cleanup_dead_symlinks = lambda root: None
    except Exception:
        pass


@pytest.fixture
def tmp_path():
    base = Path(__file__).resolve().parents[1] / ".tmp_pytest_runtime"
    base.mkdir(parents=True, exist_ok=True)
    path = (base.resolve() / f"haruquant-pytest-{uuid.uuid4().hex}").resolve()
    path.mkdir(parents=True, exist_ok=True)
    try:
        yield path
    finally:
        shutil.rmtree(path, ignore_errors=True)


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
