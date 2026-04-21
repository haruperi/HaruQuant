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
    assert metadata["task_class"] == "diagnostic"
    assert metadata["response_style"] == "diagnostic"
    assert metadata["tools_used"] == ["portfolio_summary", "risk_snapshot"]
    assert metadata["specialist_agents_used"] == ["portfolio_risk_agent"]
    assert message_id == refreshed.messages[-1].message_id
    assert refreshed.messages[-2].role == "user"
    assert refreshed.messages[-1].role == "assistant"
    assert refreshed.messages[-1].tool_calls == ["portfolio_summary", "risk_snapshot"]
    assert "dashboard" in content.lower()
    assert "drawdown" in content.lower()
    assert metadata["answer_mode"] == "direct_answer"
    assert metadata["clarification_required"] is False
    assert metadata["conversation_plan_id"].startswith("convplan_")


def test_ai_gateway_stream_response_creates_signal_proposal(tmp_path) -> None:
    database_path = tmp_path / "agentic_signal_gateway.db"
    db = DatabaseManager(db_path=str(database_path))
    db.initialize_database()
    apply_pending_migrations(database_path, default_migrations_dir())
    db.create_user(email="signal@example.com", username="signal_user", password="password")

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

    metadata, chunks, _message_id = gateway.stream_response(
        ChatStreamRequest(
            user_id=1,
            thread_id=thread.thread_id,
            prompt="Generate a EURUSD buy signal setup for me.",
        )
    )
    content = "".join(chunks)
    refreshed = conversation_service.get_thread(user_id=1, thread_id=thread.thread_id)
    proposals = conversation_service.list_signal_proposals(user_id=1, thread_id=thread.thread_id)

    assert metadata["response_mode"] == "signal_proposal"
    assert metadata["task_class"] == "signal_proposal"
    assert metadata["signal_proposal_id"] == proposals[0].proposal_id
    assert refreshed.messages[-1].signal_proposal_id == proposals[0].proposal_id
    assert proposals[0].non_executed_label == "non_executed_signal_proposal"
    assert content.strip() != ""


def test_ai_gateway_stream_response_creates_action_draft(tmp_path) -> None:
    database_path = tmp_path / "agentic_action_gateway.db"
    db = DatabaseManager(db_path=str(database_path))
    db.initialize_database()
    apply_pending_migrations(database_path, default_migrations_dir())
    db.create_user(email="action@example.com", username="action_user", password="password")

    conversation_service = ConversationService(AiChatRepository(database_path))
    thread = conversation_service.create_thread(
        user_id=1,
        current_route="/strategy/lab",
        current_page_type="strategy_detail",
    )
    gateway = AIGatewayService(
        conversation_service=conversation_service,
        context_assembler=PageContextAssembler(db_manager=db),
    )

    metadata, chunks, _message_id = gateway.stream_response(
        ChatStreamRequest(
            user_id=1,
            thread_id=thread.thread_id,
            prompt="Launch a backtest for this strategy.",
        )
    )
    content = "".join(chunks)
    refreshed = conversation_service.get_thread(user_id=1, thread_id=thread.thread_id)
    drafts = conversation_service.list_action_drafts(user_id=1, thread_id=thread.thread_id)

    assert metadata["response_mode"] == "action_draft"
    assert metadata["task_class"] == "action_draft"
    assert metadata["action_draft_id"] == drafts[0].draft_id
    assert refreshed.messages[-1].action_draft_id == drafts[0].draft_id
    assert drafts[0].draft_type == "backtest_launch"
    assert drafts[0].side_effect_status == "not_executed"
    assert content.strip() != ""


def test_ai_gateway_selects_internal_knowledge_for_docs_queries(tmp_path) -> None:
    database_path = tmp_path / "agentic_docs_gateway.db"
    db = DatabaseManager(db_path=str(database_path))
    db.initialize_database()
    apply_pending_migrations(database_path, default_migrations_dir())
    db.create_user(email="docs@example.com", username="docs_user", password="password")

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

    selected = gateway._select_tools(
        prompt="Explain the chatbot rollout plan and incident runbook documentation.",
        page_type="dashboard",
        context={"route": "/dashboard", "page_type": "dashboard", "query": "Explain the chatbot rollout plan and incident runbook documentation."},
    )

    assert "internal_knowledge" in selected


def test_ai_gateway_returns_clarification_question_for_unresolved_reference(tmp_path) -> None:
    database_path = tmp_path / "agentic_clarification_gateway.db"
    db = DatabaseManager(db_path=str(database_path))
    db.initialize_database()
    apply_pending_migrations(database_path, default_migrations_dir())
    db.create_user(email="clarify@example.com", username="clarify_user", password="password")

    conversation_service = ConversationService(AiChatRepository(database_path))
    thread = conversation_service.create_thread(
        user_id=1,
        current_route="/unknown",
        current_page_type="generic",
    )
    gateway = AIGatewayService(
        conversation_service=conversation_service,
        context_assembler=PageContextAssembler(db_manager=db),
    )

    metadata, chunks, _message_id = gateway.stream_response(
        ChatStreamRequest(
            user_id=1,
            thread_id=thread.thread_id,
            prompt="Compare this run to the previous one",
        )
    )
    content = "".join(chunks)

    assert metadata["answer_mode"] == "clarification"
    assert metadata["clarification_required"] is True
    assert metadata["generation_source"] == "clarification_policy"
    assert "which two runs or strategies" in content.lower()


def test_ai_gateway_resolves_previous_run_from_thread_state(tmp_path) -> None:
    database_path = tmp_path / "agentic_reference_gateway.db"
    db = DatabaseManager(db_path=str(database_path))
    db.initialize_database()
    apply_pending_migrations(database_path, default_migrations_dir())
    db.create_user(email="stateful@example.com", username="stateful_user", password="password")

    conversation_service = ConversationService(AiChatRepository(database_path))
    thread = conversation_service.create_thread(
        user_id=1,
        current_route="/unknown",
        current_page_type="generic",
    )
    conversation_service.add_message(
        user_id=1,
        thread_id=thread.thread_id,
        role="user",
        content="Backtest 41 underperformed after the EURUSD setup. Backtest 42 is the newer run.",
    )
    gateway = AIGatewayService(
        conversation_service=conversation_service,
        context_assembler=PageContextAssembler(db_manager=db),
    )

    metadata, chunks, _message_id = gateway.stream_response(
        ChatStreamRequest(
            user_id=1,
            thread_id=thread.thread_id,
            prompt="Compare this run to the previous one",
        )
    )
    content = "".join(chunks)

    assert metadata["answer_mode"] == "direct_answer"
    assert metadata["clarification_required"] is False
    assert "optimization_comparison_agent" in metadata["specialist_agents_used"]
    assert "backtest_summary" in metadata["tools_used"]
    assert "comparison" in content.lower()
