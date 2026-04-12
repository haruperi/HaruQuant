from __future__ import annotations

from pathlib import Path
import sqlite3

from backend.data.database import apply_pending_migrations


def test_observations_migration_supports_severity_and_source_queries(tmp_path) -> None:
    repo_root = Path(__file__).resolve().parents[4]
    migrations_dir = repo_root / "backend" / "db" / "migrations"
    database_path = tmp_path / "agentic.db"

    apply_pending_migrations(database_path, migrations_dir)

    connection = sqlite3.connect(database_path)
    try:
        connection.execute("PRAGMA foreign_keys = ON")
        connection.execute(
            "INSERT INTO core_workflows (workflow_id, workflow_type, environment, operating_mode, state, objective, scope_json, initiator_type, initiator_id, timeout_policy_json, stop_conditions_json) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
            ("wf_001", "trade_review", "paper", "MODE-002", "CREATED", "Review setup", "{}", "user", "operator_001", "{}", "[]"),
        )
        connection.execute(
            "INSERT INTO core_observations (observation_id, workflow_id, observation_type, severity, source, payload_ref, payload_json, authority_state, freshness_status) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)",
            ("obs_001", "wf_001", "risk_signal", "warning", "risk_engine", "payload_001", '{"value":42}', "authoritative", "fresh"),
        )
        connection.commit()

        row = connection.execute(
            "SELECT observation_id, severity, source FROM core_observations"
        ).fetchone()
    finally:
        connection.close()

    assert row == ("obs_001", "warning", "risk_engine")
