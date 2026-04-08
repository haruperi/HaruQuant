"""Workflow creation and persistence services."""

from __future__ import annotations

from dataclasses import dataclass, field
import json

from apps.core import ValidationError, generate_id
from backend.db import WorkflowRecord, WorkflowRepository

from .states import WorkflowState


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
                "workflow_objective_required",
                "Workflow creation requires a non-empty objective.",
            )
        if not request.constraints:
            raise ValidationError(
                "workflow_constraints_required",
                "Workflow creation requires declared constraints.",
            )
        if not request.permitted_tools:
            raise ValidationError(
                "workflow_permitted_tools_required",
                "Workflow creation requires at least one permitted tool.",
            )
        if not request.required_agents:
            raise ValidationError(
                "workflow_required_agents_required",
                "Workflow creation requires at least one required agent.",
            )
        if not request.stop_conditions:
            raise ValidationError(
                "workflow_stop_conditions_required",
                "Workflow creation requires at least one stop condition.",
            )
        if not request.evaluation_criteria:
            raise ValidationError(
                "workflow_evaluation_criteria_required",
                "Workflow creation requires evaluation criteria.",
            )
