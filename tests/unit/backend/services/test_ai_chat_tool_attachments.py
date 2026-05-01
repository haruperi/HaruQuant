from __future__ import annotations

from unittest.mock import patch

from backend.agents.runtime import LLMRuntimeError
from backend.data.database import AiChatRepository, apply_pending_migrations, default_migrations_dir
from backend.data.database.sqlite.database_operations import DatabaseManager
from backend.services.ai_chat import AIGatewayService, ChatStreamRequest, ConversationService, PageContextAssembler
from backend.services.ai_chat.tool_attachment_registry import ChatToolAttachmentRegistry
from backend.services.ai_chat.tool_attachment_runtime import ChatToolAttachmentRuntime


def test_chat_tool_registry_exposes_strategy_creator() -> None:
    registry = ChatToolAttachmentRegistry()

    definitions = registry.list_definitions()

    strategy_creator = next(definition for definition in definitions if definition.tool_id == "strategy_creator")
    assert strategy_creator.display_name == "Strategy Creator"
    assert strategy_creator.side_effect_policy == "artifact_only"
    assert "symbol_stats" in strategy_creator.allowed_backend_tools


def test_chat_tool_runtime_marks_missing_context(tmp_path) -> None:
    database_path = tmp_path / "tool_attachment_runtime.db"
    db = DatabaseManager(db_path=str(database_path))
    db.initialize_database()
    apply_pending_migrations(database_path, default_migrations_dir())
    db.create_user(email="toolruntime@example.com", username="tool_runtime_user", password="password")
    page_context = PageContextAssembler(db_manager=db).assemble_context(route="/dashboard", user_id=1)

    runtime = ChatToolAttachmentRuntime()
    attachments = runtime.resolve_attachments(
        selected_tool_ids=["strategy_creator"],
        page_context=page_context,
        tool_context={"route": "/dashboard", "page_type": "dashboard"},
    )

    assert attachments[0].tool_id == "strategy_creator"
    assert attachments[0].missing_context == ["symbol", "timeframe"]


def test_gateway_returns_attached_tool_metadata(tmp_path) -> None:
    database_path = tmp_path / "tool_attachment_gateway.db"
    db = DatabaseManager(db_path=str(database_path))
    db.initialize_database()
    apply_pending_migrations(database_path, default_migrations_dir())
    db.create_user(email="toolgateway@example.com", username="tool_gateway_user", password="password")

    conversation_service = ConversationService(AiChatRepository(database_path))
    thread = conversation_service.create_thread(user_id=1, current_route="/dashboard")
    gateway = AIGatewayService(
        conversation_service=conversation_service,
        context_assembler=PageContextAssembler(db_manager=db),
    )

    with patch("backend.services.ai_chat.ai_gateway.create_llm_runtime", side_effect=LLMRuntimeError("disabled")):
        metadata, chunks, _message_id = gateway.stream_response(
            ChatStreamRequest(
                user_id=1,
                thread_id=thread.thread_id,
                prompt="Create a simple EURUSD H1 mean reversion strategy.",
                attached_tools=["strategy_creator"],
            )
        )
    content = "".join(chunks)

    assert content.strip()
    assert metadata["attached_tools"][0]["tool_id"] == "strategy_creator"
    assert metadata["attached_tools"][0]["missing_context"] == []
