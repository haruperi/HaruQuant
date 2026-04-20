"""AI chatbot endpoints for contract freeze and Phase 2 conversation memory."""

from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query, status
from fastapi.responses import JSONResponse, PlainTextResponse, StreamingResponse
from pydantic import BaseModel, ConfigDict, Field

from backend.api.auth_utils import get_user_id_from_token
from backend.data.database.repositories.ai_chat_repository import AiChatRepository
from backend.data.database.sqlite.database_operations import DatabaseManager
from backend.services.trade_action_governor import TradeActionGovernor
from backend.services.ai_chat import (
    ALLOWED_TIERS_BY_AUTHORITY_BAND,
    AIGatewayService,
    AuthorityBand,
    ChatStreamManager,
    ChatStreamRequest,
    ConversationService,
    PageContextAssembler,
)


router = APIRouter()
AUTHENTICATED_USER_ID = Annotated[int, Depends(get_user_id_from_token)]


class CreateThreadRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    title: str | None = Field(default=None, max_length=128)
    current_route: str | None = None
    current_page_type: str | None = None
    active_context_revision: str | None = None


class UpdateThreadContextRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    current_route: str | None = None
    current_page_type: str | None = None
    active_context_revision: str | None = None


class RenameThreadRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    title: str = Field(min_length=1, max_length=128)


class AddMessageRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    role: str = Field(pattern="^(system|user|assistant|tool)$")
    content: str = Field(min_length=1)
    request_id: str | None = None
    context_revision: str | None = None
    tool_calls: list[str] = Field(default_factory=list)
    signal_proposal_id: str | None = None
    action_draft_id: str | None = None


class RefreshSummaryRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    source: str | None = None


class UpsertPinnedFactRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    key: str = Field(min_length=1)
    value: str = Field(min_length=1)
    source: str = Field(min_length=1)


class StreamChatRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    prompt: str = Field(min_length=1)
    request_id: str | None = None
    include_debug: bool = False


class ExportThreadResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    thread_id: str
    title: str
    format: str
    content: object


class ListSignalProposalsResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    proposals: list[dict]


class RequestActionDraftApprovalRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    actor_type: str = Field(default="user", min_length=1)


class ExecutePaperActionDraftRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    terminal_connected: bool = True


def get_conversation_service() -> ConversationService:
    db_manager = DatabaseManager()
    return ConversationService(AiChatRepository(db_manager.db_path))


def get_page_context_assembler() -> PageContextAssembler:
    return PageContextAssembler(db_manager=DatabaseManager())


def get_trade_action_governor() -> TradeActionGovernor:
    db_manager = DatabaseManager()
    return TradeActionGovernor(db_manager.db_path)


def get_ai_gateway(
    conversation_service: Annotated[ConversationService, Depends(get_conversation_service)],
    context_assembler: Annotated[PageContextAssembler, Depends(get_page_context_assembler)],
) -> AIGatewayService:
    return AIGatewayService(
        conversation_service=conversation_service,
        context_assembler=context_assembler,
    )


@router.get("/phase0/contracts")
def get_ai_chat_phase0_contracts() -> dict:
    """Expose frozen Phase 0 contract metadata for implementation alignment."""

    return {
        "feature": "haruquant_ai_chatbot",
        "phase": 0,
        "contracts": {
            "page_context": "PageContextPacket@1.0.0",
            "chat_event": "ChatLifecycleEvent@1.0.0",
            "conversation_thread_model": "ConversationThreadRecord",
        },
        "authority_bands": {
            band.value: [tier.value for tier in ALLOWED_TIERS_BY_AUTHORITY_BAND[band]]
            for band in AuthorityBand
        },
        "supported_page_types": sorted(
            {descriptor.page_type for descriptor in PageContextAssembler().registry} | {"generic"}
        ),
    }


@router.get("/phase0/route-contexts")
def get_ai_chat_route_contexts() -> list[dict[str, str]]:
    """Expose the frozen route-to-context registry for page-aware assembly."""

    assembler = PageContextAssembler()
    return [
        {
            "route_pattern": descriptor.route_pattern,
            "page_type": descriptor.page_type,
            "builder_name": descriptor.builder_name,
        }
        for descriptor in assembler.registry
    ]


@router.get("/context")
def get_page_context(
    route: str,
    page_title: str | None = None,
    user_id: AUTHENTICATED_USER_ID = None,
    assembler: Annotated[PageContextAssembler, Depends(get_page_context_assembler)] = None,
) -> dict:
    packet = assembler.assemble_context(route=route, user_id=user_id, page_title=page_title)
    return packet.model_dump(mode="json")


@router.get("/threads")
def list_threads(
    user_id: AUTHENTICATED_USER_ID,
    service: Annotated[ConversationService, Depends(get_conversation_service)],
    q: str | None = Query(default=None, max_length=128),
) -> list[dict]:
    return [thread.model_dump(mode="json") for thread in service.list_threads(user_id=user_id, query=q)]


@router.post("/threads", status_code=status.HTTP_201_CREATED)
def create_thread(
    payload: CreateThreadRequest,
    user_id: AUTHENTICATED_USER_ID,
    service: Annotated[ConversationService, Depends(get_conversation_service)],
) -> dict:
    thread = service.create_thread(
        user_id=user_id,
        title=payload.title,
        current_route=payload.current_route,
        current_page_type=payload.current_page_type,
        active_context_revision=payload.active_context_revision,
    )
    return thread.model_dump(mode="json")


@router.get("/threads/{thread_id}")
def get_thread(
    thread_id: str,
    user_id: AUTHENTICATED_USER_ID,
    service: Annotated[ConversationService, Depends(get_conversation_service)],
) -> dict:
    try:
        thread = service.get_thread(user_id=user_id, thread_id=thread_id)
    except LookupError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
    return thread.model_dump(mode="json")


@router.patch("/threads/{thread_id}/context")
def update_thread_context(
    thread_id: str,
    payload: UpdateThreadContextRequest,
    user_id: AUTHENTICATED_USER_ID,
    service: Annotated[ConversationService, Depends(get_conversation_service)],
) -> dict:
    try:
        thread = service.update_thread_context(
            user_id=user_id,
            thread_id=thread_id,
            current_route=payload.current_route,
            current_page_type=payload.current_page_type,
            active_context_revision=payload.active_context_revision,
        )
    except LookupError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
    return thread.model_dump(mode="json")


@router.patch("/threads/{thread_id}")
def rename_thread(
    thread_id: str,
    payload: RenameThreadRequest,
    user_id: AUTHENTICATED_USER_ID,
    service: Annotated[ConversationService, Depends(get_conversation_service)],
) -> dict:
    try:
        thread = service.rename_thread(
            user_id=user_id,
            thread_id=thread_id,
            title=payload.title,
        )
    except LookupError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc
    return thread.model_dump(mode="json")


@router.delete("/threads/{thread_id}")
def delete_thread(
    thread_id: str,
    user_id: AUTHENTICATED_USER_ID,
    service: Annotated[ConversationService, Depends(get_conversation_service)],
) -> dict:
    deleted = service.delete_thread(user_id=user_id, thread_id=thread_id)
    if not deleted:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"thread not found: {thread_id}")
    return {"deleted": True, "thread_id": thread_id}


@router.get("/threads/{thread_id}/export")
def export_thread(
    thread_id: str,
    format: str = Query(default="markdown", pattern="^(markdown|json)$"),
    user_id: AUTHENTICATED_USER_ID = None,
    service: Annotated[ConversationService, Depends(get_conversation_service)] = None,
):
    try:
        exported = service.export_thread(user_id=user_id, thread_id=thread_id, format=format)
    except LookupError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc
    if format == "json":
        return JSONResponse(exported)
    return PlainTextResponse(str(exported["content"]))


@router.post("/threads/{thread_id}/messages", status_code=status.HTTP_201_CREATED)
def add_message(
    thread_id: str,
    payload: AddMessageRequest,
    user_id: AUTHENTICATED_USER_ID,
    service: Annotated[ConversationService, Depends(get_conversation_service)],
) -> dict:
    try:
        message = service.add_message(
            user_id=user_id,
            thread_id=thread_id,
            role=payload.role,
            content=payload.content,
            request_id=payload.request_id,
            context_revision=payload.context_revision,
            tool_calls=payload.tool_calls,
            signal_proposal_id=payload.signal_proposal_id,
            action_draft_id=payload.action_draft_id,
        )
    except LookupError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
    return message.model_dump(mode="json")


@router.post("/threads/{thread_id}/summary/refresh")
def refresh_memory_summary(
    thread_id: str,
    _: RefreshSummaryRequest,
    user_id: AUTHENTICATED_USER_ID,
    service: Annotated[ConversationService, Depends(get_conversation_service)],
) -> dict:
    try:
        summary = service.refresh_memory_summary(user_id=user_id, thread_id=thread_id)
    except LookupError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
    return summary.model_dump(mode="json")


@router.put("/threads/{thread_id}/pinned-facts")
def upsert_pinned_fact(
    thread_id: str,
    payload: UpsertPinnedFactRequest,
    user_id: AUTHENTICATED_USER_ID,
    service: Annotated[ConversationService, Depends(get_conversation_service)],
) -> dict:
    try:
        fact = service.upsert_pinned_fact(
            user_id=user_id,
            thread_id=thread_id,
            key=payload.key,
            value=payload.value,
            source=payload.source,
        )
    except LookupError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
    return fact.model_dump(mode="json")


@router.get("/threads/{thread_id}/signal-proposals")
def list_signal_proposals(
    thread_id: str,
    user_id: AUTHENTICATED_USER_ID,
    service: Annotated[ConversationService, Depends(get_conversation_service)],
    status: str | None = Query(default=None, pattern="^(draft|watchlist|review_queue)$"),
) -> list[dict]:
    return [
        proposal.model_dump(mode="json")
        for proposal in service.list_signal_proposals(user_id=user_id, thread_id=thread_id, status=status)
    ]


@router.post("/threads/{thread_id}/signal-proposals/{proposal_id}/watchlist")
def save_signal_proposal_to_watchlist(
    thread_id: str,
    proposal_id: str,
    user_id: AUTHENTICATED_USER_ID,
    service: Annotated[ConversationService, Depends(get_conversation_service)],
) -> dict:
    _ = service.get_thread(user_id=user_id, thread_id=thread_id)
    existing = service.get_signal_proposal(user_id=user_id, proposal_id=proposal_id)
    if existing.thread_id != thread_id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"signal proposal not found in thread: {proposal_id}")
    proposal = service.save_signal_proposal_to_watchlist(user_id=user_id, proposal_id=proposal_id)
    return proposal.model_dump(mode="json")


@router.post("/threads/{thread_id}/signal-proposals/{proposal_id}/review-queue")
def queue_signal_proposal_for_review(
    thread_id: str,
    proposal_id: str,
    user_id: AUTHENTICATED_USER_ID,
    service: Annotated[ConversationService, Depends(get_conversation_service)],
) -> dict:
    _ = service.get_thread(user_id=user_id, thread_id=thread_id)
    existing = service.get_signal_proposal(user_id=user_id, proposal_id=proposal_id)
    if existing.thread_id != thread_id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"signal proposal not found in thread: {proposal_id}")
    proposal = service.queue_signal_proposal_for_review(user_id=user_id, proposal_id=proposal_id)
    return proposal.model_dump(mode="json")


@router.get("/threads/{thread_id}/action-drafts")
def list_action_drafts(
    thread_id: str,
    user_id: AUTHENTICATED_USER_ID,
    service: Annotated[ConversationService, Depends(get_conversation_service)],
    status: str | None = Query(default=None, pattern="^(draft|approval_requested|approved|rejected|cancelled)$"),
) -> list[dict]:
    _ = service.get_thread(user_id=user_id, thread_id=thread_id)
    return [
        draft.model_dump(mode="json")
        for draft in service.list_action_drafts(user_id=user_id, thread_id=thread_id, status=status)
    ]


@router.post("/threads/{thread_id}/action-drafts/{draft_id}/request-approval")
def request_action_draft_approval(
    thread_id: str,
    draft_id: str,
    payload: RequestActionDraftApprovalRequest,
    user_id: AUTHENTICATED_USER_ID,
    service: Annotated[ConversationService, Depends(get_conversation_service)],
) -> dict:
    _ = service.get_thread(user_id=user_id, thread_id=thread_id)
    existing = service.get_action_draft(user_id=user_id, draft_id=draft_id)
    if existing.thread_id != thread_id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"action draft not found in thread: {draft_id}")
    draft = service.request_action_draft_approval(
        user_id=user_id,
        draft_id=draft_id,
        actor_type=payload.actor_type,
    )
    return draft.model_dump(mode="json")


@router.post("/threads/{thread_id}/action-drafts/{draft_id}/paper-execute")
def execute_paper_action_draft(
    thread_id: str,
    draft_id: str,
    payload: ExecutePaperActionDraftRequest,
    user_id: AUTHENTICATED_USER_ID,
    service: Annotated[ConversationService, Depends(get_conversation_service)],
    governor: Annotated[TradeActionGovernor, Depends(get_trade_action_governor)],
) -> dict:
    _ = service.get_thread(user_id=user_id, thread_id=thread_id)
    existing = service.get_action_draft(user_id=user_id, draft_id=draft_id)
    if existing.thread_id != thread_id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"action draft not found in thread: {draft_id}")
    try:
        result = governor.execute_paper_action_draft(
            user_id=user_id,
            draft_id=draft_id,
            terminal_connected=payload.terminal_connected,
        )
    except PermissionError as exc:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc
    return {
        "workflow_id": result.workflow_id,
        "execution_intent_id": result.execution_intent_id,
        "receipt_id": result.receipt_id,
        "authority_state": result.authority_state,
        "approval_state": {
            "approval_id": result.approval_state.approval_id,
            "state": result.approval_state.state,
            "approve_count": result.approval_state.approve_count,
            "reject_count": result.approval_state.reject_count,
            "required_count": result.approval_state.required_count,
            "eligible": result.approval_state.eligible,
            "reason_codes": list(result.approval_state.reason_codes),
        },
        "action_draft": result.action_draft.model_dump(mode="json"),
    }


@router.post("/threads/{thread_id}/responses/stream")
def stream_thread_response(
    thread_id: str,
    payload: StreamChatRequest,
    user_id: AUTHENTICATED_USER_ID,
    gateway: Annotated[AIGatewayService, Depends(get_ai_gateway)],
) -> StreamingResponse:
    stream_manager = ChatStreamManager()

    def event_stream():
        try:
            metadata, chunks, message_id = gateway.stream_response(
                ChatStreamRequest(
                    user_id=user_id,
                    thread_id=thread_id,
                    prompt=payload.prompt,
                    request_id=payload.request_id,
                    include_debug=payload.include_debug,
                )
            )
            yield stream_manager.meta_event(metadata)
            full_text = ""
            for chunk in chunks:
                full_text += chunk
                yield from stream_manager.token_events([chunk])
            yield stream_manager.done_event(
                {
                    "message_id": message_id,
                    "content": full_text,
                    **metadata,
                }
            )
        except LookupError as exc:
            yield stream_manager.error_event(str(exc))
        except Exception as exc:  # pragma: no cover - defensive path
            yield stream_manager.error_event(f"AI gateway failed: {exc}")

    return StreamingResponse(event_stream(), media_type="text/event-stream")


@router.post("/threads/{thread_id}/responses/regenerate")
def regenerate_thread_response(
    thread_id: str,
    payload: StreamChatRequest,
    user_id: AUTHENTICATED_USER_ID,
    gateway: Annotated[AIGatewayService, Depends(get_ai_gateway)],
    service: Annotated[ConversationService, Depends(get_conversation_service)],
) -> StreamingResponse:
    stream_manager = ChatStreamManager()

    def event_stream():
        try:
            last_prompt = service.get_last_user_prompt(user_id=user_id, thread_id=thread_id)
            metadata, chunks, message_id = gateway.stream_response(
                ChatStreamRequest(
                    user_id=user_id,
                    thread_id=thread_id,
                    prompt=last_prompt.content,
                    request_id=payload.request_id,
                    include_debug=payload.include_debug,
                    persist_user_message=False,
                )
            )
            yield stream_manager.meta_event({**metadata, "regenerated_from_message_id": last_prompt.message_id})
            full_text = ""
            for chunk in chunks:
                full_text += chunk
                yield from stream_manager.token_events([chunk])
            yield stream_manager.done_event(
                {
                    "message_id": message_id,
                    "content": full_text,
                    "regenerated_from_message_id": last_prompt.message_id,
                    **metadata,
                }
            )
        except LookupError as exc:
            yield stream_manager.error_event(str(exc))
        except Exception as exc:  # pragma: no cover - defensive path
            yield stream_manager.error_event(f"AI gateway failed: {exc}")

    return StreamingResponse(event_stream(), media_type="text/event-stream")
