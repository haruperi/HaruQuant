from __future__ import annotations

from pathlib import Path
import sqlite3

from backend.data.database import apply_pending_migrations, default_migrations_dir


def test_workflow_steps_migration_supports_insert_and_indexes(tmp_path) -> None:
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
            INSERT INTO core_workflow_steps (
                step_id,
                workflow_id,
                step_order,
                step_type,
                assigned_agent,
                input_contract_type,
                input_ref,
                output_contract_type,
                output_ref,
                status,
                started_at,
                latency_ms,
                metadata_json
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                "step_001",
                "wf_001",
                1,
                "reason",
                "strategy_agent",
                "WorkflowIntent",
                "intent_001",
                "WorkflowPlan",
                "plan_001",
                "completed",
                "2026-04-08T10:00:00Z",
                125,
                '{"phase":"reason"}',
            ),
        )
        connection.commit()

        row = connection.execute(
            """
            SELECT step_id, workflow_id, step_order, step_type, status, iteration_no
            FROM core_workflow_steps
            WHERE step_id = ?
            """,
            ("step_001",),
        ).fetchone()
        indexes = {
            item[1]
            for item in connection.execute(
                "PRAGMA index_list('core_workflow_steps')"
            ).fetchall()
        }
    finally:
        connection.close()

    assert row == ("step_001", "wf_001", 1, "reason", "completed", 0)
    assert "ix_core_workflow_steps_workflow_order" in indexes
    assert "ix_core_workflow_steps_agent_started" in indexes
