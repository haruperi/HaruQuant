from __future__ import annotations

from fastapi.testclient import TestClient

from backend.api.auth_utils import get_user_id_from_token
from backend.api.main import app
from backend.api.routes.ai_chat import get_conversation_service
from backend.data.database import AiChatRepository, apply_pending_migrations, default_migrations_dir
from backend.services.ai_chat import ConversationService


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
