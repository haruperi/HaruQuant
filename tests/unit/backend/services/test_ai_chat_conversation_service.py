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


def test_conversation_service_rename_search_and_export(tmp_path) -> None:
    database_path = tmp_path / "agentic_phase6.db"
    apply_pending_migrations(database_path, default_migrations_dir())
    service = ConversationService(AiChatRepository(database_path))

    thread = service.create_thread(user_id=11, current_route="/strategy/lab", current_page_type="strategy_detail")
    service.add_message(
        user_id=11,
        thread_id=thread.thread_id,
        role="user",
        content="Review the momentum strategy parameters",
    )
    renamed = service.rename_thread(user_id=11, thread_id=thread.thread_id, title="Momentum review")

    search_results = service.list_threads(user_id=11, query="momentum")
    exported = service.export_thread(user_id=11, thread_id=thread.thread_id, format="markdown")
    last_prompt = service.get_last_user_prompt(user_id=11, thread_id=thread.thread_id)

    assert renamed.title == "Momentum review"
    assert len(search_results) == 1
    assert search_results[0].thread_id == thread.thread_id
    assert exported["format"] == "markdown"
    assert "Momentum review" in str(exported["content"])
    assert last_prompt.content == "Review the momentum strategy parameters"
