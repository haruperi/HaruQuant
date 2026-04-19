from __future__ import annotations

from fastapi.testclient import TestClient

from backend.api.main import app


def test_ai_chat_phase0_contracts_endpoint_exposes_frozen_contracts():
    client = TestClient(app)

    response = client.get("/api/ai-chat/phase0/contracts")

    assert response.status_code == 200
    payload = response.json()
    assert payload["feature"] == "haruquant_ai_chatbot"
    assert payload["contracts"]["page_context"] == "PageContextPacket@1.0.0"
    assert "generic" in payload["supported_page_types"]


def test_ai_chat_phase0_route_contexts_endpoint_exposes_registry():
    client = TestClient(app)

    response = client.get("/api/ai-chat/phase0/route-contexts")

    assert response.status_code == 200
    payload = response.json()
    assert any(item["page_type"] == "strategy_detail" for item in payload)
