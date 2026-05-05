from __future__ import annotations

from data.database import AiChatRepository, apply_pending_migrations, default_migrations_dir
from data.database.sqlite.database_operations import DatabaseManager
from backend_retiring.agents.chat.ai_chat import (
    AIGatewayService,
    ChatAgentRouter,
    ChatPromptBuilder,
    ChatStreamRequest,
    ConversationStateService,
    ConversationService,
    PageContextAssembler,
)


def test_agent_router_returns_domain_specific_styles() -> None:
    router = ChatAgentRouter()

    diagnostic = router.route("Why is this strategy underperforming with higher drawdown?")
    comparison = router.route("Compare optimization run A versus run B")
    risk = router.route("Explain the current portfolio risk and exposure")
    knowledge = router.route("Explain the chatbot rollout runbook documentation")

    assert diagnostic.task_class == "diagnostic"
    assert diagnostic.response_style == "diagnostic"
    assert comparison.task_class == "comparison"
    assert comparison.response_style == "compare"
    assert risk.task_class == "risk_explanation"
    assert risk.response_style == "warning"
    assert knowledge.task_class == "knowledge_dialogue"
    assert knowledge.domain_focus == "knowledge_dialogue"


def test_prompt_builder_includes_domain_sections(tmp_path) -> None:
    database_path = tmp_path / "agentic_phase7_prompt.db"
    db = DatabaseManager(db_path=str(database_path))
    db.initialize_database()
    apply_pending_migrations(database_path, default_migrations_dir())
    service = ConversationService(AiChatRepository(database_path))
    thread = service.create_thread(user_id=1)
    page_context = PageContextAssembler(db_manager=db).assemble_context(
        route="/dashboard",
        user_id=1,
    )
    conversation_state = ConversationStateService().build_state(
        thread=thread,
        page_context=page_context,
        latest_prompt="Diagnose the current equity curve weakness",
    )

    built = ChatPromptBuilder().build(
        thread=thread,
        page_context=page_context,
        conversation_state=conversation_state,
        specialist_artifacts=[],
        user_prompt="Diagnose the current equity curve weakness",
        response_mode="tool_assisted",
        task_class="diagnostic",
    )

    assert "Task class: diagnostic" in built.system_prompt
    assert "Conversation topic: diagnostic" in built.system_prompt
    assert "Required sections:" not in built.system_prompt
    assert "Expected response sections:" not in built.user_prompt
    assert "Conversation resolved references:" in built.user_prompt
    assert built.debug["response_style"] == "diagnostic"


def test_prompt_builder_uses_conversational_shape_for_knowledge_dialogue(tmp_path) -> None:
    database_path = tmp_path / "agentic_phase7_prompt_knowledge.db"
    db = DatabaseManager(db_path=str(database_path))
    db.initialize_database()
    apply_pending_migrations(database_path, default_migrations_dir())
    service = ConversationService(AiChatRepository(database_path))
    thread = service.create_thread(user_id=1)
    page_context = PageContextAssembler(db_manager=db).assemble_context(
        route="/dashboard",
        user_id=1,
    )
    conversation_state = ConversationStateService().build_state(
        thread=thread,
        page_context=page_context,
        latest_prompt="Explain the chatbot rollout runbook",
    )

    built = ChatPromptBuilder().build(
        thread=thread,
        page_context=page_context,
        conversation_state=conversation_state,
        specialist_artifacts=[],
        user_prompt="Explain the chatbot rollout runbook",
        response_mode="tool_assisted",
        task_class="knowledge_dialogue",
    )

    assert "Task class: knowledge_dialogue" in built.system_prompt
    assert "Required sections:" not in built.system_prompt
    assert "Expected response sections:" not in built.user_prompt
    assert built.debug["task_class"] == "knowledge_dialogue"


def test_prompt_builder_includes_live_runtime_quality_instructions(tmp_path) -> None:
    database_path = tmp_path / "agentic_phase7_prompt_quality.db"
    db = DatabaseManager(db_path=str(database_path))
    db.initialize_database()
    apply_pending_migrations(database_path, default_migrations_dir())
    service = ConversationService(AiChatRepository(database_path))
    thread = service.create_thread(user_id=1)
    page_context = PageContextAssembler(db_manager=db).assemble_context(
        route="/dashboard",
        user_id=1,
    )
    conversation_state = ConversationStateService().build_state(
        thread=thread,
        page_context=page_context,
        latest_prompt="Summarize the dashboard",
    )

    built = ChatPromptBuilder().build(
        thread=thread,
        page_context=page_context,
        conversation_state=conversation_state,
        specialist_artifacts=[],
        user_prompt="Summarize the dashboard",
        response_mode="answer",
        task_class="performance_summary",
    )

    assert "Default to a natural conversational answer." in built.system_prompt
    assert "Do not echo internal metadata" in built.system_prompt
    assert "If you need a clarification, ask one short direct question and stop there." in built.system_prompt


def test_ai_gateway_phase7_returns_structured_domain_metadata(tmp_path) -> None:
    database_path = tmp_path / "agentic_phase7_gateway.db"
    db = DatabaseManager(db_path=str(database_path))
    db.initialize_database()
    apply_pending_migrations(database_path, default_migrations_dir())
    db.create_user(email="phase7@example.com", username="phase7_user", password="password")

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
            prompt="Why is my dashboard flat and underperforming this week?",
        )
    )
    content = "".join(chunks)

    assert metadata["task_class"] == "diagnostic"
    assert metadata["response_style"] == "diagnostic"
    assert metadata["domain_focus"] == "drawdown_diagnosis"
    assert metadata["specialist_agents_used"] == ["portfolio_risk_agent"]
    assert "drawdown" in content.lower()
    assert "diagnostic signal" in content.lower()
