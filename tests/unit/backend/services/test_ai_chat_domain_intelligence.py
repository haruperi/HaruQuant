from __future__ import annotations

from backend.data.database import AiChatRepository, apply_pending_migrations, default_migrations_dir
from backend.data.database.sqlite.database_operations import DatabaseManager
from backend.services.ai_chat import (
    AIGatewayService,
    ChatAgentRouter,
    ChatPromptBuilder,
    ChatStreamRequest,
    ConversationService,
    PageContextAssembler,
)


def test_agent_router_returns_domain_specific_styles() -> None:
    router = ChatAgentRouter()

    diagnostic = router.route("Why is this strategy underperforming with higher drawdown?")
    comparison = router.route("Compare optimization run A versus run B")
    risk = router.route("Explain the current portfolio risk and exposure")

    assert diagnostic.task_class == "diagnostic"
    assert diagnostic.response_style == "diagnostic"
    assert comparison.task_class == "comparison"
    assert comparison.response_style == "compare"
    assert risk.task_class == "risk_explanation"
    assert risk.response_style == "warning"


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

    built = ChatPromptBuilder().build(
        thread=thread,
        page_context=page_context,
        user_prompt="Diagnose the current equity curve weakness",
        response_mode="tool_assisted",
        task_class="diagnostic",
    )

    assert "Task class: diagnostic" in built.system_prompt
    assert "Required sections: Observed State; Likely Drivers; Next Checks" in built.system_prompt
    assert "Expected response sections: Observed State; Likely Drivers; Next Checks" in built.user_prompt
    assert built.debug["response_style"] == "diagnostic"


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
    assert "Observed State:" in content
    assert "Likely Drivers:" in content
    assert "Next Checks:" in content
