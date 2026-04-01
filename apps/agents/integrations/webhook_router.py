"""Inbound webhook router for n8n-triggered agent workflows."""

from __future__ import annotations

import hmac
import json
import os

from fastapi import APIRouter, Header, HTTPException, Request

from apps.agents.core.agent_models import AgentTask
from apps.agents.core.gateway import AgentWorkflowGateway
from apps.agents.core.policies import load_agent_settings
from apps.agents.integrations.n8n_models import (
    AgentWebhookTaskRequest,
    AgentWebhookTaskResponse,
)

router = APIRouter()


def _verify_signature(raw_body: bytes, signature: str | None) -> None:
    settings = load_agent_settings("config/agent_settings.json")
    if not settings.n8n.require_signature:
        return
    secret = os.environ.get(settings.n8n.shared_secret_env, "")
    if not secret:
        raise HTTPException(status_code=503, detail="n8n webhook secret is not configured")
    if not signature:
        raise HTTPException(status_code=401, detail="Missing webhook signature")
    expected = "sha256=" + hmac.new(secret.encode("utf-8"), raw_body, "sha256").hexdigest()
    if not hmac.compare_digest(expected, signature):
        raise HTTPException(status_code=401, detail="Invalid webhook signature")


@router.post("/n8n/trigger", response_model=AgentWebhookTaskResponse)
async def trigger_agent_workflow(
    request: Request,
    x_haru_signature: str | None = Header(default=None),
):
    """Receive one signed n8n webhook and execute the requested agent workflow."""
    raw_body = await request.body()
    _verify_signature(raw_body, x_haru_signature)
    payload = AgentWebhookTaskRequest.model_validate(json.loads(raw_body.decode("utf-8")))
    task = AgentTask(
        task_id=payload.task_id,
        task_type=payload.task_type,
        actor_user_id=payload.actor_user_id,
        actor_role=payload.actor_role,
        scope=payload.scope,
        intent=payload.intent,
        input_payload=payload.input_payload,
        correlation_id=payload.correlation_id,
        run_id=payload.run_id,
        approval_mode=payload.approval_mode,
    )
    gateway = AgentWorkflowGateway()
    result = gateway.run_task(task)
    workflow_name = gateway.planner.plan(task).workflow_name
    return AgentWebhookTaskResponse(
        ok=result.status == "ok",
        workflow_name=workflow_name,
        status=result.status,
        summary=result.summary,
        correlation_id=task.correlation_id,
        metadata=dict(result.metadata or {}),
    )
