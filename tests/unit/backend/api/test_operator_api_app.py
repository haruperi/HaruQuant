"""Tests for the operator API application skeleton."""

from pathlib import Path

from fastapi.testclient import TestClient

from haruquant.utils import load_runtime_settings_from_mapping
from backend.api import build_operator_api_dependencies, create_app


def test_create_app_wires_operator_dependencies() -> None:
    settings = load_runtime_settings_from_mapping(
        {
            "environment": "test",
            "ui_origin": "http://localhost:3000",
        }
    )
    app = create_app(build_operator_api_dependencies(settings=settings))
    client = TestClient(app)

    response = client.get(
        "/api/operator",
        headers={
            "Authorization": "Bearer test-token",
            "X-HQ-Actor-Id": "user:test",
            "X-HQ-Role": "operator",
        },
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["service"] == "haruquant-operator-api"
    assert payload["environment"] == "test"
    assert payload["schema_registry_contracts"] == 1
    assert payload["policy_bundle_count"] == 0
    assert payload["actor_id"] == "user:test"
    assert payload["role"] == "operator"


def test_operator_api_rejects_missing_bearer_token() -> None:
    settings = load_runtime_settings_from_mapping(
        {
            "environment": "test",
            "ui_origin": "http://localhost:3000",
        }
    )
    app = create_app(build_operator_api_dependencies(settings=settings))
    client = TestClient(app)

    response = client.get("/api/operator")

    assert response.status_code == 401
    assert response.json()["detail"] == "Missing bearer token."


def test_operator_api_rejects_unsupported_role() -> None:
    settings = load_runtime_settings_from_mapping(
        {
            "environment": "test",
            "ui_origin": "http://localhost:3000",
        }
    )
    app = create_app(build_operator_api_dependencies(settings=settings))
    client = TestClient(app)

    response = client.get(
        "/api/operator",
        headers={
            "Authorization": "Bearer test-token",
            "X-HQ-Role": "viewer",
        },
    )

    assert response.status_code == 403
    assert response.json()["detail"] == "Unsupported operator role 'viewer'."


def test_operator_api_health_reports_component_statuses(tmp_path: Path) -> None:
    settings = load_runtime_settings_from_mapping(
        {
            "environment": "test",
            "ui_origin": "http://localhost:3000",
            "database_url": f"sqlite:///{tmp_path / 'operator-health.db'}",
            "event_backend": "inmemory",
        }
    )
    app = create_app(build_operator_api_dependencies(settings=settings))
    client = TestClient(app)

    response = client.get("/api/operator/health")

    assert response.status_code == 200
    payload = response.json()
    assert payload["status"] == "healthy"
    assert payload["components"]["app"]["status"] == "healthy"
    assert payload["components"]["db"]["status"] == "healthy"
    assert payload["components"]["redis"]["status"] == "disabled"
    assert payload["components"]["schema_registry"]["status"] == "healthy"
