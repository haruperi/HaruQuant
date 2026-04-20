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


def test_conversation_service_signal_proposal_lifecycle(tmp_path) -> None:
    database_path = tmp_path / "agentic_signal.db"
    apply_pending_migrations(database_path, default_migrations_dir())
    service = ConversationService(AiChatRepository(database_path))

    thread = service.create_thread(user_id=21, current_route="/dashboard", current_page_type="dashboard")
    proposal = service.create_signal_proposal(
        user_id=21,
        thread_id=thread.thread_id,
        request_id="req_signal_01",
        title="EURUSD signal proposal",
        hypothesis="Buy EURUSD on pullback",
        symbol="EURUSD",
        timeframe="1H",
        direction="long",
        entry_logic="Enter on pullback confirmation.",
        exit_logic="Exit on invalidation.",
        confidence=68,
        rationale="Trend continuation setup.",
        risk_note="Non-executed proposal only.",
    )

    watchlisted = service.save_signal_proposal_to_watchlist(user_id=21, proposal_id=proposal.proposal_id)
    reviewed = service.queue_signal_proposal_for_review(user_id=21, proposal_id=proposal.proposal_id)
    proposals = service.list_signal_proposals(user_id=21, thread_id=thread.thread_id)

    assert proposal.status == "draft"
    assert watchlisted.watchlist_saved is True
    assert reviewed.review_queue_saved is True
    assert reviewed.status == "review_queue"
    assert proposals[0].proposal_id == proposal.proposal_id


def test_conversation_service_action_draft_lifecycle(tmp_path) -> None:
    database_path = tmp_path / "agentic_action_draft.db"
    apply_pending_migrations(database_path, default_migrations_dir())
    service = ConversationService(AiChatRepository(database_path))

    thread = service.create_thread(user_id=31, current_route="/strategy/lab", current_page_type="strategy_detail")
    draft = service.create_action_draft(
        user_id=31,
        thread_id=thread.thread_id,
        request_id="req_action_01",
        draft_type="backtest_launch",
        title="Backtest launch draft",
        description="Prepared a supervised backtest request.",
        payload={"strategy_id": "strategy_01", "route": "/strategy/lab"},
        risk_precheck_status="passed",
        risk_precheck_notes="Draft remains non-executed pending approval.",
    )
    requested = service.request_action_draft_approval(user_id=31, draft_id=draft.draft_id)
    drafts = service.list_action_drafts(user_id=31, thread_id=thread.thread_id)

    assert draft.status == "draft"
    assert requested.approval_id is not None
    assert requested.status == "approval_requested"
    assert requested.side_effect_status == "not_executed"
    assert drafts[0].draft_id == draft.draft_id
