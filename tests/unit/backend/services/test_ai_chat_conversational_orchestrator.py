from __future__ import annotations

from backend.data.database import AiChatRepository, apply_pending_migrations, default_migrations_dir
from backend.data.database.sqlite.database_operations import DatabaseManager
from backend.agents.chat.ai_chat import (
    ClarificationPolicy,
    ConversationOrchestrator,
    ConversationService,
    ConversationStateService,
    PageContextAssembler,
)
from backend.agents.chat.ai_chat.conversation_planner import ConversationPlanner, StructuredChatPlan


class PlannerMockRuntime:
    def __init__(self, response_content: str) -> None:
        self.response_content = response_content

    def run(self, *, request, context):
        import json

        class Result:
            pass

        result = Result()
        result.output_payload = json.loads(self.response_content)
        return result


def _base_tool_context(query: str, **overrides) -> dict[str, object]:
    context: dict[str, object] = {
        "route": "/dashboard",
        "page_type": "dashboard",
        "session_id": None,
        "strategy_id": None,
        "backtest_id": None,
        "optimization_id": None,
        "symbol": None,
        "timeframe": None,
        "query": query,
        "attached_tool_ids": (),
    }
    context.update(overrides)
    return context


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
    assert "unresolved_reference" in plan.missing_inputs


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


def test_planner_routes_confirmation_of_pending_page_action(tmp_path) -> None:
    database_path = tmp_path / "ai_chat_page_action_confirmation.db"
    db = DatabaseManager(db_path=str(database_path))
    db.initialize_database()
    apply_pending_migrations(database_path, default_migrations_dir())
    db.create_user(email="pageconfirm@example.com", username="page_confirm_user", password="password")

    service = ConversationService(AiChatRepository(database_path))
    thread = service.create_thread(user_id=1, current_route="/simulation")
    service.add_message(
        user_id=1,
        thread_id=thread.thread_id,
        role="assistant",
        content="Do you want me to navigate to `/performance`? page_action_confirmation: navigate_app_page {'path': '/performance'}",
    )
    thread = service.get_thread(user_id=1, thread_id=thread.thread_id)
    page_context = PageContextAssembler(db_manager=db).assemble_context(route="/simulation", user_id=1)
    conversation_state = ConversationStateService().build_state(
        thread=thread,
        page_context=page_context,
        latest_prompt="yes",
    )

    plan = ConversationPlanner().plan(
        prompt="yes",
        thread=thread,
        page_context=page_context,
        conversation_state=conversation_state,
        tool_context=_base_tool_context("yes"),
    )

    assert plan.task_class == "page_operation"
    assert "page_operator" in plan.attached_tools
    assert plan.page_actions_to_plan == ("registered_page_action_plan",)


def test_planner_explains_missing_strategy_creator_tool(tmp_path) -> None:
    database_path = tmp_path / "ai_chat_missing_strategy_creator_tool.db"
    db = DatabaseManager(db_path=str(database_path))
    db.initialize_database()
    apply_pending_migrations(database_path, default_migrations_dir())
    db.create_user(email="missingstrategytool@example.com", username="missing_strategy_tool_user", password="password")

    service = ConversationService(AiChatRepository(database_path))
    thread = service.create_thread(user_id=1, current_route="/strategies")
    page_context = PageContextAssembler(db_manager=db).assemble_context(route="/strategies", user_id=1)
    prompt = "Create a strategy that buys RSI dips"

    plan = ConversationPlanner().plan(
        prompt=prompt,
        thread=thread,
        page_context=page_context,
        conversation_state=ConversationStateService().build_state(thread=thread, page_context=page_context, latest_prompt=prompt),
        tool_context=_base_tool_context(prompt),
    )

    assert plan.needs_clarification is True
    assert plan.task_class == "tool_requirement"
    assert "Strategy Creator" in (plan.clarification_question or "")
    assert "Tools menu" in (plan.clarification_question or "")


def test_planner_explains_missing_page_operator_tool(tmp_path) -> None:
    database_path = tmp_path / "ai_chat_missing_page_operator_tool.db"
    db = DatabaseManager(db_path=str(database_path))
    db.initialize_database()
    apply_pending_migrations(database_path, default_migrations_dir())
    db.create_user(email="missingpageoperator@example.com", username="missing_page_operator_user", password="password")

    service = ConversationService(AiChatRepository(database_path))
    thread = service.create_thread(user_id=1, current_route="/simulation")
    page_context = PageContextAssembler(db_manager=db).assemble_context(route="/simulation", user_id=1)
    prompt = "go to the home page"

    plan = ConversationPlanner().plan(
        prompt=prompt,
        thread=thread,
        page_context=page_context,
        conversation_state=ConversationStateService().build_state(thread=thread, page_context=page_context, latest_prompt=prompt),
        tool_context=_base_tool_context(prompt),
    )

    assert plan.needs_clarification is True
    assert plan.task_class == "tool_requirement"
    assert "Page Operator" in (plan.clarification_question or "")
    assert "navigation" in (plan.clarification_question or "")


def test_planner_explains_missing_full_permissions_for_strategy_write(tmp_path) -> None:
    database_path = tmp_path / "ai_chat_missing_full_permissions_tool.db"
    db = DatabaseManager(db_path=str(database_path))
    db.initialize_database()
    apply_pending_migrations(database_path, default_migrations_dir())
    db.create_user(email="missingfullpermission@example.com", username="missing_full_permission_user", password="password")

    service = ConversationService(AiChatRepository(database_path))
    thread = service.create_thread(user_id=1, current_route="/strategies")
    page_context = PageContextAssembler(db_manager=db).assemble_context(route="/strategies", user_id=1)
    prompt = "Create and save the actual strategy implementation from A to Z"

    plan = ConversationPlanner().plan(
        prompt=prompt,
        thread=thread,
        page_context=page_context,
        conversation_state=ConversationStateService().build_state(thread=thread, page_context=page_context, latest_prompt=prompt),
        tool_context=_base_tool_context(prompt, attached_tool_ids=("strategy_creator",)),
    )

    assert plan.needs_clarification is True
    assert plan.task_class == "tool_requirement"
    assert "Full Permissions" in (plan.clarification_question or "")
    assert "save files or register strategies" in (plan.clarification_question or "")


def test_planner_does_not_block_strategy_creator_when_required_tools_selected(tmp_path) -> None:
    database_path = tmp_path / "ai_chat_selected_strategy_tools.db"
    db = DatabaseManager(db_path=str(database_path))
    db.initialize_database()
    apply_pending_migrations(database_path, default_migrations_dir())
    db.create_user(email="selectedstrategytools@example.com", username="selected_strategy_tools_user", password="password")

    service = ConversationService(AiChatRepository(database_path))
    thread = service.create_thread(user_id=1, current_route="/strategies")
    page_context = PageContextAssembler(db_manager=db).assemble_context(route="/strategies", user_id=1)
    prompt = "Create and save the actual strategy implementation from A to Z"

    plan = ConversationPlanner().plan(
        prompt=prompt,
        thread=thread,
        page_context=page_context,
        conversation_state=ConversationStateService().build_state(thread=thread, page_context=page_context, latest_prompt=prompt),
        tool_context=_base_tool_context(prompt, attached_tool_ids=("strategy_creator", "full_permissions")),
    )

    assert plan.task_class == "strategy_creation"
    assert plan.needs_clarification is False
    assert "strategy_creator" in plan.attached_tools


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


def test_clarification_policy_requests_scope_for_broad_docs_prompt(tmp_path) -> None:
    database_path = tmp_path / "agentic_conversation_policy_docs.db"
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
    route_decision = ConversationOrchestrator().agent_router.route("docs")
    conversation_state = ConversationStateService().build_state(
        thread=thread,
        page_context=page_context,
        latest_prompt="docs",
    )

    result = ClarificationPolicy().evaluate(
        prompt="docs",
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
            "query": "docs",
        },
        route_decision=route_decision,
    )

    assert result.needs_clarification is True
    assert "document area" in (result.question or "").lower()


def test_conversation_planner_requires_strategy_creator_tool_for_strategy_creation(tmp_path) -> None:
    database_path = tmp_path / "agentic_conversation_planner_strategy.db"
    db = DatabaseManager(db_path=str(database_path))
    db.initialize_database()
    apply_pending_migrations(database_path, default_migrations_dir())
    service = ConversationService(AiChatRepository(database_path))
    thread = service.create_thread(user_id=1, current_route="/strategies", current_page_type="generic")
    page_context = PageContextAssembler(db_manager=db).assemble_context(route="/strategies", user_id=1)
    prompt = "Create me a mean reversion strategy for EURUSD H1"

    plan = ConversationOrchestrator().build_plan(
        prompt=prompt,
        thread=thread,
        page_context=page_context,
        conversation_state=ConversationStateService().build_state(thread=thread, page_context=page_context, latest_prompt=prompt),
        tool_context=_base_tool_context(prompt, route="/strategies", symbol="EURUSD", timeframe="H1"),
    )

    assert plan.needs_clarification is True
    assert plan.task_class == "tool_requirement"
    assert "Strategy Creator" in (plan.clarification_question or "")
    assert "Tools menu" in (plan.clarification_question or "")


def test_conversation_planner_routes_backtest_page_to_backtest_analyst(tmp_path) -> None:
    database_path = tmp_path / "agentic_conversation_planner_backtest.db"
    db = DatabaseManager(db_path=str(database_path))
    db.initialize_database()
    apply_pending_migrations(database_path, default_migrations_dir())
    service = ConversationService(AiChatRepository(database_path))
    thread = service.create_thread(user_id=1, current_route="/backtests/42", current_page_type="backtest_detail")
    page_context = PageContextAssembler(db_manager=db).assemble_context(route="/backtests/42", user_id=1, page_state={"backtest_id": 42})
    prompt = "Why did this backtest fail?"

    plan = ConversationOrchestrator().build_plan(
        prompt=prompt,
        thread=thread,
        page_context=page_context,
        conversation_state=ConversationStateService().build_state(thread=thread, page_context=page_context, latest_prompt=prompt),
        tool_context=_base_tool_context(prompt, route="/backtests/42", page_type="backtest_detail", backtest_id=42),
    )

    assert plan.intent == "diagnose_backtest"
    assert plan.task_class == "diagnostic"
    assert "backtest_analyst" in plan.attached_tools
    assert "backtest_summary" in plan.tools_to_run


def test_conversation_planner_routes_page_actions_to_page_operator_when_tool_selected(tmp_path) -> None:
    database_path = tmp_path / "agentic_conversation_planner_page_action.db"
    db = DatabaseManager(db_path=str(database_path))
    db.initialize_database()
    apply_pending_migrations(database_path, default_migrations_dir())
    service = ConversationService(AiChatRepository(database_path))
    thread = service.create_thread(user_id=1, current_route="/backtests/42", current_page_type="backtest_detail")
    page_context = PageContextAssembler(db_manager=db).assemble_context(route="/backtests/42", user_id=1)
    prompt = "Click export and download this report"

    plan = ConversationOrchestrator().build_plan(
        prompt=prompt,
        thread=thread,
        page_context=page_context,
        conversation_state=ConversationStateService().build_state(thread=thread, page_context=page_context, latest_prompt=prompt),
        tool_context=_base_tool_context(prompt, route="/backtests/42", page_type="backtest_detail", attached_tool_ids=("page_operator",)),
    )

    assert plan.intent == "operate_page"
    assert plan.task_class == "page_operation"
    assert "page_operator" in plan.attached_tools
    assert plan.artifact_expected == "page_action_plan"
    assert plan.page_actions_to_plan == ["registered_page_action_plan"]


class FakeLLMPlanner:
    def __init__(self, proposal: dict[str, object]) -> None:
        self.proposal = proposal
        self.called = False

    def refine_plan(self, **kwargs) -> dict[str, object]:
        self.called = True
        return self.proposal


def test_hybrid_planner_uses_llm_assist_for_ambiguous_strategy_request(tmp_path) -> None:
    database_path = tmp_path / "agentic_hybrid_planner.db"
    db = DatabaseManager(db_path=str(database_path))
    db.initialize_database()
    apply_pending_migrations(database_path, default_migrations_dir())
    service = ConversationService(AiChatRepository(database_path))
    thread = service.create_thread(user_id=1, current_route="/strategies", current_page_type="generic")
    page_context = PageContextAssembler(db_manager=db).assemble_context(route="/strategies", user_id=1)
    prompt = "I want something mean-reverting but not too aggressive"
    fake = FakeLLMPlanner(
        {
            "intent": "create_strategy",
            "backend_tools_to_run": ["symbol_stats", "internal_knowledge"],
            "attached_tools": ["strategy_creator"],
            "specialist_agents_to_run": ["strategy_creator_agent"],
            "page_actions_to_plan": [],
            "artifact_expected": "strategy_artifact",
            "risk_level": "read_only",
            "confidence": 0.86,
            "rationale": "LLM inferred a strategy creation request from ambiguous language.",
        }
    )

    plan = ConversationOrchestrator(planner=ConversationPlanner(llm_planner=fake)).build_plan(
        prompt=prompt,
        thread=thread,
        page_context=page_context,
        conversation_state=ConversationStateService().build_state(thread=thread, page_context=page_context, latest_prompt=prompt),
        tool_context=_base_tool_context(prompt, route="/strategies"),
    )

    assert fake.called is True
    assert plan.planner_source == "llm_assist"
    assert plan.intent == "create_strategy"
    assert "strategy_creator" in plan.attached_tools


def test_hybrid_planner_rejects_invalid_llm_tool_proposal(tmp_path) -> None:
    database_path = tmp_path / "agentic_hybrid_planner_invalid.db"
    db = DatabaseManager(db_path=str(database_path))
    db.initialize_database()
    apply_pending_migrations(database_path, default_migrations_dir())
    service = ConversationService(AiChatRepository(database_path))
    thread = service.create_thread(user_id=1, current_route="/dashboard", current_page_type="dashboard")
    page_context = PageContextAssembler(db_manager=db).assemble_context(route="/dashboard", user_id=1)
    prompt = "make it better"
    fake = FakeLLMPlanner(
        {
            "intent": "draft_action",
            "backend_tools_to_run": ["place_live_trade"],
            "attached_tools": ["unknown_tool"],
            "risk_level": "live_execution",
            "confidence": 0.99,
        }
    )

    plan = ConversationOrchestrator(planner=ConversationPlanner(llm_planner=fake)).build_plan(
        prompt=prompt,
        thread=thread,
        page_context=page_context,
        conversation_state=ConversationStateService().build_state(thread=thread, page_context=page_context, latest_prompt=prompt),
        tool_context=_base_tool_context(prompt),
    )

    assert fake.called is True
    assert plan.planner_source == "deterministic"
    assert "place_live_trade" not in plan.tools_to_run
    assert plan.risk_level == "read_only"


def test_gateway_default_planner_uses_live_llm_assist_when_needed(tmp_path, monkeypatch) -> None:
    database_path = tmp_path / "agentic_gateway_live_assist.db"
    db = DatabaseManager(db_path=str(database_path))
    db.initialize_database()
    apply_pending_migrations(database_path, default_migrations_dir())
    db.create_user(email="plannerassist@example.com", username="planner_assist_user", password="password")

    proposal = """{
      "intent": "create_strategy",
      "backend_tools_to_run": ["symbol_stats", "internal_knowledge"],
      "attached_tools": ["strategy_creator"],
      "specialist_agents_to_run": ["strategy_creator_agent"],
      "page_actions_to_plan": [],
      "artifact_expected": "strategy_artifact",
      "risk_level": "read_only",
      "confidence": 0.88,
      "rationale": "LLM planner inferred strategy creation."
    }"""
    calls = {"count": 0}

    def fake_create_llm_runtime(**kwargs):
        calls["count"] += 1
        return PlannerMockRuntime(proposal)

    monkeypatch.setattr("backend.agents.chat.ai_chat.conversation_planner.create_llm_runtime", fake_create_llm_runtime)

    service = ConversationService(AiChatRepository(database_path))
    thread = service.create_thread(user_id=1, current_route="/strategies", current_page_type="generic")
    gateway = __import__("backend.agents.chat.ai_chat", fromlist=["AIGatewayService"]).AIGatewayService(
        conversation_service=service,
        context_assembler=PageContextAssembler(db_manager=db),
    )

    metadata, chunks, _message_id = gateway.stream_response(
        __import__("backend.agents.chat.ai_chat", fromlist=["ChatStreamRequest"]).ChatStreamRequest(
            user_id=1,
            thread_id=thread.thread_id,
            prompt="I want something mean-reverting but not too aggressive",
        )
    )
    content = "".join(chunks)

    assert calls["count"] == 1
    assert metadata["planner"]["source"] == "llm_assist"
    assert metadata["planner"]["intent"] == "create_strategy"
    assert "strategy_creator" in metadata["planner"]["attached_tools"]
    assert content.strip()
