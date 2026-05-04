from __future__ import annotations

from backend.data.database import (
    AgenticFirmRepository,
    apply_pending_migrations,
    default_migrations_dir,
)


def test_agentic_firm_repository_persists_task_evidence_and_audit(tmp_path) -> None:
    database_path = tmp_path / "agentic.db"
    apply_pending_migrations(database_path, default_migrations_dir())
    repository = AgenticFirmRepository(database_path)

    with repository._connect() as connection:  # noqa: SLF001
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
                "wf-1",
                "strategy_creation",
                "paper",
                "MODE-002",
                "CREATED",
                "Create a strategy",
                "{}",
                "user",
                "operator",
                "{}",
                "[]",
            ),
        )

    task = repository.create_agent_task(
        task_id="task-1",
        workflow_id="wf-1",
        title="Create spec",
        description="Create a structured strategy spec",
        owner_agent="strategy_creator",
        expected_output_contract="StrategySpec",
    )
    assert task.workflow_id == "wf-1"
    assert task.status == "pending"

    event = repository.append_agent_task_event(
        task_id="task-1",
        event_type="assigned",
        actor_type="agent",
        actor_id="planner",
        from_status="pending",
        to_status="assigned",
    )
    assert event.task_id == "task-1"
    assert event.to_status == "assigned"

    evidence = repository.create_evidence_ref(
        evidence_id="ev-1",
        evidence_type="research_report",
        workflow_id="wf-1",
        task_id="task-1",
        uri="memory/evidence/ev-1.json",
        content_hash="hash-1",
        source_agent="research",
    )
    assert evidence.source_agent == "research"

    audit = repository.append_audit_log(
        audit_id="audit-1",
        actor_name="planner",
        agent_name="planner",
        action_type="assign_task",
        input_hash="input-hash",
        output_hash="output-hash",
        parent_task_id="task-1",
        workflow_id="wf-1",
        evidence_refs_json='["ev-1"]',
    )
    assert audit.audit_id == "audit-1"
    assert audit.parent_task_id == "task-1"
