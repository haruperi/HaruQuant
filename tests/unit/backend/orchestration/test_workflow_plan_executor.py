from __future__ import annotations

from pathlib import Path

from backend_retiring.agents import (
    ADKRunnerConfig,
    ADKRunnerService,
    AgentExecutionResult,
    RuntimeTrajectoryLogService,
)
from contracts.common import Originator
from contracts.workflow_plan.model import (
    WorkflowPattern,
    WorkflowPhaseStep,
    WorkflowPlan,
    WorkflowPlanPayload,
)
from data.database import (
    ResearchAuditRepository,
    WorkflowRepository,
    apply_pending_migrations,
    default_migrations_dir,
)
from backend_retiring.read_models.operator_dashboard import build_workflow_trajectory_read_model
from backend_retiring.orchestration.workflow import (
    WorkflowPlanExecutor,
    WorkflowStepRecorder,
    WorkflowTransitionLogger,
)


class _Runtime:
    def run(self, *, request, context):  # noqa: ANN001
        return AgentExecutionResult(
            output_payload={
                "contract_type": request.input_payload["expected_contract_type"],
                "schema_version": "1.0.0",
                "step_id": request.metadata["step_id"],
            }
        )


def _plan() -> WorkflowPlan:
    phases = (
        ("step_reason", "reason", "ObservationEvent"),
        ("step_plan", "plan", "WorkflowPlan"),
        ("step_act", "act", "ExecutionIntent"),
        ("step_observe", "observe", "ObservationEvent"),
        ("step_evaluate", "evaluate", "EvaluationReport"),
    )
    return WorkflowPlan(
        workflow_id="wf_executor_001",
        correlation_id="corr_executor_001",
        causation_id="evt_executor_001",
        originator=Originator(type="agent", id="orchestrator_agent"),
        environment="paper",
        operating_mode="MODE-001",
        payload=WorkflowPlanPayload(
            plan_id="plan_executor_001",
            selected_pattern=WorkflowPattern.SEQUENTIAL,
            phase_steps=[
                WorkflowPhaseStep(
                    step_id=step_id,
                    phase=phase,
                    owner_agent="worker_agent",
                    input_contract_type="WorkflowIntent",
                    expected_output_contract_type=contract_type,
                    metadata={
                        "input_payload": {
                            "contract_type": "WorkflowIntent",
                            "schema_version": "1.0.0",
                            "expected_contract_type": contract_type,
                        }
                    },
                )
                for step_id, phase, contract_type in phases
            ],
        ),
    )


def test_workflow_plan_executor_records_steps_and_completes(tmp_path) -> None:
    database_path = Path(tmp_path) / "agentic.db"
    apply_pending_migrations(database_path, default_migrations_dir())
    repository = WorkflowRepository(database_path)
    repository.create_workflow(
        workflow_id="wf_executor_001",
        workflow_type="trade_review",
        environment="paper",
        operating_mode="MODE-001",
        state="CREATED",
        objective="Execute typed workflow plan",
        initiator_type="user",
        initiator_id="operator_001",
    )
    executor = WorkflowPlanExecutor(
        runner=ADKRunnerService(ADKRunnerConfig(runner_name="agent-runtime")),
        workflow_repository=repository,
        step_recorder=WorkflowStepRecorder(database_path),
        transition_logger=WorkflowTransitionLogger(repository),
        runtime_agents={"worker_agent": _Runtime()},
    )

    result = executor.execute(_plan())

    assert result.final_state == "COMPLETED"
    assert len(result.steps) == 5
    assert result.failed_steps == ()
    assert result.trace_id
    assert result.spans
    assert all(step.input_ref.startswith("artifact://workflow/") for step in result.steps)
    assert all(step.output_ref.startswith("artifact://workflow/") for step in result.steps)
    assert repository.get_workflow("wf_executor_001").state == "COMPLETED"


def test_workflow_plan_executor_persists_trajectory_and_evaluations(tmp_path) -> None:
    database_path = Path(tmp_path) / "agentic.db"
    apply_pending_migrations(database_path, default_migrations_dir())
    workflow_repository = WorkflowRepository(database_path)
    audit_repository = ResearchAuditRepository(database_path)
    workflow_repository.create_workflow(
        workflow_id="wf_eval_001",
        workflow_type="trade_review",
        environment="paper",
        operating_mode="MODE-001",
        state="CREATED",
        objective="Run evaluator optimizer",
        initiator_type="user",
        initiator_id="operator_001",
    )

    plan = WorkflowPlan(
        workflow_id="wf_eval_001",
        correlation_id="corr_eval_001",
        causation_id="evt_eval_001",
        originator=Originator(type="agent", id="orchestrator_agent"),
        environment="paper",
        operating_mode="MODE-001",
        payload=WorkflowPlanPayload(
            plan_id="plan_eval_001",
            selected_pattern=WorkflowPattern.EVALUATOR_OPTIMIZER,
            phase_steps=[
                WorkflowPhaseStep(
                    step_id="optimize_report",
                    phase="evaluate",
                    owner_agent="worker_agent",
                    input_contract_type="WorkflowIntent",
                    expected_output_contract_type="EvaluationReport",
                    metadata={
                        "acceptance_threshold": 0.8,
                        "max_iterations": 2,
                        "input_payload": {
                            "contract_type": "WorkflowIntent",
                            "schema_version": "1.0.0",
                            "expected_contract_type": "EvaluationReport",
                        },
                    },
                )
            ],
        ),
    )
    scores = iter((0.4, 0.9))
    executor = WorkflowPlanExecutor(
        runner=ADKRunnerService(ADKRunnerConfig(runner_name="agent-runtime")),
        workflow_repository=workflow_repository,
        step_recorder=WorkflowStepRecorder(database_path),
        transition_logger=WorkflowTransitionLogger(workflow_repository),
        runtime_agents={"worker_agent": _Runtime()},
        trajectory_log_service=RuntimeTrajectoryLogService(audit_repository),
        research_audit_repository=audit_repository,
        evaluator_by_step_id={"optimize_report": lambda result: next(scores)},
    )

    result = executor.execute(plan)
    trajectory = build_workflow_trajectory_read_model(
        database_path,
        workflow_id="wf_eval_001",
    )

    assert result.final_state == "FAILED"
    assert len(trajectory.steps) == 1
    assert len(trajectory.trajectory_logs) == 1
    assert len(trajectory.evaluation_reports) == 2
