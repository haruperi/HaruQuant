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


def test_policy_change_approval_requires_dual_authorization(tmp_path: Path) -> None:
    settings = load_runtime_settings_from_mapping(
        {
            "environment": "test",
            "ui_origin": "http://localhost:3000",
            "database_url": f"sqlite:///{tmp_path / 'approval-api.db'}",
        }
    )
    app = create_app(build_operator_api_dependencies(settings=settings))
    client = TestClient(app)

    single_auth = client.post(
        "/api/operator/approvals/policy-change",
        headers={
            "Authorization": "Bearer test-token",
            "X-HQ-Actor-Id": "approver:test",
            "X-HQ-Role": "approver",
        },
        json={
            "target_ref_id": "policy_001",
            "required_count": 1,
            "expires_at": "2026-04-09T12:00:00Z",
        },
    )
    dual_auth = client.post(
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

    assert single_auth.status_code == 400
    assert dual_auth.status_code == 200


def test_override_approval_enforces_expiry_and_rationale(tmp_path: Path) -> None:
    settings = load_runtime_settings_from_mapping(
        {
            "environment": "test",
            "ui_origin": "http://localhost:3000",
            "database_url": f"sqlite:///{tmp_path / 'approval-api.db'}",
        }
    )
    app = create_app(build_operator_api_dependencies(settings=settings))
    client = TestClient(app)

    missing_rationale = client.post(
        "/api/operator/approvals/override",
        headers={
            "Authorization": "Bearer test-token",
            "X-HQ-Actor-Id": "operator:test",
            "X-HQ-Role": "operator",
        },
        json={
            "original_decision_ref": "risk_001",
            "original_action_ref": "exec_001",
            "requested_action": {"action": "force_send"},
            "reason_code": "manual_override",
            "rationale": "",
            "requested_expiry": "2026-04-09T12:00:00Z",
        },
    )
    valid = client.post(
        "/api/operator/approvals/override",
        headers={
            "Authorization": "Bearer test-token",
            "X-HQ-Actor-Id": "operator:test",
            "X-HQ-Role": "operator",
        },
        json={
            "original_decision_ref": "risk_001",
            "original_action_ref": "exec_001",
            "requested_action": {"action": "force_send"},
            "reason_code": "manual_override",
            "rationale": "Operator accepts bounded temporary override.",
            "requested_expiry": "2026-04-09T12:00:00Z",
            "required_roles": ["approver"],
        },
    )

    assert missing_rationale.status_code == 422
    assert valid.status_code == 200


def test_kill_switch_recovery_approval_requires_dual_auth_roles(tmp_path: Path) -> None:
    settings = load_runtime_settings_from_mapping(
        {
            "environment": "test",
            "ui_origin": "http://localhost:3000",
            "database_url": f"sqlite:///{tmp_path / 'approval-api.db'}",
        }
    )
    app = create_app(build_operator_api_dependencies(settings=settings))
    client = TestClient(app)

    invalid = client.post(
        "/api/operator/approvals/kill-switch-recovery",
        headers={
            "Authorization": "Bearer test-token",
            "X-HQ-Actor-Id": "approver:test",
            "X-HQ-Role": "approver",
        },
        json={
            "target_ref_id": "kill_001",
            "expires_at": "2026-04-09T12:00:00Z",
            "required_roles": ["risk_manager"],
        },
    )
    valid = client.post(
        "/api/operator/approvals/kill-switch-recovery",
        headers={
            "Authorization": "Bearer test-token",
            "X-HQ-Actor-Id": "approver:test",
            "X-HQ-Role": "approver",
        },
        json={
            "target_ref_id": "kill_001",
            "expires_at": "2026-04-09T12:00:00Z",
            "required_roles": ["risk_manager", "compliance"],
        },
    )

    assert invalid.status_code == 400
    assert valid.status_code == 200
