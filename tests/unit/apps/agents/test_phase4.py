from __future__ import annotations

import hmac
import json

from fastapi import FastAPI
from fastapi.testclient import TestClient

from apps.agents.core.agent_models import AgentResult
from apps.agents.integrations.n8n_client import N8NClient
from apps.agents.integrations import webhook_router
from apps.api.main import app


def _signature(secret: str, payload: dict) -> str:
    body = json.dumps(payload, separators=(",", ":")).encode("utf-8")
    return "sha256=" + hmac.new(secret.encode("utf-8"), body, "sha256").hexdigest()


def test_n8n_client_queues_signed_local_payload(tmp_path, monkeypatch):
    monkeypatch.setenv("HQT_N8N_WEBHOOK_SECRET", "top-secret")
    client = N8NClient(outbound_dir=tmp_path)

    result = client.trigger_workflow(workflow_name="daily_brief", payload={"ok": True})

    assert result["status"] == "queued_local"
    stored = json.loads((tmp_path / "daily_brief.json").read_text(encoding="utf-8"))
    assert stored["workflow_name"] == "daily_brief"
    assert stored["signature"] is not None


def test_agents_route_is_mounted():
    paths = {route.path for route in app.routes}
    assert "/api/agents/n8n/trigger" in paths


def test_inbound_n8n_trigger_verifies_signature_and_calls_gateway(monkeypatch):
    secret = "phase4-secret"
    monkeypatch.setenv("HQT_N8N_WEBHOOK_SECRET", secret)

    payload = {
        "task_id": "task-1",
        "task_type": "daily_market_brief",
        "actor_user_id": 0,
        "actor_role": "n8n",
        "scope": "edge",
        "intent": "daily_market_brief",
        "correlation_id": "corr-1",
        "run_id": "run-1",
        "input_payload": {"symbol": "EURUSD", "timeframe": "H1"},
        "approval_mode": "auto_read_only",
    }

    class _Gateway:
        planner = type("Planner", (), {"plan": staticmethod(lambda task: type("Plan", (), {"workflow_name": "daily_market_brief"})())})()

        def run_task(self, task):
            return AgentResult(
                status="ok",
                summary="daily brief ready",
                evidence=[{"type": "edge_snapshot", "snapshot_id": 1}],
                metadata={"state": "ok"},
            )

    monkeypatch.setattr(webhook_router, "AgentWorkflowGateway", _Gateway)

    test_app = FastAPI()
    test_app.include_router(webhook_router.router, prefix="/api/agents")
    body = json.dumps(payload, separators=(",", ":")).encode("utf-8")
    with TestClient(test_app) as client:
        response = client.post(
            "/api/agents/n8n/trigger",
            content=body,
            headers={
                "Content-Type": "application/json",
                "X-Haru-Signature": _signature(secret, payload),
            },
        )

    assert response.status_code == 200
    body = response.json()
    assert body["ok"] is True
    assert body["workflow_name"] == "daily_market_brief"


def test_inbound_n8n_trigger_rejects_bad_signature(monkeypatch):
    monkeypatch.setenv("HQT_N8N_WEBHOOK_SECRET", "phase4-secret")
    payload = {
        "task_id": "task-1",
        "task_type": "daily_market_brief",
        "actor_user_id": 0,
        "actor_role": "n8n",
        "scope": "edge",
        "intent": "daily_market_brief",
        "correlation_id": "corr-1",
        "run_id": "run-1",
        "input_payload": {"symbol": "EURUSD", "timeframe": "H1"},
        "approval_mode": "auto_read_only",
    }

    test_app = FastAPI()
    test_app.include_router(webhook_router.router, prefix="/api/agents")
    body = json.dumps(payload, separators=(",", ":")).encode("utf-8")
    with TestClient(test_app) as client:
        response = client.post(
            "/api/agents/n8n/trigger",
            content=body,
            headers={"Content-Type": "application/json", "X-Haru-Signature": "sha256=bad"},
        )

    assert response.status_code == 401
