from __future__ import annotations

from fastapi.testclient import TestClient

from backend_retiring.api.auth_utils import get_user_id_from_token
from backend_retiring.api.main import app
from backend_retiring.api.routes.ai_chat import get_ai_gateway, get_conversation_service, get_page_context_assembler, get_trade_action_governor
from data.database import AiChatRepository, GovernanceRepository, apply_pending_migrations, default_migrations_dir
from data.database.sqlite.database_operations import DatabaseManager
from backend_retiring.agents.chat.ai_chat import AIGatewayService, ConversationService, PageContextAssembler
from haruquant.execution import ApprovalVoteRequest, ApprovalVoteService
from haruquant.execution import TradeActionGovernor


def test_ai_chat_phase2_thread_and_message_flow(tmp_path) -> None:
    database_path = tmp_path / "agentic.db"
    apply_pending_migrations(database_path, default_migrations_dir())
    service = ConversationService(AiChatRepository(database_path))

    app.dependency_overrides[get_conversation_service] = lambda: service
    app.dependency_overrides[get_user_id_from_token] = lambda: 9
    client = TestClient(app)

    created = client.post(
        "/api/ai-chat/threads",
        json={
            "current_route": "/dashboard",
            "current_page_type": "dashboard",
        },
    )
    assert created.status_code == 201
    thread = created.json()
    assert thread["user_id"] == "9"

    message = client.post(
        f"/api/ai-chat/threads/{thread['thread_id']}/messages",
        json={
            "role": "user",
            "content": "Explain why the dashboard equity curve flattened",
        },
    )
    assert message.status_code == 201
    assert message.json()["role"] == "user"

    fetched = client.get(f"/api/ai-chat/threads/{thread['thread_id']}")
    assert fetched.status_code == 200
    payload = fetched.json()
    assert payload["messages"][0]["content"].startswith("Explain why")
    assert payload["title"] == "Explain why the dashboard equity curve flattened"

    listed = client.get("/api/ai-chat/threads")
    assert listed.status_code == 200
    assert listed.json()[0]["thread_id"] == thread["thread_id"]

    app.dependency_overrides.clear()


def test_ai_chat_phase6_thread_management_routes(tmp_path) -> None:
    database_path = tmp_path / "agentic_phase6.db"
    db = DatabaseManager(db_path=str(database_path))
    db.initialize_database()
    apply_pending_migrations(database_path, default_migrations_dir())
    service = ConversationService(AiChatRepository(database_path))
    context_assembler = PageContextAssembler(db_manager=db)
    gateway = AIGatewayService(
        conversation_service=service,
        context_assembler=context_assembler,
    )

    app.dependency_overrides[get_conversation_service] = lambda: service
    app.dependency_overrides[get_page_context_assembler] = lambda: context_assembler
    app.dependency_overrides[get_ai_gateway] = lambda: gateway
    app.dependency_overrides[get_user_id_from_token] = lambda: 12
    client = TestClient(app)

    created = client.post(
        "/api/ai-chat/threads",
        json={
            "title": "Initial title",
            "current_route": "/dashboard",
            "current_page_type": "dashboard",
        },
    )
    assert created.status_code == 201
    thread = created.json()

    message = client.post(
        f"/api/ai-chat/threads/{thread['thread_id']}/messages",
        json={
            "role": "user",
            "content": "Explain current portfolio risk",
        },
    )
    assert message.status_code == 201

    renamed = client.patch(
        f"/api/ai-chat/threads/{thread['thread_id']}",
        json={"title": "Portfolio risk review"},
    )
    assert renamed.status_code == 200
    assert renamed.json()["title"] == "Portfolio risk review"

    searched = client.get("/api/ai-chat/threads?q=portfolio")
    assert searched.status_code == 200
    assert searched.json()[0]["thread_id"] == thread["thread_id"]

    exported = client.get(f"/api/ai-chat/threads/{thread['thread_id']}/export?format=markdown")
    assert exported.status_code == 200
    assert "Portfolio risk review" in exported.text

    regenerated = client.post(
        f"/api/ai-chat/threads/{thread['thread_id']}/responses/regenerate",
        json={"prompt": "ignored"},
    )
    assert regenerated.status_code == 200
    payload = regenerated.text
    assert "event: meta" in payload
    assert "regenerated_from_message_id" in payload

    deleted = client.delete(f"/api/ai-chat/threads/{thread['thread_id']}")
    assert deleted.status_code == 200
    assert deleted.json()["deleted"] is True

    app.dependency_overrides.clear()


def test_ai_chat_phase8_signal_proposal_routes(tmp_path) -> None:
    database_path = tmp_path / "agentic_phase8.db"
    db = DatabaseManager(db_path=str(database_path))
    db.initialize_database()
    apply_pending_migrations(database_path, default_migrations_dir())
    db.create_user(email="phase8@example.com", username="phase8_user", password="password")
    service = ConversationService(AiChatRepository(database_path))
    context_assembler = PageContextAssembler(db_manager=db)
    gateway = AIGatewayService(
        conversation_service=service,
        context_assembler=context_assembler,
    )

    app.dependency_overrides[get_conversation_service] = lambda: service
    app.dependency_overrides[get_page_context_assembler] = lambda: context_assembler
    app.dependency_overrides[get_ai_gateway] = lambda: gateway
    app.dependency_overrides[get_user_id_from_token] = lambda: 1
    client = TestClient(app)

    created = client.post(
        "/api/ai-chat/threads",
        json={"current_route": "/dashboard", "current_page_type": "dashboard"},
    )
    thread = created.json()

    streamed = client.post(
        f"/api/ai-chat/threads/{thread['thread_id']}/responses/stream",
        json={"prompt": "Generate a EURUSD buy signal setup for me."},
    )
    assert streamed.status_code == 200
    assert "signal_proposal" in streamed.text

    proposals = client.get(f"/api/ai-chat/threads/{thread['thread_id']}/signal-proposals")
    assert proposals.status_code == 200
    proposal = proposals.json()[0]
    assert proposal["status"] == "draft"
    assert proposal["non_executed_label"] == "non_executed_signal_proposal"

    watchlisted = client.post(
        f"/api/ai-chat/threads/{thread['thread_id']}/signal-proposals/{proposal['proposal_id']}/watchlist"
    )
    assert watchlisted.status_code == 200
    assert watchlisted.json()["watchlist_saved"] is True

    review_queued = client.post(
        f"/api/ai-chat/threads/{thread['thread_id']}/signal-proposals/{proposal['proposal_id']}/review-queue"
    )
    assert review_queued.status_code == 200
    assert review_queued.json()["review_queue_saved"] is True
    assert review_queued.json()["status"] == "review_queue"

    app.dependency_overrides.clear()


def test_ai_chat_phase9_action_draft_routes(tmp_path) -> None:
    database_path = tmp_path / "agentic_phase9.db"
    db = DatabaseManager(db_path=str(database_path))
    db.initialize_database()
    apply_pending_migrations(database_path, default_migrations_dir())
    db.create_user(email="phase9@example.com", username="phase9_user", password="password")
    service = ConversationService(AiChatRepository(database_path))
    context_assembler = PageContextAssembler(db_manager=db)
    gateway = AIGatewayService(
        conversation_service=service,
        context_assembler=context_assembler,
    )

    app.dependency_overrides[get_conversation_service] = lambda: service
    app.dependency_overrides[get_page_context_assembler] = lambda: context_assembler
    app.dependency_overrides[get_ai_gateway] = lambda: gateway
    app.dependency_overrides[get_user_id_from_token] = lambda: 1
    client = TestClient(app)

    created = client.post(
        "/api/ai-chat/threads",
        json={"current_route": "/strategy/lab", "current_page_type": "strategy_detail"},
    )
    thread = created.json()

    streamed = client.post(
        f"/api/ai-chat/threads/{thread['thread_id']}/responses/stream",
        json={"prompt": "Launch a backtest for this strategy."},
    )
    assert streamed.status_code == 200
    assert "action_draft" in streamed.text

    drafts = client.get(f"/api/ai-chat/threads/{thread['thread_id']}/action-drafts")
    assert drafts.status_code == 200
    draft = drafts.json()[0]
    assert draft["status"] == "draft"
    assert draft["side_effect_status"] == "not_executed"

    requested = client.post(
        f"/api/ai-chat/threads/{thread['thread_id']}/action-drafts/{draft['draft_id']}/request-approval",
        json={"actor_type": "user"},
    )
    assert requested.status_code == 200
    assert requested.json()["approval_id"] is not None
    assert requested.json()["status"] == "approval_requested"

    app.dependency_overrides.clear()


def test_ai_chat_phase10_paper_execution_route(tmp_path) -> None:
    database_path = tmp_path / "agentic_phase10.db"
    db = DatabaseManager(db_path=str(database_path))
    db.initialize_database()
    apply_pending_migrations(database_path, default_migrations_dir())
    db.create_user(email="phase10@example.com", username="phase10_user", password="password")
    service = ConversationService(AiChatRepository(database_path))
    context_assembler = PageContextAssembler(db_manager=db)
    gateway = AIGatewayService(
        conversation_service=service,
        context_assembler=context_assembler,
    )
    governor = TradeActionGovernor(str(database_path))

    app.dependency_overrides[get_conversation_service] = lambda: service
    app.dependency_overrides[get_page_context_assembler] = lambda: context_assembler
    app.dependency_overrides[get_ai_gateway] = lambda: gateway
    app.dependency_overrides[get_trade_action_governor] = lambda: governor
    app.dependency_overrides[get_user_id_from_token] = lambda: 1
    client = TestClient(app)

    created = client.post(
        "/api/ai-chat/threads",
        json={"current_route": "/live", "current_page_type": "live_trading"},
    )
    thread = created.json()

    streamed = client.post(
        f"/api/ai-chat/threads/{thread['thread_id']}/responses/stream",
        json={"prompt": "Create order to buy EURUSD now."},
    )
    assert streamed.status_code == 200

    drafts = client.get(f"/api/ai-chat/threads/{thread['thread_id']}/action-drafts")
    draft = drafts.json()[0]
    approval_requested = client.post(
        f"/api/ai-chat/threads/{thread['thread_id']}/action-drafts/{draft['draft_id']}/request-approval",
        json={"actor_type": "user"},
    )
    approval_id = approval_requested.json()["approval_id"]
    ApprovalVoteService(GovernanceRepository(database_path)).vote(
        ApprovalVoteRequest(
            approval_id=approval_id,
            approver_role="approver",
            approver_id="approver_001",
            decision="APPROVE",
            rationale="Approved for paper execution.",
        )
    )

    executed = client.post(
        f"/api/ai-chat/threads/{thread['thread_id']}/action-drafts/{draft['draft_id']}/paper-execute",
        json={"terminal_connected": True},
    )
    assert executed.status_code == 200
    payload = executed.json()
    assert payload["execution_intent_id"].startswith("exec_")
    assert payload["receipt_id"].startswith("rcpt_")
    assert payload["action_draft"]["side_effect_status"] == "paper_execution_acknowledged"

    app.dependency_overrides.clear()
