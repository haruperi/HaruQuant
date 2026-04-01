"""Typed inbound and outbound payload schemas for n8n integration."""

from __future__ import annotations

from typing import Any, Dict, Optional

from pydantic import BaseModel, Field


class AgentWebhookTaskRequest(BaseModel):
    """Inbound task contract used by n8n to trigger one agent workflow."""

    task_id: str
    task_type: str
    actor_user_id: int = 0
    actor_role: str = "system"
    scope: str = "agents"
    intent: str
    correlation_id: str
    run_id: str
    input_payload: Dict[str, Any] = Field(default_factory=dict)
    approval_mode: str = "auto_read_only"


class AgentWebhookTaskResponse(BaseModel):
    """Synchronous response returned to n8n after one workflow run."""

    ok: bool
    workflow_name: str
    status: str
    summary: str
    correlation_id: str
    metadata: Dict[str, Any] = Field(default_factory=dict)


class AgentNotificationPayload(BaseModel):
    """Compact outbound payload sent from HaruQuant into n8n."""

    workflow_name: str
    correlation_id: str
    status: str
    summary: str
    metadata: Dict[str, Any] = Field(default_factory=dict)
    evidence_count: int = 0


class SignedWebhookEnvelope(BaseModel):
    """Local outbox envelope used for outbound webhook delivery."""

    workflow_name: str
    target_url: str
    signature: Optional[str] = None
    payload: Dict[str, Any] = Field(default_factory=dict)
