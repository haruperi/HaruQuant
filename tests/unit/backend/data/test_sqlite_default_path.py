from __future__ import annotations

from pathlib import Path

from data.database.sqlite.base import DatabaseBase


def test_default_sqlite_path_resolves_to_root_data_database() -> None:
    db_path = Path(DatabaseBase.__new__(DatabaseBase)._get_default_db_path())

    assert db_path.name == "haruquant.db"
    assert db_path.parts[-3:] == ("data", "database", "haruquant.db")
    assert "backend_retiring\\data" not in str(db_path)
    assert "backend_retiring/data" not in str(db_path)
