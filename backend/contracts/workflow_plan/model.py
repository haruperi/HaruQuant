"""WorkflowPlan canonical contract models."""

from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field

from backend.contracts.common import CanonicalEnvelope, Originator


class WorkflowPlanPayload(BaseModel):
    """Payload fields for a formalized executable workflow plan."""

    model_config = ConfigDict(extra="forbid")

    plan_id: str = Field(min_length=1)
    selected_pattern: str = Field(min_length=1)
    phase_steps: list[dict[str, Any]] = Field(min_length=1)
    assigned_agents: list[str] = Field(default_factory=list)
    tool_permissions: dict[str, list[str]] = Field(default_factory=dict)
    success_conditions: list[str] = Field(default_factory=list)
    escalation_conditions: list[str] = Field(default_factory=list)


class WorkflowPlan(CanonicalEnvelope):
    """Canonical envelope specialization for WorkflowPlan."""

    contract_type: Literal["WorkflowPlan"] = "WorkflowPlan"
    payload: WorkflowPlanPayload


__all__ = [
    "WorkflowPlan",
    "WorkflowPlanPayload",
    "Originator",
]
