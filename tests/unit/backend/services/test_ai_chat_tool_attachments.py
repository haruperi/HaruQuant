from __future__ import annotations

from unittest.mock import patch

from backend.agents.strategy_creator_agent import StrategyCreatorAgent, StrategyCreatorResult
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

    full_permissions = next(definition for definition in definitions if definition.tool_id == "full_permissions")
    assert full_permissions.display_name == "Full Permissions"
    assert full_permissions.side_effect_policy == "approval_gate"
    assert full_permissions.required_user_ack is True


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
                prompt=(
                    "Create an RSI mean reversion strategy for EURUSD H1. "
                    "Enter long when RSI is below 30, exit when RSI recovers above 50, "
                    "use a 50 pip stop loss and 100 pip take profit, and risk 1% position size per trade."
                ),
                attached_tools=["strategy_creator"],
            )
        )
    content = "".join(chunks)

    assert content.strip()
    assert "CONFIRMATION" in content
    assert metadata["attached_tools"][0]["tool_id"] == "strategy_creator"
    assert metadata["attached_tools"][0]["missing_context"] == []
    assert metadata["strategy_creator"]["needs_confirmation"] is True


def test_gateway_grants_strategy_creator_only_with_full_permissions(tmp_path) -> None:
    database_path = tmp_path / "tool_attachment_full_permissions.db"
    db = DatabaseManager(db_path=str(database_path))
    db.initialize_database()
    apply_pending_migrations(database_path, default_migrations_dir())
    db.create_user(email="toolfullpermissions@example.com", username="tool_full_permissions_user", password="password")

    class CapturingStrategyCreator:
        def __init__(self) -> None:
            self.calls: list[bool] = []
            self.delegate = StrategyCreatorAgent(db_manager=db)

        def create_from_idea(self, **kwargs) -> StrategyCreatorResult:
            self.calls.append(bool(kwargs["full_permissions"]))
            return self.delegate.create_from_idea(
                user_id=kwargs["user_id"],
                idea=kwargs["idea"],
                context=kwargs["context"],
                full_permissions=False,
            )

    creator = CapturingStrategyCreator()
    conversation_service = ConversationService(AiChatRepository(database_path))
    first_thread = conversation_service.create_thread(user_id=1, current_route="/dashboard")
    second_thread = conversation_service.create_thread(user_id=1, current_route="/dashboard")
    gateway = AIGatewayService(
        conversation_service=conversation_service,
        context_assembler=PageContextAssembler(db_manager=db),
        strategy_creator_agent=creator,
    )

    with patch("backend.services.ai_chat.ai_gateway.create_llm_runtime", side_effect=LLMRuntimeError("disabled")):
        gateway.stream_response(
            ChatStreamRequest(
                user_id=1,
                thread_id=first_thread.thread_id,
                prompt=(
                    "Create an RSI mean reversion strategy for EURUSD H1. "
                    "Enter long when RSI is below 30, exit when RSI recovers above 50, "
                    "use a 50 pip stop loss and 100 pip take profit, and risk 1% position size per trade."
                ),
                attached_tools=["strategy_creator"],
            )
        )
        gateway.stream_response(
            ChatStreamRequest(
                user_id=1,
                thread_id=second_thread.thread_id,
                prompt=(
                    "Create an RSI mean reversion strategy for EURUSD H1. "
                    "Enter long when RSI is below 30, exit when RSI recovers above 50, "
                    "use a 50 pip stop loss and 100 pip take profit, and risk 1% position size per trade."
                ),
                attached_tools=["strategy_creator", "full_permissions"],
            )
        )

    assert creator.calls == [False, True]


def test_gateway_strategy_creator_clarifies_incomplete_strategy_request(tmp_path) -> None:
    database_path = tmp_path / "tool_attachment_strategy_clarification.db"
    db = DatabaseManager(db_path=str(database_path))
    db.initialize_database()
    apply_pending_migrations(database_path, default_migrations_dir())
    db.create_user(email="toolclarify@example.com", username="tool_clarify_user", password="password")

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
                prompt="Create a mean reversion strategy.",
                attached_tools=["strategy_creator", "full_permissions"],
            )
        )
    content = "".join(chunks)

    assert "I cannot generate the strategy yet" in content
    assert metadata["clarification_required"] is True
    assert metadata["response_style"] == "clarification"
    assert metadata["strategy_creator"]["needs_clarification"] is True
    assert metadata["strategy_creator"]["blueprint"] is None
    assert metadata["strategy_creator"]["materialized"] is False


def test_gateway_strategy_creator_generates_after_confirmation(tmp_path) -> None:
    database_path = tmp_path / "tool_attachment_strategy_confirmation.db"
    db = DatabaseManager(db_path=str(database_path))
    db.initialize_database()
    apply_pending_migrations(database_path, default_migrations_dir())
    db.create_user(email="toolconfirm@example.com", username="tool_confirm_user", password="password")

    conversation_service = ConversationService(AiChatRepository(database_path))
    thread = conversation_service.create_thread(user_id=1, current_route="/dashboard")
    gateway = AIGatewayService(
        conversation_service=conversation_service,
        context_assembler=PageContextAssembler(db_manager=db),
    )

    first_prompt = (
        "Create an RSI mean reversion strategy for EURUSD H1. "
        "Enter long when RSI is below 30, exit when RSI recovers above 50, "
        "use a 50 pip stop loss and 100 pip take profit, and risk 1% position size per trade."
    )

    with patch("backend.services.ai_chat.ai_gateway.create_llm_runtime", side_effect=LLMRuntimeError("disabled")):
        first_metadata, first_chunks, _message_id = gateway.stream_response(
            ChatStreamRequest(
                user_id=1,
                thread_id=thread.thread_id,
                prompt=first_prompt,
                attached_tools=["strategy_creator", "full_permissions"],
            )
        )
        first_content = "".join(first_chunks)
        second_metadata, second_chunks, _message_id = gateway.stream_response(
            ChatStreamRequest(
                user_id=1,
                thread_id=thread.thread_id,
                prompt="Confirm and generate it.",
                attached_tools=["strategy_creator", "full_permissions"],
            )
        )
    second_content = "".join(second_chunks)

    assert "CONFIRMATION" in first_content
    assert first_metadata["strategy_creator"]["needs_confirmation"] is True
    assert "Strategy Creator produced" in second_content
    assert second_metadata["strategy_creator"]["needs_confirmation"] is False
    assert second_metadata["strategy_creator"]["materialized"] is True
    assert second_metadata["strategy_id"] == 1
