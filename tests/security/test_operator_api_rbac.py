from __future__ import annotations

from pathlib import Path

from fastapi.testclient import TestClient

from backend.common.settings import load_runtime_settings_from_mapping
from backend.api import build_operator_api_dependencies, create_app


def _client(tmp_path: Path) -> TestClient:
    settings = load_runtime_settings_from_mapping(
        {
            "environment": "test",
            "ui_origin": "http://localhost:3000",
            "database_url": f"sqlite:///{tmp_path / 'rbac-api.db'}",
        }
    )
    app = create_app(build_operator_api_dependencies(settings=settings))
    return TestClient(app)


def test_operator_api_rbac_covers_public_and_protected_endpoints(tmp_path: Path) -> None:
    client = _client(tmp_path)

    health = client.get("/api/operator/health")
    events = client.get("/api/operator/events/stream")
    live_execution_missing_auth = client.post(
        "/api/operator/approvals/live-execution",
        json={
            "target_ref_id": "exec_001",
            "required_count": 2,
            "expires_at": "2026-04-09T12:00:00Z",
        },
    )
    live_execution_operator = client.post(
        "/api/operator/approvals/live-execution",
        headers={
            "Authorization": "Bearer test-token",
            "X-HQ-Actor-Id": "operator:test",
            "X-HQ-Role": "operator",
        },
        json={
            "target_ref_id": "exec_001",
            "required_count": 2,
            "expires_at": "2026-04-09T12:00:00Z",
        },
    )
    policy_change_operator = client.post(
        "/api/operator/approvals/policy-change",
        headers={
            "Authorization": "Bearer test-token",
            "X-HQ-Actor-Id": "operator:test",
            "X-HQ-Role": "operator",
        },
        json={
            "target_ref_id": "policy_001",
            "required_count": 2,
            "expires_at": "2026-04-09T12:00:00Z",
        },
    )
    policy_change_approver = client.post(
        "/api/operator/approvals/policy-change",
        headers={
            "Authorization": "Bearer test-token",
            "X-HQ-Actor-Id": "approver:test",
            "X-HQ-Role": "approver",
        },
        json={
            "target_ref_id": "policy_001",
            "required_count": 2,
            "expires_at": "2026-04-09T12:00:00Z",
        },
    )

    approval_id = live_execution_operator.json()["approval_id"]
    vote_operator = client.post(
        f"/api/operator/approvals/live-execution/{approval_id}/votes",
        headers={
            "Authorization": "Bearer test-token",
            "X-HQ-Actor-Id": "operator:test",
            "X-HQ-Role": "operator",
        },
        json={"decision": "approve"},
    )
    vote_approver = client.post(
        f"/api/operator/approvals/live-execution/{approval_id}/votes",
        headers={
            "Authorization": "Bearer test-token",
            "X-HQ-Actor-Id": "approver:test",
            "X-HQ-Role": "approver",
        },
        json={"decision": "approve"},
    )

    assert health.status_code == 200
    assert events.status_code == 200
    assert live_execution_missing_auth.status_code == 401
    assert live_execution_operator.status_code == 200
    assert policy_change_operator.status_code == 403
    assert policy_change_approver.status_code == 200
    assert vote_operator.status_code == 403
    assert vote_approver.status_code == 200
