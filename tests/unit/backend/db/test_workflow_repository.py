from __future__ import annotations

from pathlib import Path

from services.utils import StaleVersionError
from backend.data.database import apply_pending_migrations, default_migrations_dir
from backend.data.database.repositories import WorkflowRepository


def test_workflow_repository_crud_and_optimistic_lock(tmp_path) -> None:
    migrations_dir = default_migrations_dir()
    database_path = tmp_path / "agentic.db"

    apply_pending_migrations(database_path, migrations_dir)
    repository = WorkflowRepository(database_path)

    created = repository.create_workflow(
        workflow_id="wf_001",
        workflow_type="trade_review",
        environment="paper",
        operating_mode="MODE-002",
        state="CREATED",
        objective="Review EURUSD setup",
        initiator_type="user",
        initiator_id="operator_001",
    )
    assert created.workflow_id == "wf_001"
    assert created.version_no == 1

    loaded = repository.get_workflow("wf_001")
    assert loaded is not None
    assert loaded.state == "CREATED"

    updated = repository.update_workflow_state(
        workflow_id="wf_001",
        expected_version=1,
        state="REASONING",
        current_step_id="step_001",
    )
    assert updated.state == "REASONING"
    assert updated.version_no == 2
    assert updated.current_step_id == "step_001"

    transition_id = repository.append_transition(
        workflow_id="wf_001",
        from_state="CREATED",
        to_state="REASONING",
        actor_type="user",
        actor_id="operator_001",
        correlation_id="corr_001",
        phase_name="reason",
    )
    assert transition_id > 0

    stale_failed = False
    try:
        repository.update_workflow_state(
            workflow_id="wf_001",
            expected_version=1,
            state="PLANNING",
        )
    except StaleVersionError:
        stale_failed = True

    assert stale_failed is True
