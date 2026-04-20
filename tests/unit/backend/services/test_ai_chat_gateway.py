from __future__ import annotations

from backend.data.database import AiChatRepository, apply_pending_migrations, default_migrations_dir
from backend.data.database.sqlite.database_operations import DatabaseManager
from backend.services.ai_chat import (
    AIGatewayService,
    ChatStreamRequest,
    ConversationService,
    PageContextAssembler,
)


def test_ai_gateway_stream_response_persists_user_and_assistant_messages(tmp_path) -> None:
    database_path = tmp_path / "agentic.db"
    db = DatabaseManager(db_path=str(database_path))
    db.initialize_database()
    apply_pending_migrations(database_path, default_migrations_dir())
    db.create_user(email="gateway@example.com", username="gateway_user", password="password")

    conversation_service = ConversationService(AiChatRepository(database_path))
    thread = conversation_service.create_thread(
        user_id=1,
        current_route="/dashboard",
        current_page_type="dashboard",
    )
    gateway = AIGatewayService(
        conversation_service=conversation_service,
        context_assembler=PageContextAssembler(db_manager=db),
    )

    metadata, chunks, message_id = gateway.stream_response(
        ChatStreamRequest(
            user_id=1,
            thread_id=thread.thread_id,
            prompt="Why is my dashboard flat this week?",
        )
    )
    content = "".join(chunks)
    refreshed = conversation_service.get_thread(user_id=1, thread_id=thread.thread_id)

    assert metadata["response_mode"] == "tool_assisted"
    assert metadata["tools_used"] == ["portfolio_summary", "risk_snapshot"]
    assert message_id == refreshed.messages[-1].message_id
    assert refreshed.messages[-2].role == "user"
    assert refreshed.messages[-1].role == "assistant"
    assert refreshed.messages[-1].tool_calls == ["portfolio_summary", "risk_snapshot"]
    assert "dashboard" in content.lower()
