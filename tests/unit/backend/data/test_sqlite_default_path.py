from __future__ import annotations

from pathlib import Path

from backend.data.database.sqlite.base import DatabaseBase


def test_default_sqlite_path_resolves_to_single_backend_data_database() -> None:
    db_path = Path(DatabaseBase.__new__(DatabaseBase)._get_default_db_path())

    assert db_path.name == "haruquant.db"
    assert db_path.parts[-4:] == ("backend", "data", "database", "haruquant.db")
    assert "backend\\backend" not in str(db_path)
    assert "backend/backend" not in str(db_path)
