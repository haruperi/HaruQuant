from __future__ import annotations

from pathlib import Path
import sqlite3

from backend.data.database import apply_pending_migrations


def test_incidents_migration_enforces_state_enum(tmp_path) -> None:
    repo_root = Path(__file__).resolve().parents[4]
    migrations_dir = repo_root / "backend" / "db" / "migrations"
    database_path = tmp_path / "agentic.db"

    apply_pending_migrations(database_path, migrations_dir)

    connection = sqlite3.connect(database_path)
    try:
        connection.execute(
            "INSERT INTO core_incidents (incident_id, severity, state, alert_type, source, summary, recommended_action, metadata_json) VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
            ("inc_001", "high", "OPEN", "risk_breach", "risk_engine", "Risk threshold exceeded", "Reduce position", '{"ticket":"123"}'),
        )
        connection.commit()
        row = connection.execute(
            "SELECT incident_id, state, severity FROM core_incidents"
        ).fetchone()

        failed = False
        try:
            connection.execute(
                "INSERT INTO core_incidents (incident_id, severity, state, alert_type, source, summary, recommended_action, metadata_json) VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
                ("inc_002", "low", "INVALID", "info", "monitor", "Bad state", None, '{}'),
            )
            connection.commit()
        except sqlite3.IntegrityError:
            failed = True
            connection.rollback()
    finally:
        connection.close()

    assert row == ("inc_001", "OPEN", "high")
    assert failed is True
