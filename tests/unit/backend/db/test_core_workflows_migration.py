from __future__ import annotations

from pathlib import Path
import sqlite3

from backend.data.database import apply_pending_migrations, default_migrations_dir


def test_core_workflows_migration_supports_insert_and_select(tmp_path) -> None:
    migrations_dir = default_migrations_dir()
    database_path = tmp_path / "agentic.db"

    apply_pending_migrations(database_path, migrations_dir)

    connection = sqlite3.connect(database_path)
    try:
        connection.execute(
            """
            INSERT INTO core_workflows (
                workflow_id,
                workflow_type,
                environment,
                operating_mode,
                state,
                objective,
                scope_json,
                initiator_type,
                initiator_id,
                timeout_policy_json,
                stop_conditions_json
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                "wf_001",
                "trade_review",
                "paper",
                "MODE-002",
                "CREATED",
                "Review EURUSD setup",
                '{"symbols":["EURUSD"]}',
                "user",
                "operator_001",
                '{"ttl_seconds":900}',
                '["human_escalation"]',
            ),
        )
        connection.commit()

        row = connection.execute(
            """
            SELECT workflow_id, workflow_type, environment, operating_mode, state, version_no
            FROM core_workflows
            WHERE workflow_id = ?
            """,
            ("wf_001",),
        ).fetchone()

        indexes = {
            item[1]
            for item in connection.execute("PRAGMA index_list('core_workflows')").fetchall()
        }
    finally:
        connection.close()

    assert row == ("wf_001", "trade_review", "paper", "MODE-002", "CREATED", 1)
    assert "ix_core_workflows_state_updated" in indexes
    assert "ix_core_workflows_type_created" in indexes
    assert "ix_core_workflows_env_mode_created" in indexes
