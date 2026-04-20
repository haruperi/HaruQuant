from __future__ import annotations

from fastapi.testclient import TestClient

from backend.api.auth_utils import get_user_id_from_token
from backend.api.main import app
from backend.api.routes.ai_chat import get_ai_gateway, get_conversation_service, get_page_context_assembler
from backend.data.database import AiChatRepository, apply_pending_migrations, default_migrations_dir
from backend.data.database.sqlite.database_operations import DatabaseManager
from backend.services.ai_chat import AIGatewayService, ConversationService, PageContextAssembler


def test_ai_chat_phase2_thread_and_message_flow(tmp_path) -> None:
    database_path = tmp_path / "agentic.db"
    apply_pending_migrations(database_path, default_migrations_dir())
    service = ConversationService(AiChatRepository(database_path))

    app.dependency_overrides[get_conversation_service] = lambda: service
    app.dependency_overrides[get_user_id_from_token] = lambda: 9
    client = TestClient(app)

    created = client.post(
        "/api/ai-chat/threads",
        json={
            "current_route": "/dashboard",
            "current_page_type": "dashboard",
        },
    )
    assert created.status_code == 201
    thread = created.json()
    assert thread["user_id"] == "9"

    message = client.post(
        f"/api/ai-chat/threads/{thread['thread_id']}/messages",
        json={
            "role": "user",
            "content": "Explain why the dashboard equity curve flattened",
        },
    )
    assert message.status_code == 201
    assert message.json()["role"] == "user"

    fetched = client.get(f"/api/ai-chat/threads/{thread['thread_id']}")
    assert fetched.status_code == 200
    payload = fetched.json()
    assert payload["messages"][0]["content"].startswith("Explain why")
    assert payload["title"] == "Explain why the dashboard equity curve flattened"

    listed = client.get("/api/ai-chat/threads")
    assert listed.status_code == 200
    assert listed.json()[0]["thread_id"] == thread["thread_id"]

    app.dependency_overrides.clear()


def test_ai_chat_phase6_thread_management_routes(tmp_path) -> None:
    database_path = tmp_path / "agentic_phase6.db"
    db = DatabaseManager(db_path=str(database_path))
    db.initialize_database()
    apply_pending_migrations(database_path, default_migrations_dir())
    service = ConversationService(AiChatRepository(database_path))
    context_assembler = PageContextAssembler(db_manager=db)
    gateway = AIGatewayService(
        conversation_service=service,
        context_assembler=context_assembler,
    )

    app.dependency_overrides[get_conversation_service] = lambda: service
    app.dependency_overrides[get_page_context_assembler] = lambda: context_assembler
    app.dependency_overrides[get_ai_gateway] = lambda: gateway
    app.dependency_overrides[get_user_id_from_token] = lambda: 12
    client = TestClient(app)

    created = client.post(
        "/api/ai-chat/threads",
        json={
            "title": "Initial title",
            "current_route": "/dashboard",
            "current_page_type": "dashboard",
        },
    )
    assert created.status_code == 201
    thread = created.json()

    message = client.post(
        f"/api/ai-chat/threads/{thread['thread_id']}/messages",
        json={
            "role": "user",
            "content": "Explain current portfolio risk",
        },
    )
    assert message.status_code == 201

    renamed = client.patch(
        f"/api/ai-chat/threads/{thread['thread_id']}",
        json={"title": "Portfolio risk review"},
    )
    assert renamed.status_code == 200
    assert renamed.json()["title"] == "Portfolio risk review"

    searched = client.get("/api/ai-chat/threads?q=portfolio")
    assert searched.status_code == 200
    assert searched.json()[0]["thread_id"] == thread["thread_id"]

    exported = client.get(f"/api/ai-chat/threads/{thread['thread_id']}/export?format=markdown")
    assert exported.status_code == 200
    assert "Portfolio risk review" in exported.text

    regenerated = client.post(
        f"/api/ai-chat/threads/{thread['thread_id']}/responses/regenerate",
        json={"prompt": "ignored"},
    )
    assert regenerated.status_code == 200
    payload = regenerated.text
    assert "event: meta" in payload
    assert "regenerated_from_message_id" in payload

    deleted = client.delete(f"/api/ai-chat/threads/{thread['thread_id']}")
    assert deleted.status_code == 200
    assert deleted.json()["deleted"] is True

    app.dependency_overrides.clear()
