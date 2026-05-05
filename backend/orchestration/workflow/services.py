"""Workflow creation and persistence services."""

from __future__ import annotations

from dataclasses import dataclass, field
import json

from haruquant.utils import ErrorDescriptor, ValidationError, generate_id
from haruquant.utils import logger
from backend.data.database import WorkflowRecord, WorkflowRepository

from .executor import WorkflowExecutionResult, WorkflowPlanExecutor
from .states import WorkflowState


_WORKFLOW_OBJECTIVE_REQUIRED = ErrorDescriptor(
    code=4050,
    name="WORKFLOW_OBJECTIVE_REQUIRED",
    message="Workflow creation requires a non-empty objective.",
    domain="workflow",
)
_WORKFLOW_CONSTRAINTS_REQUIRED = ErrorDescriptor(
    code=4051,
    name="WORKFLOW_CONSTRAINTS_REQUIRED",
    message="Workflow creation requires declared constraints.",
    domain="workflow",
)
_WORKFLOW_PERMITTED_TOOLS_REQUIRED = ErrorDescriptor(
    code=4052,
    name="WORKFLOW_PERMITTED_TOOLS_REQUIRED",
    message="Workflow creation requires at least one permitted tool.",
    domain="workflow",
)
_WORKFLOW_REQUIRED_AGENTS_REQUIRED = ErrorDescriptor(
    code=4053,
    name="WORKFLOW_REQUIRED_AGENTS_REQUIRED",
    message="Workflow creation requires at least one required agent.",
    domain="workflow",
)
_WORKFLOW_STOP_CONDITIONS_REQUIRED = ErrorDescriptor(
    code=4054,
    name="WORKFLOW_STOP_CONDITIONS_REQUIRED",
    message="Workflow creation requires at least one stop condition.",
    domain="workflow",
)
_WORKFLOW_EVALUATION_CRITERIA_REQUIRED = ErrorDescriptor(
    code=4055,
    name="WORKFLOW_EVALUATION_CRITERIA_REQUIRED",
    message="Workflow creation requires evaluation criteria.",
    domain="workflow",
)
_WORKFLOW_PLAN_ID_MISMATCH = ErrorDescriptor(
    code=4056,
    name="WORKFLOW_PLAN_ID_MISMATCH",
    message="Workflow plan must target the created workflow.",
    domain="workflow",
)


@dataclass(frozen=True)
class WorkflowCreateRequest:
    """Minimum workflow declaration required to start a new workflow."""

    workflow_type: str
    environment: str
    operating_mode: str
    objective: str
    trigger_type: str
    initiator_type: str
    initiator_id: str
    constraints: dict[str, object] = field(default_factory=dict)
    permitted_tools: list[str] = field(default_factory=list)
    required_agents: list[str] = field(default_factory=list)
    stop_conditions: list[str] = field(default_factory=list)
    timeout_policy: dict[str, object] = field(default_factory=dict)
    evaluation_criteria: list[str] = field(default_factory=list)


class WorkflowCreationService:
    """Create workflow records after validating the declared execution envelope."""

    def __init__(self, repository: WorkflowRepository) -> None:
        self.repository = repository

    def create_workflow(self, request: WorkflowCreateRequest) -> WorkflowRecord:
        self._validate_request(request)

        scope_json = json.dumps(
            {
                "trigger_type": request.trigger_type,
                "constraints": request.constraints,
                "permitted_tools": request.permitted_tools,
                "required_agents": request.required_agents,
                "evaluation_criteria": request.evaluation_criteria,
            },
            sort_keys=True,
        )
        timeout_policy_json = json.dumps(request.timeout_policy, sort_keys=True)
        stop_conditions_json = json.dumps(request.stop_conditions)

        return self.repository.create_workflow(
            workflow_id=generate_id("workflow"),
            workflow_type=request.workflow_type,
            environment=request.environment,
            operating_mode=request.operating_mode,
            state=WorkflowState.CREATED.value,
            objective=request.objective,
            scope_json=scope_json,
            initiator_type=request.initiator_type,
            initiator_id=request.initiator_id,
            timeout_policy_json=timeout_policy_json,
            stop_conditions_json=stop_conditions_json,
        )

    @staticmethod
    def _validate_request(request: WorkflowCreateRequest) -> None:
        if not request.objective.strip():
            raise ValidationError(
                _WORKFLOW_OBJECTIVE_REQUIRED,
            )
        if not request.constraints:
            raise ValidationError(
                _WORKFLOW_CONSTRAINTS_REQUIRED,
            )
        if not request.permitted_tools:
            raise ValidationError(
                _WORKFLOW_PERMITTED_TOOLS_REQUIRED,
            )
        if not request.required_agents:
            raise ValidationError(
                _WORKFLOW_REQUIRED_AGENTS_REQUIRED,
            )
        if not request.stop_conditions:
            raise ValidationError(
                _WORKFLOW_STOP_CONDITIONS_REQUIRED,
            )
        if not request.evaluation_criteria:
            raise ValidationError(
                _WORKFLOW_EVALUATION_CRITERIA_REQUIRED,
            )


class WorkflowRuntimeService:
    """Create workflow records and execute validated workflow plans."""

    def __init__(
        self,
        creation_service: WorkflowCreationService,
        executor: WorkflowPlanExecutor,
    ) -> None:
        self.creation_service = creation_service
        self.executor = executor

    def create_and_execute(
        self,
        *,
        request: WorkflowCreateRequest,
        plan_factory,
    ) -> WorkflowExecutionResult:
        workflow = self.creation_service.create_workflow(request)
        plan = plan_factory(workflow)
        if plan.workflow_id != workflow.workflow_id:
            raise ValidationError(
                _WORKFLOW_PLAN_ID_MISMATCH,
                "Workflow plan must target the created workflow: "
                f"{plan.workflow_id} != {workflow.workflow_id}.",
            )
        return self.executor.execute(plan)
