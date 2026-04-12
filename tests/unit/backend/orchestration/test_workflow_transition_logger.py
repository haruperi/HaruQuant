from __future__ import annotations

from pathlib import Path
import sqlite3

from backend.data.database import WorkflowRepository, apply_pending_migrations
from backend.orchestration.workflow import (
    WorkflowState,
    WorkflowTransitionEvent,
    WorkflowTransitionLogger,
)


def test_workflow_transition_logger_is_append_only(tmp_path) -> None:
    repo_root = Path(__file__).resolve().parents[4]
    migrations_dir = repo_root / "backend" / "db" / "migrations"
    database_path = tmp_path / "agentic.db"

    apply_pending_migrations(database_path, migrations_dir)
    repository = WorkflowRepository(database_path)
    logger = WorkflowTransitionLogger(repository)

    repository.create_workflow(
        workflow_id="wf_001",
        workflow_type="trade_review",
        environment="paper",
        operating_mode="MODE-002",
        state="CREATED",
        objective="Review EURUSD setup",
        initiator_type="user",
        initiator_id="operator_001",
    )

    first_id = logger.append(
        WorkflowTransitionEvent(
            workflow_id="wf_001",
            from_state=WorkflowState.CREATED,
            to_state=WorkflowState.REASONING,
            actor_type="user",
            actor_id="operator_001",
            correlation_id="corr_001",
            phase_name="reason",
        )
    )
    second_id = logger.append(
        WorkflowTransitionEvent(
            workflow_id="wf_001",
            from_state=WorkflowState.REASONING,
            to_state=WorkflowState.PLANNING,
            actor_type="agent",
            actor_id="orchestrator_agent",
            correlation_id="corr_002",
            phase_name="plan",
        )
    )

    connection = sqlite3.connect(database_path)
    try:
        rows = connection.execute(
            """
            SELECT transition_id, from_state, to_state
            FROM core_workflow_transitions
            WHERE workflow_id = ?
            ORDER BY transition_id
            """,
            ("wf_001",),
        ).fetchall()
    finally:
        connection.close()

    assert first_id > 0
    assert second_id > first_id
    assert rows == [
        (first_id, "CREATED", "REASONING"),
        (second_id, "REASONING", "PLANNING"),
    ]
