from __future__ import annotations

from pathlib import Path
import sqlite3

from data.database import apply_pending_migrations, default_migrations_dir


def test_workflow_transitions_migration_creates_fk_and_indexes(tmp_path) -> None:
    migrations_dir = default_migrations_dir()
    database_path = tmp_path / "agentic.db"

    apply_pending_migrations(database_path, migrations_dir)

    connection = sqlite3.connect(database_path)
    try:
        connection.execute("PRAGMA foreign_keys = ON")
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
                "{}",
                "user",
                "operator_001",
                "{}",
                "[]",
            ),
        )
        connection.execute(
            """
            INSERT INTO core_workflow_transitions (
                workflow_id,
                from_state,
                to_state,
                phase_name,
                transition_reason,
                actor_type,
                actor_id,
                correlation_id,
                causation_id,
                metadata_json
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                "wf_001",
                "CREATED",
                "REASONING",
                "reason",
                "workflow_started",
                "user",
                "operator_001",
                "corr_001",
                "cause_001",
                '{"source":"test"}',
            ),
        )
        connection.commit()

        row = connection.execute(
            """
            SELECT workflow_id, from_state, to_state, correlation_id
            FROM core_workflow_transitions
            """
        ).fetchone()
        foreign_keys = connection.execute(
            "PRAGMA foreign_key_list('core_workflow_transitions')"
        ).fetchall()
        indexes = {
            item[1]
            for item in connection.execute(
                "PRAGMA index_list('core_workflow_transitions')"
            ).fetchall()
        }
    finally:
        connection.close()

    assert row == ("wf_001", "CREATED", "REASONING", "corr_001")
    assert any(fk[2] == "core_workflows" and fk[3] == "workflow_id" for fk in foreign_keys)
    assert "ix_core_workflow_transitions_workflow_occurred" in indexes
    assert "ix_core_workflow_transitions_correlation" in indexes
    assert "ix_core_workflow_transitions_to_state_occurred" in indexes
