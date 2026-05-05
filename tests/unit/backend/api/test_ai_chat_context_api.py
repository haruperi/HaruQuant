from __future__ import annotations

from fastapi.testclient import TestClient

from backend_retiring.api.auth_utils import get_user_id_from_token
from backend_retiring.api.main import app
from backend_retiring.api.routes.ai_chat import get_page_context_assembler
from data.database import apply_pending_migrations, default_migrations_dir
from data.database.sqlite.database_operations import DatabaseManager
from backend_retiring.agents.chat.ai_chat import PageContextAssembler


def test_ai_chat_context_endpoint_returns_route_aware_packet(tmp_path) -> None:
    database_path = tmp_path / "agentic.db"
    db = DatabaseManager(db_path=str(database_path))
    db.initialize_database()
    apply_pending_migrations(database_path, default_migrations_dir())
    db.create_user(email="api-ctx@example.com", username="api_ctx_user", password="password")

    app.dependency_overrides[get_page_context_assembler] = lambda: PageContextAssembler(db_manager=db)
    app.dependency_overrides[get_user_id_from_token] = lambda: 1
    client = TestClient(app)

    response = client.get("/api/ai-chat/context", params={"route": "/dashboard"})

    assert response.status_code == 200
    payload = response.json()["payload"]
    assert payload["page_type"] == "dashboard"
    assert payload["authority"]["trust_level"] == "system_state"

    app.dependency_overrides.clear()


def test_ai_chat_context_resolve_endpoint_accepts_dom_fallback(tmp_path) -> None:
    database_path = tmp_path / "agentic_resolve.db"
    db = DatabaseManager(db_path=str(database_path))
    db.initialize_database()
    apply_pending_migrations(database_path, default_migrations_dir())
    db.create_user(email="api-resolve@example.com", username="api_resolve_user", password="password")

    app.dependency_overrides[get_page_context_assembler] = lambda: PageContextAssembler(db_manager=db)
    app.dependency_overrides[get_user_id_from_token] = lambda: 1
    client = TestClient(app)

    response = client.post(
        "/api/ai-chat/context/resolve",
        json={
            "route": "/documentation/fundamentals",
            "page_title": "Documentation",
            "page_state": {
                "page_type_hint": "generic",
            },
            "dom": {
                "title": "Documentation",
                "headings": ["Documentation", "Fundamentals", "Order Types"],
                "text_excerpt": "This page explains order types and execution constraints.",
                "semantic_blocks": [
                    {
                        "id": "doc:order-types",
                        "blockType": "text",
                        "title": "Order Types",
                        "summary": "Order types and execution constraints.",
                    }
                ],
            },
        },
    )

    assert response.status_code == 200
    payload = response.json()["payload"]
    assert payload["page_type"] == "generic"
    assert payload["page_title"] == "Documentation"
    assert "captured current ui context" in payload["summary"]["headline"].lower()
    assert payload["payload"]["dom"]["headings"][0] == "Documentation"
    assert payload["payload"]["dom"]["semantic_blocks"][0]["title"] == "Order Types"

    app.dependency_overrides.clear()
