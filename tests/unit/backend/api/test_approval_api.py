from __future__ import annotations

from pathlib import Path

from fastapi.testclient import TestClient

from apps.core.settings import load_runtime_settings_from_mapping
from backend.api import build_operator_api_dependencies, create_app


def test_live_execution_approval_create_endpoint_requires_operator_auth(tmp_path: Path) -> None:
    settings = load_runtime_settings_from_mapping(
        {
            "environment": "test",
            "ui_origin": "http://localhost:3000",
            "database_url": f"sqlite:///{tmp_path / 'approval-api.db'}",
        }
    )
    app = create_app(build_operator_api_dependencies(settings=settings))
    client = TestClient(app)

    response = client.post(
        "/api/operator/approvals/live-execution",
        json={
            "target_ref_id": "exec_001",
            "required_count": 2,
            "expires_at": "2026-04-09T12:00:00Z",
        },
    )

    assert response.status_code == 401


def test_live_execution_approval_vote_endpoint_requires_approver_role(tmp_path: Path) -> None:
    settings = load_runtime_settings_from_mapping(
        {
            "environment": "test",
            "ui_origin": "http://localhost:3000",
            "database_url": f"sqlite:///{tmp_path / 'approval-api.db'}",
        }
    )
    app = create_app(build_operator_api_dependencies(settings=settings))
    client = TestClient(app)

    create_response = client.post(
        "/api/operator/approvals/live-execution",
        headers={
            "Authorization": "Bearer test-token",
            "X-HQ-Actor-Id": "user:test",
            "X-HQ-Role": "operator",
        },
        json={
            "target_ref_id": "exec_001",
            "required_count": 2,
            "expires_at": "2026-04-09T12:00:00Z",
        },
    )
    approval_id = create_response.json()["approval_id"]

    forbidden = client.post(
        f"/api/operator/approvals/live-execution/{approval_id}/votes",
        headers={
            "Authorization": "Bearer test-token",
            "X-HQ-Actor-Id": "user:test",
            "X-HQ-Role": "operator",
        },
        json={"decision": "approve"},
    )
    allowed = client.post(
        f"/api/operator/approvals/live-execution/{approval_id}/votes",
        headers={
            "Authorization": "Bearer test-token",
            "X-HQ-Actor-Id": "approver:test",
            "X-HQ-Role": "approver",
        },
        json={"decision": "approve"},
    )

    assert forbidden.status_code == 403
    assert allowed.status_code == 200
