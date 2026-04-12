from __future__ import annotations

import sqlite3

from backend.data.database import apply_pending_migrations


def test_apply_pending_migrations_is_idempotent(tmp_path) -> None:
    migrations_dir = tmp_path / "migrations"
    migrations_dir.mkdir()
    database_path = tmp_path / "agentic.db"

    (migrations_dir / "0001_create_workflows.sql").write_text(
        """
        CREATE TABLE workflows (
            workflow_id TEXT PRIMARY KEY,
            status TEXT NOT NULL
        );
        """,
        encoding="utf-8",
    )
    (migrations_dir / "0002_create_events.sql").write_text(
        """
        CREATE TABLE events (
            event_id TEXT PRIMARY KEY,
            workflow_id TEXT NOT NULL
        );
        """,
        encoding="utf-8",
    )

    applied = apply_pending_migrations(database_path, migrations_dir)
    assert [record.version for record in applied] == ["0001", "0002"]

    applied_again = apply_pending_migrations(database_path, migrations_dir)
    assert applied_again == []

    connection = sqlite3.connect(database_path)
    try:
        tables = {
            row[0]
            for row in connection.execute(
                "SELECT name FROM sqlite_master WHERE type = 'table'"
            ).fetchall()
        }
        assert "workflows" in tables
        assert "events" in tables

        history_rows = connection.execute(
            "SELECT version FROM _schema_migrations ORDER BY version"
        ).fetchall()
        assert history_rows == [("0001",), ("0002",)]
    finally:
        connection.close()
