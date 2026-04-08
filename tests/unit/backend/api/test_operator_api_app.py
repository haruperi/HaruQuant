"""Tests for the operator API application skeleton."""

from fastapi.testclient import TestClient

from apps.core.settings import load_runtime_settings_from_mapping
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

    response = client.get("/api/operator")

    assert response.status_code == 200
    payload = response.json()
    assert payload["service"] == "haruquant-operator-api"
    assert payload["environment"] == "test"
    assert payload["schema_registry_contracts"] == 1
    assert payload["policy_bundle_count"] == 0
