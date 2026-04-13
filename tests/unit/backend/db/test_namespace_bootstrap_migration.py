from __future__ import annotations

from pathlib import Path
import sqlite3

from backend.data.database import apply_pending_migrations, default_migrations_dir


def test_namespace_bootstrap_migration_registers_logical_namespaces(tmp_path) -> None:
    migrations_dir = default_migrations_dir()
    database_path = tmp_path / "agentic.db"

    apply_pending_migrations(database_path, migrations_dir)

    connection = sqlite3.connect(database_path)
    try:
        rows = connection.execute(
            """
            SELECT namespace_name, physical_schema, naming_mode
            FROM _logical_namespaces
            ORDER BY namespace_name
            """
        ).fetchall()
    finally:
        connection.close()

    assert rows == [
        ("audit", "main", "single-schema"),
        ("core", "main", "single-schema"),
        ("gov", "main", "single-schema"),
        ("ref", "main", "single-schema"),
        ("research", "main", "single-schema"),
        ("risk", "main", "single-schema"),
    ]
