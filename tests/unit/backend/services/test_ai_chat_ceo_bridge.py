from __future__ import annotations

import pytest

from backend.data.database import AiChatRepository, apply_pending_migrations, default_migrations_dir
from backend.data.database.sqlite.database_operations import DatabaseManager
from backend.services.ai_chat import (
    AIGatewayService,
    CEOChatOrchestrator,
    ChatStreamRequest,
    ConversationService,
    PageContextAssembler,
)
from backend.services.ai_chat.ceo_chat_orchestrator import CHAT_ATTACHMENT_TO_FIRM_HINT
from backend.services.ai_chat.conversation_state_service import ConversationStateService


@pytest.fixture(autouse=True)
def _disable_live_llm_calls(monkeypatch):
    monkeypatch.setenv("HARUQUANT_CEO_CLASSIFIER_LLM_ENABLED", "false")
    monkeypatch.setenv("HARUQUANT_CEO_LLM_ENABLED", "false")


def _setup_chat(tmp_path, name: str = "ceo_bridge"):
    database_path = tmp_path / f"{name}.db"
    db = DatabaseManager(db_path=str(database_path))
    db.initialize_database()
    apply_pending_migrations(database_path, default_migrations_dir())
    db.create_user(email=f"{name}@example.com", username=f"{name}_user", password="password")
    conversation_service = ConversationService(AiChatRepository(database_path))
    thread = conversation_service.create_thread(
        user_id=1,
        current_route="/dashboard",
        current_page_type="dashboard",
    )
    page_context = PageContextAssembler(db_manager=db).assemble_context(
        route="/dashboard",
        user_id=1,
        page_state={"symbol": "EURUSD", "timeframe": "H1"},
    )
    conversation_state = ConversationStateService().build_state(
        thread=thread,
        page_context=page_context,
        latest_prompt="Create a EURUSD strategy",
    )
    return db, conversation_service, thread, page_context, conversation_state


def test_ceo_chat_orchestrator_persists_chat_messages_and_firm_metadata(tmp_path) -> None:
    _db, conversation_service, thread, page_context, conversation_state = _setup_chat(tmp_path)
    orchestrator = CEOChatOrchestrator(conversation_service=conversation_service)

    result = orchestrator.handle_chat_turn(
        user_id=1,
        thread=thread,
        prompt="Create and backtest a EURUSD H1 mean reversion strategy.",
        request_id="req-ceo-bridge",
        page_context=page_context,
        conversation_state=conversation_state,
        tool_context={"symbol": "EURUSD", "timeframe": "H1"},
        attached_tool_ids=("strategy_creator",),
    )
    refreshed = conversation_service.get_thread(user_id=1, thread_id=thread.thread_id)

    assert not result.text.startswith("CEO memo:")
    assert result.metadata["agentic_firm_chat"] is True
    assert result.metadata["planner"]["source"] == "phase7_planner_agent"
    assert result.metadata["firm_workflow"]["workflow_id"] == "firm-req-ceo-bridge"
    assert result.metadata["firm_workflow"]["audit_id"]
    assert result.metadata["tools_used"] == [
        "get_symbol_data",
        "get_latest_ohlcv",
        "create_strategy_spec",
        "run_backtest",
    ]
    assert "strategy_creator" in result.metadata["specialist_agents_used"]
    assert result.metadata["legacy_chat_tools_as_hints"] == ["strategy_creator"]
    assert result.metadata["operator_hints"][0]["preferred_department"] == "strategy_creator"
    assert result.metadata["attached_tools"][0]["authority"] == "operator_hint_only"
    assert refreshed.messages[-2].role == "user"
    assert refreshed.messages[-1].role == "assistant"
    assert refreshed.messages[-1].metadata["agentic_firm_chat"] is True


def test_ai_gateway_can_route_chat_through_ceo_bridge(tmp_path) -> None:
    db, conversation_service, thread, _page_context, _conversation_state = _setup_chat(tmp_path, "gateway_ceo")
    gateway = AIGatewayService(
        conversation_service=conversation_service,
        context_assembler=PageContextAssembler(db_manager=db),
    )

    metadata, chunks, message_id = gateway.stream_response(
        ChatStreamRequest(
            user_id=1,
            thread_id=thread.thread_id,
            prompt="Research EURUSD market structure.",
            attached_tools=["haruquant_docs"],
            context_symbol="EURUSD",
            context_timeframe="H1",
        )
    )
    content = "".join(chunks)
    refreshed = conversation_service.get_thread(user_id=1, thread_id=thread.thread_id)

    assert metadata["response_mode"] == "agentic_firm"
    assert metadata["planner"]["intent"] == "research"
    assert metadata["generation_source"] == "agentic_firm_ceo"
    assert metadata["operator_hints"][0] == {
        "tool_id": "haruquant_docs",
        **CHAT_ATTACHMENT_TO_FIRM_HINT["haruquant_docs"],
    }
    assert metadata["legacy_tool_mapping"]["risk_snapshot"] == "get_risk_snapshot"
    assert metadata["chat_specialist_mapping"]["final_responder_agent"] == "ceo"
    assert message_id == refreshed.messages[-1].message_id
    assert not content.startswith("CEO memo:")
    assert "get_symbol_data" in metadata["tools_used"]
    assert "market_intelligence" in metadata["specialist_agents_used"]


def test_ai_gateway_default_ceo_chat_answers_identity_prompt(tmp_path) -> None:
    db, conversation_service, thread, _page_context, _conversation_state = _setup_chat(tmp_path, "gateway_ceo_identity")
    gateway = AIGatewayService(
        conversation_service=conversation_service,
        context_assembler=PageContextAssembler(db_manager=db),
    )

    metadata, chunks, _message_id = gateway.stream_response(
        ChatStreamRequest(
            user_id=1,
            thread_id=thread.thread_id,
            prompt="Who are you in the HaruQuant agentic firm?",
        )
    )
    content = "".join(chunks)

    assert metadata["agentic_firm_chat"] is True
    assert metadata["planner"]["intent"] == "ceo_identity"
    assert metadata["response_style"] == "identity_memo"
    assert metadata["ceo_memo"]["memo_type"] == "ceo_identity"
    assert "CEO/CIO-style orchestrator" in content
    assert "not an execution engine" in content
    assert "delegate work to specialist departments" in content
    assert "Human Board" in content
    assert not content.startswith("CEO memo:")


def test_ai_gateway_default_ceo_chat_answers_short_identity_prompt(tmp_path) -> None:
    db, conversation_service, thread, _page_context, _conversation_state = _setup_chat(tmp_path, "gateway_ceo_short_identity")
    gateway = AIGatewayService(
        conversation_service=conversation_service,
        context_assembler=PageContextAssembler(db_manager=db),
    )

    metadata, chunks, _message_id = gateway.stream_response(
        ChatStreamRequest(
            user_id=1,
            thread_id=thread.thread_id,
            prompt="who are you?",
        )
    )
    content = "".join(chunks)

    assert metadata["planner"]["intent"] == "ceo_identity"
    assert metadata["clarification_required"] is False
    assert "CEO/CIO-style orchestrator" in content
    assert "What market, timeframe" not in content


def test_ai_gateway_default_ceo_chat_answers_name_prompt(tmp_path) -> None:
    db, conversation_service, thread, _page_context, _conversation_state = _setup_chat(tmp_path, "gateway_ceo_name")
    gateway = AIGatewayService(
        conversation_service=conversation_service,
        context_assembler=PageContextAssembler(db_manager=db),
    )

    metadata, chunks, _message_id = gateway.stream_response(
        ChatStreamRequest(
            user_id=1,
            thread_id=thread.thread_id,
            prompt="what is your name?",
        )
    )
    content = "".join(chunks)

    assert metadata["planner"]["intent"] == "ceo_identity"
    assert metadata["ceo_memo"]["name"] == "HaruQuant AI"
    assert "My name is HaruQuant AI" in content
    assert "What market, timeframe" not in content


def test_ai_gateway_default_ceo_chat_blocks_live_trade_request(tmp_path) -> None:
    db, conversation_service, thread, _page_context, _conversation_state = _setup_chat(tmp_path, "gateway_ceo_live_block")
    gateway = AIGatewayService(
        conversation_service=conversation_service,
        context_assembler=PageContextAssembler(db_manager=db),
    )

    metadata, chunks, _message_id = gateway.stream_response(
        ChatStreamRequest(
            user_id=1,
            thread_id=thread.thread_id,
            prompt="Place a live trade on XAUUSD using your best judgment.",
        )
    )
    content = "".join(chunks)

    assert metadata["planner"]["intent"] == "execution_proposal"
    assert metadata["ceo_memo"]["memo_type"] == "blocked_by_risk"
    assert "cannot place a live trade" in content
    assert "RiskGovernor" in content
    assert "Human Board approval" in content
    assert "Required before trading" not in content
