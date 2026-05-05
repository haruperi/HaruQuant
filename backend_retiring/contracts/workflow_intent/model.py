"""WorkflowIntent canonical contract models."""

from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field

from backend_retiring.contracts.common import CanonicalEnvelope, Originator


WorkflowType = Literal[
    "trade_review",
    "portfolio_opt",
    "research_report",
    "paper_execution",
    "live_execution",
    "incident_triage",
    "promotion_review",
    "emergency_exit",
]

TriggerType = Literal["user_action", "schedule", "market_event", "internal_event"]


class WorkflowIntentPayload(BaseModel):
    """Payload fields for a workflow start or resume request."""

    model_config = ConfigDict(extra="forbid")

    objective: str = Field(min_length=1)
    workflow_type: WorkflowType
    trigger_type: TriggerType
    requested_scope: dict[str, Any]
    constraints: dict[str, Any] = Field(default_factory=dict)
    permitted_tools: list[str] = Field(default_factory=list)
    stop_conditions: list[str] = Field(default_factory=list)
    timeout_policy: dict[str, Any] = Field(default_factory=dict)
    evaluation_criteria: list[str] = Field(default_factory=list)


class WorkflowIntent(CanonicalEnvelope):
    """Canonical envelope specialization for WorkflowIntent."""

    contract_type: Literal["WorkflowIntent"] = "WorkflowIntent"
    payload: WorkflowIntentPayload


__all__ = [
    "TriggerType",
    "WorkflowIntent",
    "WorkflowIntentPayload",
    "WorkflowType",
    "Originator",
]
