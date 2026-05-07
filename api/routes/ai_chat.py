"""CEO chat endpoints for the canonical HaruQuant API package."""

from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Query, Response
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field

from data.database.migrations.runner import apply_pending_migrations
from data.database.repositories.ai_chat_repository import AiChatRepository
from services.ceo_gateway import CEOChatGateway
from services.context.builders import build_page_context
from services.conversation.service import ConversationService
from services.schemas.chat import ChatMessage, ChatRetentionPolicyDetail, ChatThread, ChatThreadDetail, ChatTurnRequest
from tools.read_only import list_read_only_tool_definitions


router = APIRouter()


class ThreadCreatePayload(BaseModel):
    title: str | None = None
    current_route: str | None = None
    current_page_type: str | None = None
    active_context_revision: str | None = None


class ThreadRenamePayload(BaseModel):
    title: str


class ThreadRetentionPayload(BaseModel):
    retention_class: str
    reason: str = "Retention policy updated by user."


class LifecycleRunPayload(BaseModel):
    dry_run: bool = False


class MessageCreatePayload(BaseModel):
    role: str
    content: str
    request_id: str | None = None
    context_revision: str | None = None
    tool_calls: list[str] = Field(default_factory=list)
    signal_proposal_id: str | None = None
    action_draft_id: str | None = None


class ApprovalPayload(BaseModel):
    actor_type: str = "user"


class PaperExecutePayload(BaseModel):
    terminal_connected: bool = False


class ContextResolvePayload(BaseModel):
    route: str | None = None
    page_title: str | None = None
    page_state: dict[str, Any] = Field(default_factory=dict)
    dom: dict[str, Any] = Field(default_factory=dict)


def default_database_path() -> Path:
    return Path(os.getenv("HARUQUANT_DB_PATH", "data/database/haruquant-dev.db"))


def get_user_id() -> str:
    return os.getenv("HARUQUANT_DEV_USER_ID", "local-operator")


def get_conversation_service() -> ConversationService:
    db_path = default_database_path()
    apply_pending_migrations(db_path)
    return ConversationService(AiChatRepository(db_path))


def get_ceo_chat_gateway() -> CEOChatGateway:
    return CEOChatGateway(get_conversation_service())


@router.get("/threads", response_model=list[ChatThread])
def list_threads(
    q: str | None = Query(default=None),
    include_archived: bool = Query(default=False),
    user_id: str = Depends(get_user_id),
    conversations: ConversationService = Depends(get_conversation_service),
) -> list[ChatThread]:
    return conversations.list_threads(user_id=user_id, query=q, include_archived=include_archived)


@router.post("/threads", response_model=ChatThreadDetail)
def create_thread(
    payload: ThreadCreatePayload,
    user_id: str = Depends(get_user_id),
    conversations: ConversationService = Depends(get_conversation_service),
) -> ChatThreadDetail:
    return conversations.create_thread(
        user_id=user_id,
        title=payload.title,
        current_route=payload.current_route,
        current_page_type=payload.current_page_type,
        active_context_revision=payload.active_context_revision,
    )


@router.get("/threads/{thread_id}", response_model=ChatThreadDetail)
def get_thread(
    thread_id: str,
    user_id: str = Depends(get_user_id),
    conversations: ConversationService = Depends(get_conversation_service),
) -> ChatThreadDetail:
    try:
        return conversations.get_thread(thread_id=thread_id, user_id=user_id)
    except LookupError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@router.patch("/threads/{thread_id}", response_model=ChatThreadDetail)
def rename_thread(
    thread_id: str,
    payload: ThreadRenamePayload,
    user_id: str = Depends(get_user_id),
    conversations: ConversationService = Depends(get_conversation_service),
) -> ChatThreadDetail:
    return conversations.rename_thread(thread_id=thread_id, user_id=user_id, title=payload.title)


@router.patch("/threads/{thread_id}/context", response_model=ChatThreadDetail)
def update_thread_context(
    thread_id: str,
    payload: ThreadCreatePayload,
    user_id: str = Depends(get_user_id),
    conversations: ConversationService = Depends(get_conversation_service),
) -> ChatThreadDetail:
    try:
        return conversations.update_context(
            thread_id=thread_id,
            user_id=user_id,
            current_route=payload.current_route,
            current_page_type=payload.current_page_type,
            active_context_revision=payload.active_context_revision,
        )
    except LookupError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@router.delete("/threads/{thread_id}")
def delete_thread(
    thread_id: str,
    user_id: str = Depends(get_user_id),
    conversations: ConversationService = Depends(get_conversation_service),
) -> dict[str, bool]:
    return {"deleted": conversations.delete_thread(thread_id=thread_id, user_id=user_id)}


@router.post("/threads/{thread_id}/archive", response_model=ChatThreadDetail)
def archive_thread(
    thread_id: str,
    user_id: str = Depends(get_user_id),
    conversations: ConversationService = Depends(get_conversation_service),
) -> ChatThreadDetail:
    try:
        return conversations.archive_thread(thread_id=thread_id, user_id=user_id)
    except LookupError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@router.post("/threads/{thread_id}/restore", response_model=ChatThreadDetail)
def restore_thread(
    thread_id: str,
    user_id: str = Depends(get_user_id),
    conversations: ConversationService = Depends(get_conversation_service),
) -> ChatThreadDetail:
    try:
        return conversations.restore_thread(thread_id=thread_id, user_id=user_id)
    except LookupError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@router.post("/threads/{thread_id}/purge")
def purge_thread(
    thread_id: str,
    user_id: str = Depends(get_user_id),
    conversations: ConversationService = Depends(get_conversation_service),
) -> dict[str, bool]:
    return {
        "purged": conversations.repository.purge_thread(
            thread_id=thread_id,
            user_id=user_id,
            actor_id=user_id,
            reason="User requested purge review from AI Chat.",
        )
    }


@router.get("/threads/{thread_id}/retention", response_model=ChatRetentionPolicyDetail)
def get_thread_retention(
    thread_id: str,
    user_id: str = Depends(get_user_id),
    conversations: ConversationService = Depends(get_conversation_service),
) -> ChatRetentionPolicyDetail:
    try:
        return conversations.retention_detail(thread_id=thread_id, user_id=user_id)
    except LookupError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@router.patch("/threads/{thread_id}/retention", response_model=ChatThreadDetail)
def update_thread_retention(
    thread_id: str,
    payload: ThreadRetentionPayload,
    user_id: str = Depends(get_user_id),
    conversations: ConversationService = Depends(get_conversation_service),
) -> ChatThreadDetail:
    try:
        return conversations.set_thread_retention_class(
            thread_id=thread_id,
            user_id=user_id,
            retention_class=payload.retention_class,
            reason=payload.reason,
        )
    except LookupError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.post("/retention/lifecycle-run")
def run_retention_lifecycle(
    payload: LifecycleRunPayload,
    conversations: ConversationService = Depends(get_conversation_service),
) -> dict[str, Any]:
    if payload.dry_run:
        return {"dry_run": True, "decisions": []}
    decisions = conversations.retention.run_lifecycle()
    return {"dry_run": False, "decisions": [decision.__dict__ for decision in decisions]}


@router.get("/threads/{thread_id}/export")
def export_thread(
    thread_id: str,
    format: str = "markdown",
    user_id: str = Depends(get_user_id),
    conversations: ConversationService = Depends(get_conversation_service),
) -> Response:
    exported = conversations.export_thread(thread_id=thread_id, user_id=user_id, format=format)
    media_type = "application/json" if format == "json" else "text/markdown"
    return Response(content=exported, media_type=media_type)


@router.post("/threads/{thread_id}/messages", response_model=ChatMessage)
def create_message(
    thread_id: str,
    payload: MessageCreatePayload,
    user_id: str = Depends(get_user_id),
    conversations: ConversationService = Depends(get_conversation_service),
) -> ChatMessage:
    return conversations.add_message(
        thread_id=thread_id,
        user_id=user_id,
        role=payload.role,
        content=payload.content,
        request_id=payload.request_id,
        context_revision=payload.context_revision,
        tool_calls=payload.tool_calls,
        signal_proposal_id=payload.signal_proposal_id,
        action_draft_id=payload.action_draft_id,
    )


@router.get("/tools")
def list_tools() -> list[dict[str, Any]]:
    return [
        {
            **tool.model_dump(),
            "capability_type": "haruquant_read_only",
            "authority_band": "read_only",
            "side_effect_policy": "none",
            "required_context": [],
            "allowed_backend_tools": [tool.tool_id],
            "allowed_specialist_agents": ["read_only_tool_executor"],
            "artifact_type": "state_snapshot",
            "required_user_ack": False,
        }
        for tool in list_read_only_tool_definitions()
    ]


@router.post("/context/resolve")
def resolve_context(payload: ContextResolvePayload) -> dict[str, Any]:
    page_state = payload.page_state or {}
    page_context = build_page_context(
        route=payload.route,
        page_title=payload.page_title,
        session_id=page_state.get("session_id") if isinstance(page_state.get("session_id"), int) else None,
        symbol=page_state.get("symbol") if isinstance(page_state.get("symbol"), str) else None,
        timeframe=page_state.get("timeframe") if isinstance(page_state.get("timeframe"), str) else None,
        dom_snapshot=payload.dom,
        page_intelligence=page_state.get("page_intelligence") if isinstance(page_state.get("page_intelligence"), dict) else None,
    )
    return {"payload": page_context.model_dump()}


def _signal_row(row: Any) -> dict[str, Any]:
    return {
        "proposal_id": row.proposal_id,
        "thread_id": row.thread_id,
        "user_id": row.user_id,
        "request_id": row.request_id,
        "title": row.title,
        "hypothesis": row.hypothesis,
        "symbol": row.symbol,
        "timeframe": row.timeframe,
        "direction": row.direction,
        "entry_logic": row.entry_logic,
        "exit_logic": row.exit_logic,
        "confidence": row.confidence,
        "rationale": row.rationale,
        "risk_note": row.risk_note,
        "status": row.status,
        "watchlist_saved": bool(row.watchlist_saved),
        "review_queue_saved": bool(row.review_queue_saved),
        "non_executed_label": row.non_executed_label,
        "created_at": row.created_at,
        "updated_at": row.updated_at,
    }


def _action_row(row: Any) -> dict[str, Any]:
    return {
        "draft_id": row.draft_id,
        "thread_id": row.thread_id,
        "user_id": row.user_id,
        "request_id": row.request_id,
        "draft_type": row.draft_type,
        "title": row.title,
        "description": row.description,
        "payload": json.loads(row.payload_json or "{}"),
        "risk_precheck_status": row.risk_precheck_status,
        "risk_precheck_notes": row.risk_precheck_notes,
        "approval_id": row.approval_id,
        "status": row.status,
        "requires_human_approval": bool(row.requires_human_approval),
        "side_effect_status": row.side_effect_status,
        "governed_workflow_id": row.governed_workflow_id,
        "execution_intent_id": row.execution_intent_id,
        "execution_receipt_id": row.execution_receipt_id,
        "created_at": row.created_at,
        "updated_at": row.updated_at,
    }


@router.get("/threads/{thread_id}/signal-proposals")
def list_signal_proposals(
    thread_id: str,
    user_id: str = Depends(get_user_id),
    conversations: ConversationService = Depends(get_conversation_service),
) -> list[dict[str, Any]]:
    return [_signal_row(row) for row in conversations.repository.list_signal_proposals(user_id=user_id, thread_id=thread_id)]


@router.post("/threads/{thread_id}/signal-proposals/{proposal_id}/watchlist")
def save_signal_proposal_to_watchlist(
    thread_id: str,
    proposal_id: str,
    user_id: str = Depends(get_user_id),
    conversations: ConversationService = Depends(get_conversation_service),
) -> dict[str, Any]:
    conversations.retention.mark_regulated(
        thread_id=thread_id,
        user_id=user_id,
        reason="Signal proposal saved to watchlist; conversation classified as regulated.",
    )
    row = conversations.repository.update_signal_proposal_state(
        proposal_id=proposal_id,
        user_id=user_id,
        status="watchlist",
        watchlist_saved=True,
    )
    return _signal_row(row)


@router.post("/threads/{thread_id}/signal-proposals/{proposal_id}/review-queue")
def queue_signal_proposal_for_review(
    thread_id: str,
    proposal_id: str,
    user_id: str = Depends(get_user_id),
    conversations: ConversationService = Depends(get_conversation_service),
) -> dict[str, Any]:
    conversations.retention.mark_regulated(
        thread_id=thread_id,
        user_id=user_id,
        reason="Signal proposal queued for review; conversation classified as regulated.",
    )
    row = conversations.repository.update_signal_proposal_state(
        proposal_id=proposal_id,
        user_id=user_id,
        status="review_queue",
        review_queue_saved=True,
    )
    return _signal_row(row)


@router.get("/threads/{thread_id}/action-drafts")
def list_action_drafts(
    thread_id: str,
    user_id: str = Depends(get_user_id),
    conversations: ConversationService = Depends(get_conversation_service),
) -> list[dict[str, Any]]:
    return [_action_row(row) for row in conversations.repository.list_action_drafts(user_id=user_id, thread_id=thread_id)]


@router.post("/threads/{thread_id}/action-drafts/{draft_id}/request-approval")
def request_action_draft_approval(
    thread_id: str,
    draft_id: str,
    payload: ApprovalPayload,
    user_id: str = Depends(get_user_id),
    conversations: ConversationService = Depends(get_conversation_service),
) -> dict[str, Any]:
    conversations.retention.mark_regulated(
        thread_id=thread_id,
        user_id=user_id,
        reason="Action draft approval requested; conversation classified as regulated.",
    )
    row = conversations.repository.update_action_draft(
        draft_id=draft_id,
        user_id=user_id,
        status="approval_requested",
        approval_id=f"{payload.actor_type}-approval-requested",
    )
    return _action_row(row)


@router.post("/threads/{thread_id}/action-drafts/{draft_id}/paper-execute")
def execute_paper_action_draft(
    thread_id: str,
    draft_id: str,
    payload: PaperExecutePayload,
    user_id: str = Depends(get_user_id),
    conversations: ConversationService = Depends(get_conversation_service),
) -> dict[str, Any]:
    current = conversations.repository.get_action_draft(draft_id=draft_id, user_id=user_id)
    if current is None:
        raise HTTPException(status_code=404, detail="action draft not found")
    if current.status != "approved":
        raise HTTPException(status_code=409, detail="paper execution requires an approved draft")
    row = conversations.repository.update_action_draft(
        draft_id=draft_id,
        user_id=user_id,
        side_effect_status="paper_executed" if payload.terminal_connected else "blocked_terminal_unavailable",
        governed_workflow_id=f"paper-{draft_id}",
    )
    return {"action_draft": _action_row(row)}


@router.post("/threads/{thread_id}/responses/stream")
def stream_response(
    thread_id: str,
    payload: ChatTurnRequest,
    user_id: str = Depends(get_user_id),
    gateway: CEOChatGateway = Depends(get_ceo_chat_gateway),
) -> StreamingResponse:
    def events():
        try:
            for event_name, data in gateway.stream_turn(thread_id=thread_id, user_id=user_id, request=payload):
                yield f"event: {event_name}\ndata: {json.dumps(data, default=str)}\n\n"
        except Exception as exc:  # pragma: no cover - defensive stream path
            yield f"event: error\ndata: {json.dumps({'message': str(exc)})}\n\n"

    return StreamingResponse(events(), media_type="text/event-stream")


@router.post("/threads/{thread_id}/responses/regenerate")
def regenerate_response(
    thread_id: str,
    payload: ChatTurnRequest,
    user_id: str = Depends(get_user_id),
    conversations: ConversationService = Depends(get_conversation_service),
    gateway: CEOChatGateway = Depends(get_ceo_chat_gateway),
) -> StreamingResponse:
    detail = conversations.get_thread(thread_id=thread_id, user_id=user_id)
    last_user = next((message for message in reversed(detail.messages) if message.role == "user"), None)
    regenerated = payload.model_copy(update={"prompt": last_user.content if last_user else payload.prompt})
    return stream_response(thread_id=thread_id, payload=regenerated, user_id=user_id, gateway=gateway)
