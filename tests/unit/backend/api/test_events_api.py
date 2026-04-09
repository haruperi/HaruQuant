from __future__ import annotations

from pathlib import Path

from fastapi.testclient import TestClient

from apps.core.settings import load_runtime_settings_from_mapping
from backend.api import build_operator_api_dependencies, create_app


def test_operator_events_stream_returns_sse_payload(tmp_path: Path) -> None:
    settings = load_runtime_settings_from_mapping(
        {
            "environment": "test",
            "ui_origin": "http://localhost:3000",
            "database_url": f"sqlite:///{tmp_path / 'events-api.db'}",
        }
    )
    app = create_app(build_operator_api_dependencies(settings=settings))
    client = TestClient(app)

    response = client.get("/api/operator/events/stream")

    assert response.status_code == 200
    assert response.headers["content-type"].startswith("text/event-stream")
    assert "wf_trade_review_001 entered RECONCILING" in response.text
