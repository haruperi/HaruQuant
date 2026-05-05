from __future__ import annotations

from fastapi.testclient import TestClient

from backend_retiring.api.auth_utils import get_user_id_from_token
from backend_retiring.api.main import app
from backend_retiring.api.routes.ai_chat import get_ai_gateway, get_conversation_service, get_page_context_assembler
from data.database import AiChatRepository, apply_pending_migrations, default_migrations_dir
from data.database.sqlite.database_operations import DatabaseManager
from backend_retiring.agents.chat.ai_chat import AIGatewayService, ConversationService, PageContextAssembler


def test_ai_chat_stream_endpoint_returns_sse_events(tmp_path) -> None:
    database_path = tmp_path / "agentic.db"
    db = DatabaseManager(db_path=str(database_path))
    db.initialize_database()
    apply_pending_migrations(database_path, default_migrations_dir())
    db.create_user(email="stream@example.com", username="stream_user", password="password")

    conversation_service = ConversationService(AiChatRepository(database_path))
    thread = conversation_service.create_thread(
        user_id=1,
        current_route="/dashboard",
        current_page_type="dashboard",
    )
    context_assembler = PageContextAssembler(db_manager=db)
    gateway = AIGatewayService(
        conversation_service=conversation_service,
        context_assembler=context_assembler,
    )

    app.dependency_overrides[get_conversation_service] = lambda: conversation_service
    app.dependency_overrides[get_page_context_assembler] = lambda: context_assembler
    app.dependency_overrides[get_ai_gateway] = lambda: gateway
    app.dependency_overrides[get_user_id_from_token] = lambda: 1
    client = TestClient(app)

    with client.stream(
        "POST",
        f"/api/ai-chat/threads/{thread.thread_id}/responses/stream",
        json={"prompt": "Summarize the current dashboard state"},
    ) as response:
        payload = "".join(chunk for chunk in response.iter_text())

    assert response.status_code == 200
    assert "event: meta" in payload
    assert "event: token" in payload
    assert "event: done" in payload
    assert "portfolio_summary" in payload
    assert "risk_snapshot" in payload

    app.dependency_overrides.clear()


def test_ai_chat_stream_endpoint_returns_signal_proposal_metadata(tmp_path) -> None:
    database_path = tmp_path / "agentic_signal_stream.db"
    db = DatabaseManager(db_path=str(database_path))
    db.initialize_database()
    apply_pending_migrations(database_path, default_migrations_dir())
    db.create_user(email="signalstream@example.com", username="signal_stream_user", password="password")

    conversation_service = ConversationService(AiChatRepository(database_path))
    thread = conversation_service.create_thread(
        user_id=1,
        current_route="/dashboard",
        current_page_type="dashboard",
    )
    context_assembler = PageContextAssembler(db_manager=db)
    gateway = AIGatewayService(
        conversation_service=conversation_service,
        context_assembler=context_assembler,
    )

    app.dependency_overrides[get_conversation_service] = lambda: conversation_service
    app.dependency_overrides[get_page_context_assembler] = lambda: context_assembler
    app.dependency_overrides[get_ai_gateway] = lambda: gateway
    app.dependency_overrides[get_user_id_from_token] = lambda: 1
    client = TestClient(app)

    with client.stream(
        "POST",
        f"/api/ai-chat/threads/{thread.thread_id}/responses/stream",
        json={"prompt": "Generate a EURUSD buy signal setup for me."},
    ) as response:
        payload = "".join(chunk for chunk in response.iter_text())

    assert response.status_code == 200
    assert "event: meta" in payload
    assert "signal_proposal_id" in payload
    assert "non_executed_signal_proposal" in payload

    app.dependency_overrides.clear()


def test_ai_chat_stream_endpoint_returns_action_draft_metadata(tmp_path) -> None:
    database_path = tmp_path / "agentic_action_stream.db"
    db = DatabaseManager(db_path=str(database_path))
    db.initialize_database()
    apply_pending_migrations(database_path, default_migrations_dir())
    db.create_user(email="actionstream@example.com", username="action_stream_user", password="password")

    conversation_service = ConversationService(AiChatRepository(database_path))
    thread = conversation_service.create_thread(
        user_id=1,
        current_route="/strategy/lab",
        current_page_type="strategy_detail",
    )
    context_assembler = PageContextAssembler(db_manager=db)
    gateway = AIGatewayService(
        conversation_service=conversation_service,
        context_assembler=context_assembler,
    )

    app.dependency_overrides[get_conversation_service] = lambda: conversation_service
    app.dependency_overrides[get_page_context_assembler] = lambda: context_assembler
    app.dependency_overrides[get_ai_gateway] = lambda: gateway
    app.dependency_overrides[get_user_id_from_token] = lambda: 1
    client = TestClient(app)

    with client.stream(
        "POST",
        f"/api/ai-chat/threads/{thread.thread_id}/responses/stream",
        json={"prompt": "Launch a backtest for this strategy."},
    ) as response:
        payload = "".join(chunk for chunk in response.iter_text())

    assert response.status_code == 200
    assert "event: meta" in payload
    assert "action_draft_id" in payload
    assert "event: done" in payload

    app.dependency_overrides.clear()
