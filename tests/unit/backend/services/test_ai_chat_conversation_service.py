from __future__ import annotations

from backend.data.database import AiChatRepository, apply_pending_migrations, default_migrations_dir
from backend.services.ai_chat import ConversationService


def test_conversation_service_promotes_title_and_creates_summary(tmp_path) -> None:
    database_path = tmp_path / "agentic.db"
    apply_pending_migrations(database_path, default_migrations_dir())
    service = ConversationService(AiChatRepository(database_path))

    thread = service.create_thread(user_id=7)
    assert thread.title == "New conversation"

    for index in range(6):
        role = "user" if index % 2 == 0 else "assistant"
        service.add_message(
            user_id=7,
            thread_id=thread.thread_id,
            role=role,
            content=f"Message {index} about strategy diagnostics",
        )

    updated = service.get_thread(user_id=7, thread_id=thread.thread_id)
    assert updated.title == "Message 0 about strategy diagnostics"
    assert len(updated.messages) == 6
    assert updated.memory_summary is not None
    assert updated.memory_summary.source_message_count == 6
