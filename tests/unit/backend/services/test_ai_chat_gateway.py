from __future__ import annotations

from unittest.mock import patch

import pytest

from backend.data.database import AiChatRepository, apply_pending_migrations, default_migrations_dir
from backend.data.database.sqlite.database_operations import DatabaseManager
from backend.services.ai_chat import (
    AIGatewayService,
    ChatStreamRequest,
    ConversationService,
    PageContextAssembler,
)
from backend.services.tool_executor import ToolExecutionResult


@pytest.fixture(autouse=True)
def _use_legacy_chat_gateway(monkeypatch):
    monkeypatch.setenv("HARUQUANT_AGENTIC_FIRM_CHAT", "false")


class _KnowledgeToolExecutor:
    def execute(self, *, user_id, requested_tools, context, authority_band="read_only", permission_tier="T1_READ_ONLY"):
        return (
            [
                ToolExecutionResult(
                    tool_name="internal_knowledge",
                    payload={
                        "query": context.get("query"),
                        "matches": [
                            {
                                "content": "The rollout plan defines phased release rings, rollback checks, and operator sign-off before promotion.",
                                "relevance_score": 0.94,
                                "citation": "AI_Chatbot_Implementation_Plan.md",
                                "chunk": "chunk_01",
                                "filename": "AI_Chatbot_Implementation_Plan.md",
                            },
                            {
                                "content": "The support SOP requires incident triage, escalation, and verification of grounded tool behavior before closing the case.",
                                "relevance_score": 0.88,
                                "citation": "AI_Chatbot_Support_SOP.md",
                                "chunk": "chunk_02",
                                "filename": "AI_Chatbot_Support_SOP.md",
                            },
                        ],
                        "message": "Found 2 relevant excerpts from internal knowledge.",
                    },
                    latency_ms=12,
                    success=True,
                )
            ],
            tuple(),
        )


class _LatestCandleToolExecutor:
    def execute(self, *, user_id, requested_tools, context, authority_band="read_only", permission_tier="T1_READ_ONLY"):
        results = []
        if "latest_candle" in requested_tools:
            results.append(
                ToolExecutionResult(
                    tool_name="latest_candle",
                    payload={
                        "candle_available": True,
                        "session_id": context.get("session_id"),
                        "symbol": context.get("symbol"),
                        "timeframe": context.get("timeframe"),
                        "last_candle_direction": "bullish",
                        "last_candle": {
                            "time": "2026-04-21T15:15:00+00:00",
                            "open": 3312.1,
                            "high": 3318.4,
                            "low": 3310.7,
                            "close": 3316.8,
                        },
                    },
                    latency_ms=8,
                    success=True,
                )
            )
        return results, tuple()


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


def test_ai_gateway_returns_clarification_for_broad_docs_request(tmp_path) -> None:
    database_path = tmp_path / "agentic_docs_clarification_gateway.db"
    db = DatabaseManager(db_path=str(database_path))
    db.initialize_database()
    apply_pending_migrations(database_path, default_migrations_dir())
    db.create_user(email="broad_docs@example.com", username="broad_docs_user", password="password")

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
            prompt="docs",
        )
    )
    content = "".join(chunks)

    assert metadata["answer_mode"] == "clarification"
    assert metadata["clarification_required"] is True
    assert "which document area" in content.lower()


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


def test_ai_gateway_uses_conversational_retrieval_fallback_for_docs_queries(tmp_path) -> None:
    database_path = tmp_path / "agentic_docs_dialogue_gateway.db"
    db = DatabaseManager(db_path=str(database_path))
    db.initialize_database()
    apply_pending_migrations(database_path, default_migrations_dir())
    db.create_user(email="knowledge@example.com", username="knowledge_user", password="password")

    conversation_service = ConversationService(AiChatRepository(database_path))
    thread = conversation_service.create_thread(
        user_id=1,
        current_route="/dashboard",
        current_page_type="dashboard",
    )
    gateway = AIGatewayService(
        conversation_service=conversation_service,
        context_assembler=PageContextAssembler(db_manager=db),
        tool_executor=_KnowledgeToolExecutor(),
    )

    with patch("backend.services.ai_chat.ai_gateway.create_llm_runtime", side_effect=Exception("offline runtime")):
        metadata, chunks, _message_id = gateway.stream_response(
            ChatStreamRequest(
                user_id=1,
                thread_id=thread.thread_id,
                prompt="Explain the chatbot rollout runbook and support SOP.",
            )
        )

    content = "".join(chunks)

    assert metadata["task_class"] == "knowledge_dialogue"
    assert metadata["generation_source"] == "fallback"
    assert metadata["tools_used"] == ["internal_knowledge"]
    assert metadata["specialist_agents_used"] == ["knowledge_retrieval_agent"]
    assert "AI_Chatbot_Implementation_Plan.md" in content
    assert "AI_Chatbot_Support_SOP.md" in content
    assert "rollout plan defines phased release rings" in content.lower()


def test_ai_gateway_selects_latest_candle_for_live_chart_question(tmp_path) -> None:
    database_path = tmp_path / "agentic_live_candle_tools.db"
    db = DatabaseManager(db_path=str(database_path))
    db.initialize_database()
    apply_pending_migrations(database_path, default_migrations_dir())
    db.create_user(email="live_tools@example.com", username="live_tools_user", password="password")

    conversation_service = ConversationService(AiChatRepository(database_path))
    thread = conversation_service.create_thread(
        user_id=1,
        current_route="/live",
        current_page_type="live_trading",
    )
    gateway = AIGatewayService(
        conversation_service=conversation_service,
        context_assembler=PageContextAssembler(db_manager=db),
    )

    selected = gateway._select_tools(
        prompt="Is the last candle bullish or bearish?",
        page_type="live_trading",
        context={"route": "/live", "page_type": "live_trading", "session_id": 3, "symbol": "XAUUSD", "timeframe": "M15"},
    )

    assert "latest_candle" in selected
    assert "portfolio_summary" not in selected
    assert "risk_snapshot" not in selected


def test_ai_gateway_returns_chart_clarification_when_live_chart_anchor_missing(tmp_path) -> None:
    database_path = tmp_path / "agentic_live_candle_clarify.db"
    db = DatabaseManager(db_path=str(database_path))
    db.initialize_database()
    apply_pending_migrations(database_path, default_migrations_dir())
    db.create_user(email="live_clarify@example.com", username="live_clarify_user", password="password")

    conversation_service = ConversationService(AiChatRepository(database_path))
    thread = conversation_service.create_thread(
        user_id=1,
        current_route="/live",
        current_page_type="live_trading",
    )
    gateway = AIGatewayService(
        conversation_service=conversation_service,
        context_assembler=PageContextAssembler(db_manager=db),
    )

    metadata, chunks, _message_id = gateway.stream_response(
        ChatStreamRequest(
            user_id=1,
            thread_id=thread.thread_id,
            prompt="Is the last candle bullish or bearish?",
            context_route="/live",
        )
    )
    content = "".join(chunks)

    assert metadata["clarification_required"] is True
    assert "which live session and chart should i inspect" in content.lower()


def test_ai_gateway_uses_latest_candle_fallback_for_live_chart_question(tmp_path) -> None:
    database_path = tmp_path / "agentic_live_candle_fallback.db"
    db = DatabaseManager(db_path=str(database_path))
    db.initialize_database()
    apply_pending_migrations(database_path, default_migrations_dir())
    db.create_user(email="live_fallback@example.com", username="live_fallback_user", password="password")
    session_id = db.create_live_session(user_id=1, session_name="NY Session", mode="paper")

    conversation_service = ConversationService(AiChatRepository(database_path))
    thread = conversation_service.create_thread(
        user_id=1,
        current_route="/live",
        current_page_type="live_trading",
    )
    gateway = AIGatewayService(
        conversation_service=conversation_service,
        context_assembler=PageContextAssembler(db_manager=db),
        tool_executor=_LatestCandleToolExecutor(),
    )

    with patch("backend.services.ai_chat.ai_gateway.create_llm_runtime", side_effect=Exception("offline runtime")):
        metadata, chunks, _message_id = gateway.stream_response(
            ChatStreamRequest(
                user_id=1,
                thread_id=thread.thread_id,
                prompt="Is the last candle bullish or bearish?",
                context_route="/live",
                context_session_id=session_id,
                context_symbol="XAUUSD",
                context_timeframe="M15",
            )
        )

    content = "".join(chunks)

    assert metadata["generation_source"] == "fallback"
    assert metadata["tools_used"] == ["latest_candle"]
    assert "latest completed xauusd m15 candle is bullish" in content.lower()


def test_ai_gateway_uses_dom_snapshot_for_generic_page_summary(tmp_path) -> None:
    database_path = tmp_path / "agentic_dom_snapshot_gateway.db"
    db = DatabaseManager(db_path=str(database_path))
    db.initialize_database()
    apply_pending_migrations(database_path, default_migrations_dir())
    db.create_user(email="domsnapshot@example.com", username="domsnapshot_user", password="password")

    conversation_service = ConversationService(AiChatRepository(database_path))
    thread = conversation_service.create_thread(
        user_id=1,
        current_route="/performance/overview",
        current_page_type="generic",
    )
    gateway = AIGatewayService(
        conversation_service=conversation_service,
        context_assembler=PageContextAssembler(db_manager=db),
    )

    with patch("backend.services.ai_chat.ai_gateway.create_llm_runtime", side_effect=Exception("offline runtime")):
        metadata, chunks, _message_id = gateway.stream_response(
            ChatStreamRequest(
                user_id=1,
                thread_id=thread.thread_id,
                prompt="Summarise these results on current page",
                context_route="/performance/overview",
                context_page_title="Overview",
                context_dom={
                    "title": "Overview",
                    "headings": ["Performance Report", "Overview"],
                    "text_excerpt": "Net Profit Total Return CAGR Max Drawdown Profit Factor",
                    "tables": [
                        {
                            "headers": ["Metric", "All Trades", "Long", "Short"],
                            "rows": [
                                ["Net Profit", "$340.75", "$623.48", "($282.73)"],
                                ["Total Return", "3.41%", "6.23%", "(2.83%)"],
                                ["CAGR", "3.38%", "6.19%", "(2.96%)"],
                            ],
                        }
                    ],
                    "semantic_blocks": [
                        {
                            "id": "metric-grid:overview",
                            "blockType": "metric_table",
                            "title": "Overview metrics",
                            "summary": "Performance metrics for all, long, and short trades.",
                            "headers": ["Metric", "All Trades", "Long", "Short"],
                            "rows": [
                                ["Net Profit", "$340.75", "$623.48", "($282.73)"],
                                ["Total Return", "3.41%", "6.23%", "(2.83%)"],
                                ["CAGR", "3.38%", "6.19%", "(2.96%)"],
                            ],
                        }
                    ],
                },
            )
        )

    content = "".join(chunks)

    assert metadata["generation_source"] == "fallback"
    assert metadata["tools_used"] == []
    assert "net profit" in content.lower()


def test_ai_gateway_answers_date_of_extreme_from_page_chunks(tmp_path) -> None:
    database_path = tmp_path / "agentic_page_chunk_date_gateway.db"
    db = DatabaseManager(db_path=str(database_path))
    db.initialize_database()
    apply_pending_migrations(database_path, default_migrations_dir())
    db.create_user(email="pagechunkdate@example.com", username="pagechunkdate_user", password="password")

    conversation_service = ConversationService(AiChatRepository(database_path))
    thread = conversation_service.create_thread(
        user_id=1,
        current_route="/performance/chart-analysis/drawdown",
        current_page_type="generic",
    )
    gateway = AIGatewayService(
        conversation_service=conversation_service,
        context_assembler=PageContextAssembler(db_manager=db),
    )

    with patch("backend.services.ai_chat.ai_gateway.create_llm_runtime", side_effect=Exception("offline runtime")):
        metadata, chunks, _message_id = gateway.stream_response(
            ChatStreamRequest(
                user_id=1,
                thread_id=thread.thread_id,
                prompt="What date was the max drawdown?",
                context_route="/performance/chart-analysis/drawdown",
                context_page_title="Drawdown",
                context_dom={
                    "title": "Drawdown",
                    "headings": ["Performance Report", "Drawdown"],
                    "semantic_blocks": [
                        {
                            "id": "chart:drawdown",
                            "blockType": "chart",
                            "title": "Drawdown curve",
                            "summary": "Drawdown over time.",
                            "series": [
                                {
                                    "label": "Drawdown",
                                    "points": [
                                        {"x": "2026-02-01", "y": "-0.42"},
                                        {"x": "2026-02-03", "y": "-2.77"},
                                        {"x": "2026-02-04", "y": "-1.10"},
                                    ],
                                }
                            ],
                        }
                    ],
                },
            )
        )

    content = "".join(chunks)

    assert metadata["generation_source"] == "fallback"
    assert "2026-02-03" in content
    assert "-2.77" in content


def test_ai_gateway_answers_current_vs_previous_from_page_chunks(tmp_path) -> None:
    database_path = tmp_path / "agentic_page_chunk_compare_gateway.db"
    db = DatabaseManager(db_path=str(database_path))
    db.initialize_database()
    apply_pending_migrations(database_path, default_migrations_dir())
    db.create_user(email="pagechunkcompare@example.com", username="pagechunkcompare_user", password="password")

    conversation_service = ConversationService(AiChatRepository(database_path))
    thread = conversation_service.create_thread(
        user_id=1,
        current_route="/analysis/equity",
        current_page_type="generic",
    )
    gateway = AIGatewayService(
        conversation_service=conversation_service,
        context_assembler=PageContextAssembler(db_manager=db),
    )

    with patch("backend.services.ai_chat.ai_gateway.create_llm_runtime", side_effect=Exception("offline runtime")):
        metadata, chunks, _message_id = gateway.stream_response(
            ChatStreamRequest(
                user_id=1,
                thread_id=thread.thread_id,
                prompt="Compare current equity to the previous point",
                context_route="/analysis/equity",
                context_page_title="Equity Curve",
                context_dom={
                    "title": "Equity Curve",
                    "headings": ["Dashboard", "Equity Curve"],
                    "semantic_blocks": [
                        {
                            "id": "chart:equity",
                            "blockType": "chart",
                            "title": "Equity curve",
                            "summary": "Equity over time.",
                            "series": [
                                {
                                    "label": "Equity",
                                    "points": [
                                        {"x": "2026-02-01", "y": "10100"},
                                        {"x": "2026-02-02", "y": "10250"},
                                        {"x": "2026-02-03", "y": "10340"},
                                    ],
                                }
                            ],
                        }
                    ],
                },
            )
        )

    content = "".join(chunks)

    assert metadata["generation_source"] == "fallback"
    assert "2026-02-02=10250.0" in content
    assert "2026-02-03=10340.0" in content
    assert "change=90.0" in content


def test_ai_gateway_prioritizes_page_evidence_over_dashboard_tools(tmp_path) -> None:
    database_path = tmp_path / "agentic_page_priority_dashboard.db"
    db = DatabaseManager(db_path=str(database_path))
    db.initialize_database()
    apply_pending_migrations(database_path, default_migrations_dir())
    db.create_user(email="pagepriority@example.com", username="pagepriority_user", password="password")

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

    with patch("backend.services.ai_chat.ai_gateway.create_llm_runtime", side_effect=Exception("offline runtime")):
        metadata, chunks, _message_id = gateway.stream_response(
            ChatStreamRequest(
                user_id=1,
                thread_id=thread.thread_id,
                prompt="Compare current equity to the previous point on this page",
                context_route="/dashboard",
                context_page_title="Equity Curve",
                context_dom={
                    "title": "Equity Curve",
                    "headings": ["Dashboard", "Equity Curve"],
                    "semantic_blocks": [
                        {
                            "id": "chart:equity",
                            "blockType": "chart",
                            "title": "Equity curve",
                            "summary": "Equity over time.",
                            "series": [
                                {
                                    "label": "Equity",
                                    "points": [
                                        {"x": "2026-02-01", "y": "10100"},
                                        {"x": "2026-02-02", "y": "10250"},
                                        {"x": "2026-02-03", "y": "10340"},
                                    ],
                                }
                            ],
                        }
                    ],
                },
            )
        )

    content = "".join(chunks)

    assert metadata["generation_source"] == "fallback"
    assert metadata["page_evidence_prioritized"] is True
    assert metadata["tools_used"] == []
    assert "2026-02-03=10340.0" in content
    assert "change=90.0" in content
