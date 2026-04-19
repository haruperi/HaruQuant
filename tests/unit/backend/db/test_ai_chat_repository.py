from __future__ import annotations

from backend.data.database import AiChatRepository, apply_pending_migrations, default_migrations_dir


def test_ai_chat_repository_crud_round_trip(tmp_path) -> None:
    database_path = tmp_path / "agentic.db"
    apply_pending_migrations(database_path, default_migrations_dir())
    repository = AiChatRepository(database_path)

    thread = repository.create_thread(
        thread_id="thread_001",
        user_id="42",
        title="Investigate drawdown",
        current_route="/dashboard",
        current_page_type="dashboard",
    )
    assert thread.title == "Investigate drawdown"

    message = repository.add_message(
        message_id="msg_001",
        thread_id=thread.thread_id,
        user_id="42",
        role="user",
        content="Why did the portfolio lose money?",
    )
    assert message.role == "user"

    summary = repository.create_memory_summary(
        summary_id="summary_001",
        thread_id=thread.thread_id,
        user_id="42",
        summary_text="User is reviewing a dashboard drawdown.",
        source_message_count=1,
    )
    assert summary.source_message_count == 1

    fact = repository.upsert_pinned_fact(
        thread_id=thread.thread_id,
        user_id="42",
        fact_key="preferred_symbol",
        fact_value="SPY",
        source="user_prompt",
    )
    assert fact.fact_key == "preferred_symbol"

    listed_threads = repository.list_threads(user_id="42")
    listed_messages = repository.list_messages(thread_id=thread.thread_id, user_id="42")
    listed_facts = repository.list_pinned_facts(thread_id=thread.thread_id, user_id="42")
    latest_summary = repository.get_latest_memory_summary(thread_id=thread.thread_id, user_id="42")

    assert listed_threads[0].thread_id == thread.thread_id
    assert listed_messages[0].message_id == message.message_id
    assert listed_facts[0].fact_value == "SPY"
    assert latest_summary is not None
    assert latest_summary.summary_text.startswith("User is reviewing")
