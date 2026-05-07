"""Executive Department contracts owned by the CEO Agent."""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any
from uuid import uuid4

from pydantic import BaseModel, Field


def utc_now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


class CEORequest(BaseModel):
    request_id: str = Field(default_factory=lambda: f"ceo-request-{uuid4()}")
    user_id: str = "operator"
    session_id: str | None = None
    user_message: str
    normalized_task: str | None = None
    attachments: list[dict[str, Any]] = Field(default_factory=list)
    page_context: dict[str, Any] = Field(default_factory=dict)
    workflow_context: dict[str, Any] = Field(default_factory=dict)
    permission_profile: str = "executive_operator_v1"
    constraints: dict[str, Any] = Field(default_factory=dict)
    created_at: str = Field(default_factory=utc_now_iso)


class ExecutiveDecision(BaseModel):
    status: str
    decision_type: str
    decision: str
    confidence: str = "medium"
    risk_level: str = "low"
    allowed_actions: list[str] = Field(default_factory=list)
    blocked_actions: list[str] = Field(default_factory=list)
    reasons: list[str] = Field(default_factory=list)
    required_evidence: list[str] = Field(default_factory=list)
    missing_evidence: list[str] = Field(default_factory=list)
    requires_board_approval: bool = False
    requires_risk_governor: bool = False
    requires_human_confirmation: bool = False


class CEOResponse(BaseModel):
    request_id: str
    agent_name: str = "ceo"
    status: str
    planner_output: dict[str, Any]
    specialist_responses: dict[str, Any] = Field(default_factory=dict)
    evidence_summary: dict[str, Any] = Field(default_factory=dict)
    final_memo: dict[str, Any] | str
    decision: ExecutiveDecision
    allowed_actions: list[str] = Field(default_factory=list)
    blocked_actions: list[str] = Field(default_factory=list)
    required_next_steps: list[str] = Field(default_factory=list)
    board_escalation: dict[str, Any] | None = None
    audit: dict[str, Any] = Field(default_factory=dict)
