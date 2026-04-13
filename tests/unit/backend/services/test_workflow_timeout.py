from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path

from backend.common import FixedClock
from backend.data.database import WorkflowRepository, apply_pending_migrations, default_migrations_dir
from backend.services.monitoring.workflow_timeout import WorkflowTimeoutService


def test_workflow_timeout_service_transitions_expired_workflow(tmp_path) -> None:
    migrations_dir = default_migrations_dir()
    database_path = tmp_path / "agentic.db"

    apply_pending_migrations(database_path, migrations_dir)
    repository = WorkflowRepository(database_path)
    workflow = repository.create_workflow(
        workflow_id="wf_001",
        workflow_type="trade_review",
        environment="paper",
        operating_mode="MODE-002",
        state="REASONING",
        objective="Review setup",
        initiator_type="user",
        initiator_id="operator_001",
        timeout_policy_json='{"timeout_seconds": 5}',
    )
    with repository._connect() as connection:  # noqa: SLF001
        connection.execute(
            "UPDATE core_workflows SET updated_at = ? WHERE workflow_id = ?",
            ("2026-04-09T10:00:00Z", "wf_001"),
        )
    workflow = repository.get_workflow("wf_001")

    result = WorkflowTimeoutService(repository).evaluate(
        workflow,
        clock=FixedClock(datetime(2026, 4, 9, 10, 0, 7, tzinfo=timezone.utc)),
    )
    updated = repository.get_workflow("wf_001")

    assert result.timed_out is True
    assert updated is not None
    assert updated.state == "TIMED_OUT"


def test_workflow_timeout_service_leaves_active_workflow_unchanged(tmp_path) -> None:
    migrations_dir = default_migrations_dir()
    database_path = tmp_path / "agentic.db"

    apply_pending_migrations(database_path, migrations_dir)
    repository = WorkflowRepository(database_path)
    workflow = repository.create_workflow(
        workflow_id="wf_001",
        workflow_type="trade_review",
        environment="paper",
        operating_mode="MODE-002",
        state="REASONING",
        objective="Review setup",
        initiator_type="user",
        initiator_id="operator_001",
        timeout_policy_json='{"timeout_seconds": 60}',
    )
    with repository._connect() as connection:  # noqa: SLF001
        connection.execute(
            "UPDATE core_workflows SET updated_at = ? WHERE workflow_id = ?",
            ("2026-04-09T10:00:00Z", "wf_001"),
        )
    workflow = repository.get_workflow("wf_001")

    result = WorkflowTimeoutService(repository).evaluate(
        workflow,
        clock=FixedClock(datetime(2026, 4, 9, 10, 0, 7, tzinfo=timezone.utc)),
    )

    assert result.timed_out is False
    assert repository.get_workflow("wf_001").state == "REASONING"
