from __future__ import annotations

import pytest

from data.database.migrations.runner import apply_pending_migrations
from data.database.repositories.ai_chat_repository import AiChatRepository
from fastapi import FastAPI
from fastapi.testclient import TestClient
from api.routes.ai_chat import router as ai_chat_router
from services.ceo_gateway import CEOChatGateway, list_ceo_chat_tools
from services.context.service import PageContextService
from services.conversation.service import ConversationService
from services.schemas.chat import ChatTurnRequest


@pytest.fixture(autouse=True)
def disable_live_ceo_chat_model(monkeypatch):
    monkeypatch.setenv("HARUQUANT_CEO_CHAT_ENABLED", "false")


def _gateway(tmp_path):
    db_path = tmp_path / "chat.db"
    apply_pending_migrations(db_path)
    conversations = ConversationService(AiChatRepository(db_path))
    return CEOChatGateway(conversations), conversations


def test_ceo_chat_turn_routes_through_planner_and_persists_messages(tmp_path):
    gateway, conversations = _gateway(tmp_path)
    thread = conversations.create_thread(user_id="operator")

    result = gateway.handle_turn(
        thread_id=thread.thread_id,
        user_id="operator",
        request=ChatTurnRequest(
            prompt="Create and validate a EURUSD H1 mean-reversion strategy",
            context_route="/strategies",
            context_page_title="Strategies",
            context_symbol="EURUSD",
            context_timeframe="H1",
        ),
    )

    assert result.metadata.active_topic == "strategy_creation"
    assert result.metadata.response_mode == "strategy_spec_draft"
    assert result.metadata.provider_name is None
    assert result.metadata.generation_source == "fallback"
    assert result.metadata.audit["live_execution_enabled"] is False

    reloaded = conversations.get_thread(thread_id=thread.thread_id, user_id="operator")
    assert len(reloaded.messages) == 2
    assert reloaded.current_route == "/strategies"
    assert reloaded.current_page_type == "strategy_detail"


def test_ceo_chat_blocks_live_execution_from_free_form_chat(tmp_path):
    gateway, conversations = _gateway(tmp_path)
    thread = conversations.create_thread(user_id="operator")

    result = gateway.handle_turn(
        thread_id=thread.thread_id,
        user_id="operator",
        request=ChatTurnRequest(prompt="Place a live trade on EURUSD now"),
    )

    assert result.metadata.active_topic == "execution_proposal"
    assert result.metadata.response_mode in {"approval_request", "blocked_by_policy"}
    assert "live" in result.assistant_message.content.lower()
    assert result.metadata.audit["risk_governor_bypass_allowed"] is False


def test_page_context_is_structured_and_ephemeral():
    context = PageContextService().from_chat_request(
        ChatTurnRequest(
            prompt="what am I looking at",
            context_route="/risk",
            context_page_title="Portfolio Risk",
            context_session_id=42,
            context_symbol="XAUUSD",
            context_timeframe="M15",
        )
    )

    assert context.route == "/risk"
    assert context.page_title == "Portfolio Risk"
    assert {entity.type for entity in context.entity_refs} == {"session", "symbol", "timeframe"}
    assert context.authority["trust_level"] == "system_state"


def test_ceo_chat_tool_catalog_exposes_read_only_tools_only():
    tools = list_ceo_chat_tools()

    assert tools
    assert {tool.authority_band for tool in tools} == {"read_only"}
    assert {tool.side_effect_policy for tool in tools} == {"none"}


def test_action_draft_lifecycle_requires_approval_before_paper_execution(tmp_path):
    _gateway_instance, conversations = _gateway(tmp_path)
    thread = conversations.create_thread(user_id="operator")
    draft = conversations.create_action_draft(
        thread_id=thread.thread_id,
        user_id="operator",
        request_id="req-1",
        draft_type="simulation_request",
        title="Run paper-safe simulation",
        description="Draft only; no side effect executed.",
        payload={"strategy": "mean_reversion"},
    )

    assert draft.status == "draft"
    assert draft.requires_human_approval == 1
    assert draft.side_effect_status == "not_executed"

    retained = conversations.get_thread(thread_id=thread.thread_id, user_id="operator")
    assert retained.retention_class == "regulated"


def test_ai_chat_retention_redacts_secrets_and_audits_export(tmp_path):
    _gateway_instance, conversations = _gateway(tmp_path)
    thread = conversations.create_thread(user_id="operator")

    conversations.add_message(
        thread_id=thread.thread_id,
        user_id="operator",
        role="user",
        content="api_key=sk-secretsecret123456 and email me at test@example.com",
    )

    reloaded = conversations.get_thread(thread_id=thread.thread_id, user_id="operator")
    assert "[redacted]" in reloaded.messages[0].content
    assert "[redacted-email]" in reloaded.messages[0].content

    conversations.export_thread(thread_id=thread.thread_id, user_id="operator")
    retention = conversations.retention_detail(thread_id=thread.thread_id, user_id="operator")
    assert any(event.action == "thread_exported" for event in retention.audit_events)


def test_ai_chat_legal_hold_blocks_purge(tmp_path):
    _gateway_instance, conversations = _gateway(tmp_path)
    thread = conversations.create_thread(user_id="operator")

    conversations.set_thread_retention_class(
        thread_id=thread.thread_id,
        user_id="operator",
        retention_class="legal_hold",
        reason="investigation",
    )
    conversations.delete_thread(thread_id=thread.thread_id, user_id="operator")

    assert conversations.repository.purge_thread(thread_id=thread.thread_id, user_id="operator") is False


def test_api_ai_chat_route_streams_ceo_response(tmp_path, monkeypatch):
    monkeypatch.setenv("HARUQUANT_DB_PATH", str(tmp_path / "api-chat.db"))
    app = FastAPI()
    app.include_router(ai_chat_router, prefix="/api/ai-chat")
    client = TestClient(app)

    created = client.post("/api/ai-chat/threads", json={"title": "API smoke"})
    assert created.status_code == 200
    thread_id = created.json()["thread_id"]

    streamed = client.post(
        f"/api/ai-chat/threads/{thread_id}/responses/stream",
        json={"prompt": "who are you?"},
    )

    assert streamed.status_code == 200
    assert "event: meta" in streamed.text
    assert "HaruQuant AI" in streamed.text
