from __future__ import annotations

from backend.data.database import AiChatRepository, apply_pending_migrations, default_migrations_dir
from backend.data.database.sqlite.database_operations import DatabaseManager
from backend.services.ai_chat import (
    ClarificationPolicy,
    ConversationOrchestrator,
    ConversationService,
    ConversationStateService,
    PageContextAssembler,
)


def test_conversation_orchestrator_requests_clarification_for_unresolved_reference(tmp_path) -> None:
    database_path = tmp_path / "agentic_conversation_orchestrator.db"
    db = DatabaseManager(db_path=str(database_path))
    db.initialize_database()
    apply_pending_migrations(database_path, default_migrations_dir())

    service = ConversationService(AiChatRepository(database_path))
    thread = service.create_thread(
        user_id=1,
        current_route="/unknown",
        current_page_type="generic",
    )
    assembler = PageContextAssembler(db_manager=db)
    page_context = assembler.assemble_context(route="/unknown", user_id=1)
    tool_context = {
        "route": "/unknown",
        "page_type": "generic",
        "session_id": None,
        "strategy_id": None,
        "backtest_id": None,
        "optimization_id": None,
        "symbol": None,
        "query": "Compare this run to the previous one",
    }
    conversation_state = ConversationStateService().build_state(
        thread=thread,
        page_context=page_context,
        latest_prompt="Compare this run to the previous one",
    )

    plan = ConversationOrchestrator().build_plan(
        prompt="Compare this run to the previous one",
        thread=thread,
        page_context=page_context,
        conversation_state=conversation_state,
        tool_context=tool_context,
    )

    assert plan.needs_clarification is True
    assert plan.answer_mode == "clarification"
    assert "compare" in (plan.clarification_question or "").lower()


def test_clarification_policy_does_not_block_page_summary_question(tmp_path) -> None:
    database_path = tmp_path / "agentic_conversation_policy.db"
    db = DatabaseManager(db_path=str(database_path))
    db.initialize_database()
    apply_pending_migrations(database_path, default_migrations_dir())

    service = ConversationService(AiChatRepository(database_path))
    thread = service.create_thread(
        user_id=1,
        current_route="/dashboard",
        current_page_type="dashboard",
    )
    assembler = PageContextAssembler(db_manager=db)
    page_context = assembler.assemble_context(route="/dashboard", user_id=1)
    route_decision = ConversationOrchestrator().agent_router.route("Summarize current page")
    conversation_state = ConversationStateService().build_state(
        thread=thread,
        page_context=page_context,
        latest_prompt="Summarize current page",
    )

    result = ClarificationPolicy().evaluate(
        prompt="Summarize current page",
        thread=thread,
        page_context=page_context,
        conversation_state=conversation_state,
        tool_context={
            "route": "/dashboard",
            "page_type": "dashboard",
            "session_id": None,
            "strategy_id": None,
            "backtest_id": None,
            "optimization_id": None,
            "symbol": None,
            "query": "Summarize current page",
        },
        route_decision=route_decision,
    )

    assert result.needs_clarification is False


def test_conversation_orchestrator_uses_conversation_state_to_resolve_previous_run(tmp_path) -> None:
    database_path = tmp_path / "agentic_conversation_orchestrator_state.db"
    db = DatabaseManager(db_path=str(database_path))
    db.initialize_database()
    apply_pending_migrations(database_path, default_migrations_dir())

    service = ConversationService(AiChatRepository(database_path))
    thread = service.create_thread(user_id=1)
    service.add_message(
        user_id=1,
        thread_id=thread.thread_id,
        role="user",
        content="Backtest 41 is the baseline. Backtest 42 is the new run.",
    )
    refreshed = service.get_thread(user_id=1, thread_id=thread.thread_id)
    assembler = PageContextAssembler(db_manager=db)
    page_context = assembler.assemble_context(route="/unknown", user_id=1)
    conversation_state = ConversationStateService().build_state(
        thread=refreshed,
        page_context=page_context,
        latest_prompt="Compare this run to the previous one",
    )
    tool_context = ConversationStateService().enrich_tool_context(
        context={
            "route": "/unknown",
            "page_type": "generic",
            "session_id": None,
            "strategy_id": None,
            "backtest_id": None,
            "optimization_id": None,
            "symbol": None,
            "query": "Compare this run to the previous one",
        },
        prompt="Compare this run to the previous one",
        state=conversation_state,
    )

    plan = ConversationOrchestrator().build_plan(
        prompt="Compare this run to the previous one",
        thread=refreshed,
        page_context=page_context,
        conversation_state=conversation_state,
        tool_context=tool_context,
    )

    assert plan.needs_clarification is False
    assert tool_context["backtest_id"] == "42"
    assert tool_context["comparison_backtest_id"] == "41"
