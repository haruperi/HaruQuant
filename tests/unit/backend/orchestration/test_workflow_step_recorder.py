from __future__ import annotations

from pathlib import Path

from data.database import WorkflowRepository, apply_pending_migrations, default_migrations_dir
from backend_retiring.orchestration.workflow import WorkflowStepRecorder, WorkflowStepRequest


def test_workflow_step_recorder_persists_steps_in_order(tmp_path) -> None:
    migrations_dir = default_migrations_dir()
    database_path = tmp_path / "agentic.db"

    apply_pending_migrations(database_path, migrations_dir)
    workflow_repository = WorkflowRepository(database_path)
    recorder = WorkflowStepRecorder(database_path)

    workflow_repository.create_workflow(
        workflow_id="wf_001",
        workflow_type="trade_review",
        environment="paper",
        operating_mode="MODE-002",
        state="CREATED",
        objective="Review EURUSD setup",
        initiator_type="user",
        initiator_id="operator_001",
    )

    first = recorder.record(
        WorkflowStepRequest(
            step_id="step_001",
            workflow_id="wf_001",
            step_type="reason",
            status="completed",
            assigned_agent="strategy_agent",
            input_contract_type="WorkflowIntent",
            input_ref="intent_001",
            output_contract_type="WorkflowPlan",
            output_ref="plan_001",
        )
    )
    second = recorder.record(
        WorkflowStepRequest(
            step_id="step_002",
            workflow_id="wf_001",
            step_type="plan",
            status="completed",
            assigned_agent="orchestrator_agent",
            input_contract_type="WorkflowPlan",
            input_ref="plan_001",
            output_contract_type="TradeProposal",
            output_ref="prop_001",
        )
    )

    assert first.step_order == 1
    assert second.step_order == 2
    assert second.workflow_id == "wf_001"
