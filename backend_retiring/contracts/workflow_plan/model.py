"""WorkflowPlan canonical contract models."""

from __future__ import annotations

from enum import Enum
from typing import Any, Literal

from pydantic import (
    AliasChoices,
    BaseModel,
    ConfigDict,
    Field,
    field_validator,
    model_validator,
)

from backend_retiring.contracts.common import CanonicalEnvelope, Originator


class WorkflowPattern(str, Enum):
    """Supported executable workflow patterns."""

    SEQUENTIAL = "sequential"
    ROUTING = "routing"
    PARALLEL = "parallel"
    EVALUATOR_OPTIMIZER = "evaluator_optimizer"
    ORCHESTRATOR_WORKERS = "orchestrator_workers"


class StepFailurePolicy(BaseModel):
    """Failure handling policy for one planned workflow step."""

    model_config = ConfigDict(extra="forbid")

    retry_count: int = Field(default=0, ge=0)
    timeout_seconds: int | None = Field(default=None, gt=0)
    fallback_agent: str | None = Field(default=None, min_length=1)
    compensation_action: str | None = Field(default=None, min_length=1)
    escalation_condition: str | None = Field(default=None, min_length=1)
    critical: bool = True


class WorkflowPhaseStep(BaseModel):
    """One typed, executable step in a workflow plan."""

    model_config = ConfigDict(
        extra="forbid",
        populate_by_name=True,
        str_strip_whitespace=True,
    )

    step_id: str = Field(default="", min_length=0)
    phase: str = Field(min_length=1)
    owner_agent: str = Field(
        validation_alias=AliasChoices("owner_agent", "owner"),
        min_length=1,
    )
    goal: str | None = Field(default=None, min_length=1)
    input_contract_type: str | None = Field(default=None, min_length=1)
    expected_output_contract_type: str = Field(min_length=1)
    depends_on: list[str] = Field(default_factory=list)
    allowed_tools: list[str] = Field(default_factory=list)
    timeout_seconds: int | None = Field(default=None, gt=0)
    failure_policy: StepFailurePolicy = Field(default_factory=StepFailurePolicy)
    metadata: dict[str, Any] = Field(default_factory=dict)

    @model_validator(mode="after")
    def _default_step_id(self) -> "WorkflowPhaseStep":
        if not self.step_id:
            self.step_id = self.phase
        return self


class WorkflowPlanPayload(BaseModel):
    """Payload fields for a formalized executable workflow plan."""

    model_config = ConfigDict(extra="forbid")

    plan_id: str = Field(min_length=1)
    selected_pattern: WorkflowPattern
    phase_steps: list[WorkflowPhaseStep] = Field(min_length=1)
    assigned_agents: list[str] = Field(default_factory=list)
    tool_permissions: dict[str, list[str]] = Field(default_factory=dict)
    success_conditions: list[str] = Field(default_factory=list)
    escalation_conditions: list[str] = Field(default_factory=list)

    @field_validator("selected_pattern", mode="before")
    @classmethod
    def _normalize_pattern(cls, value: object) -> object:
        aliases = {
            "sequential_review": WorkflowPattern.SEQUENTIAL.value,
            "sequential_workflow": WorkflowPattern.SEQUENTIAL.value,
            "parallel_workflow": WorkflowPattern.PARALLEL.value,
            "routing_workflow": WorkflowPattern.ROUTING.value,
            "evaluator-optimizer": WorkflowPattern.EVALUATOR_OPTIMIZER.value,
            "evaluator_optimizer_workflow": WorkflowPattern.EVALUATOR_OPTIMIZER.value,
            "orchestrator-worker": WorkflowPattern.ORCHESTRATOR_WORKERS.value,
            "orchestrator_workers_workflow": WorkflowPattern.ORCHESTRATOR_WORKERS.value,
        }
        if isinstance(value, str):
            return aliases.get(value, value)
        return value


class WorkflowPlan(CanonicalEnvelope):
    """Canonical envelope specialization for WorkflowPlan."""

    contract_type: Literal["WorkflowPlan"] = "WorkflowPlan"
    payload: WorkflowPlanPayload


__all__ = [
    "WorkflowPlan",
    "WorkflowPlanPayload",
    "WorkflowPattern",
    "WorkflowPhaseStep",
    "StepFailurePolicy",
    "Originator",
]
