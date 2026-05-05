from __future__ import annotations

from pathlib import Path

from backend.agents import ADKRunnerConfig, ADKRunnerService, AgentExecutionResult
from haruquant.utils import ValidationError
from backend.contracts.common import Originator
from backend.contracts.workflow_plan.model import (
    WorkflowPattern,
    WorkflowPhaseStep,
    WorkflowPlan,
    WorkflowPlanPayload,
)
from backend.data.database import WorkflowRepository, apply_pending_migrations, default_migrations_dir
from backend.orchestration.workflow import (
    WorkflowCreateRequest,
    WorkflowCreationService,
    WorkflowPlanExecutor,
    WorkflowRuntimeService,
    WorkflowStepRecorder,
    WorkflowTransitionLogger,
)


class _Runtime:
    def run(self, *, request, context):  # noqa: ANN001
        return AgentExecutionResult(output_payload={"contract_type": "EvaluationReport"})


def test_workflow_creation_service_requires_objective_constraints_and_tools(tmp_path) -> None:
    migrations_dir = default_migrations_dir()
    database_path = tmp_path / "agentic.db"

    apply_pending_migrations(database_path, migrations_dir)
    service = WorkflowCreationService(WorkflowRepository(database_path))

    missing_objective = False
    try:
        service.create_workflow(
            WorkflowCreateRequest(
                workflow_type="trade_review",
                environment="paper",
                operating_mode="MODE-002",
                objective="",
                trigger_type="user_action",
                initiator_type="user",
                initiator_id="operator_001",
                constraints={"symbol": "EURUSD"},
                permitted_tools=["market_data_mcp"],
                required_agents=["StrategyAgent"],
                stop_conditions=["human_escalation"],
                timeout_policy={"ttl_seconds": 900},
                evaluation_criteria=["schema_compliance"],
            )
        )
    except ValidationError as exc:
        missing_objective = exc.code == "workflow_objective_required"

    missing_constraints = False
    try:
        service.create_workflow(
            WorkflowCreateRequest(
                workflow_type="trade_review",
                environment="paper",
                operating_mode="MODE-002",
                objective="Review setup",
                trigger_type="user_action",
                initiator_type="user",
                initiator_id="operator_001",
                constraints={},
                permitted_tools=["market_data_mcp"],
                required_agents=["StrategyAgent"],
                stop_conditions=["human_escalation"],
                timeout_policy={"ttl_seconds": 900},
                evaluation_criteria=["schema_compliance"],
            )
        )
    except ValidationError as exc:
        missing_constraints = exc.code == "workflow_constraints_required"

    missing_tools = False
    try:
        service.create_workflow(
            WorkflowCreateRequest(
                workflow_type="trade_review",
                environment="paper",
                operating_mode="MODE-002",
                objective="Review setup",
                trigger_type="user_action",
                initiator_type="user",
                initiator_id="operator_001",
                constraints={"symbol": "EURUSD"},
                permitted_tools=[],
                required_agents=["StrategyAgent"],
                stop_conditions=["human_escalation"],
                timeout_policy={"ttl_seconds": 900},
                evaluation_criteria=["schema_compliance"],
            )
        )
    except ValidationError as exc:
        missing_tools = exc.code == "workflow_permitted_tools_required"

    assert missing_objective is True
    assert missing_constraints is True
    assert missing_tools is True


def test_workflow_creation_service_persists_valid_request(tmp_path) -> None:
    migrations_dir = default_migrations_dir()
    database_path = tmp_path / "agentic.db"

    apply_pending_migrations(database_path, migrations_dir)
    service = WorkflowCreationService(WorkflowRepository(database_path))

    record = service.create_workflow(
        WorkflowCreateRequest(
            workflow_type="trade_review",
            environment="paper",
            operating_mode="MODE-002",
            objective="Review EURUSD setup",
            trigger_type="user_action",
            initiator_type="user",
            initiator_id="operator_001",
            constraints={"symbol": "EURUSD"},
            permitted_tools=["market_data_mcp"],
            required_agents=["StrategyAgent", "RiskGovernorAgent"],
            stop_conditions=["human_escalation"],
            timeout_policy={"ttl_seconds": 900},
            evaluation_criteria=["schema_compliance", "risk_awareness"],
        )
    )

    assert record.workflow_id.startswith("wf_")
    assert record.state == "CREATED"
    assert '"trigger_type": "user_action"' in record.scope_json


def test_workflow_runtime_service_creates_and_executes_plan(tmp_path) -> None:
    migrations_dir = default_migrations_dir()
    database_path = tmp_path / "agentic.db"

    apply_pending_migrations(database_path, migrations_dir)
    repository = WorkflowRepository(database_path)
    creation_service = WorkflowCreationService(repository)
    executor = WorkflowPlanExecutor(
        runner=ADKRunnerService(ADKRunnerConfig(runner_name="agent-runtime")),
        workflow_repository=repository,
        step_recorder=WorkflowStepRecorder(database_path),
        transition_logger=WorkflowTransitionLogger(repository),
        runtime_agents={"worker_agent": _Runtime()},
    )
    service = WorkflowRuntimeService(creation_service, executor)

    def plan_factory(workflow):
        return WorkflowPlan(
            workflow_id=workflow.workflow_id,
            correlation_id="corr_runtime_001",
            causation_id="evt_runtime_001",
            originator=Originator(type="agent", id="orchestrator_agent"),
            environment="paper",
            operating_mode="MODE-001",
            payload=WorkflowPlanPayload(
                plan_id="plan_runtime_001",
                selected_pattern=WorkflowPattern.SEQUENTIAL,
                phase_steps=[
                    WorkflowPhaseStep(
                        step_id="evaluate",
                        phase="evaluate",
                        owner_agent="worker_agent",
                        input_contract_type="WorkflowIntent",
                        expected_output_contract_type="EvaluationReport",
                    )
                ],
            ),
        )

    result = service.create_and_execute(
        request=WorkflowCreateRequest(
            workflow_type="trade_review",
            environment="paper",
            operating_mode="MODE-001",
            objective="Review EURUSD setup",
            trigger_type="user",
            initiator_type="user",
            initiator_id="operator_001",
            constraints={"symbol": "EURUSD"},
            permitted_tools=["sql_mcp"],
            required_agents=["worker_agent"],
            stop_conditions=["evaluation_complete"],
            evaluation_criteria=["schema_valid"],
        ),
        plan_factory=plan_factory,
    )

    assert result.workflow_id.startswith("wf_")
    assert result.final_state == "FAILED"
