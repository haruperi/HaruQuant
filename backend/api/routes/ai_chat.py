"""AI chatbot endpoints for contract freeze and Phase 2 conversation memory."""

from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, ConfigDict, Field

from backend.api.auth_utils import get_user_id_from_token
from backend.data.database.repositories.ai_chat_repository import AiChatRepository
from backend.data.database.sqlite.database_operations import DatabaseManager
from backend.services.ai_chat import (
    ALLOWED_TIERS_BY_AUTHORITY_BAND,
    AuthorityBand,
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


class AddMessageRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    role: str = Field(pattern="^(system|user|assistant|tool)$")
    content: str = Field(min_length=1)
    request_id: str | None = None
    context_revision: str | None = None
    tool_calls: list[str] = Field(default_factory=list)


class RefreshSummaryRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    source: str | None = None


class UpsertPinnedFactRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    key: str = Field(min_length=1)
    value: str = Field(min_length=1)
    source: str = Field(min_length=1)


def get_conversation_service() -> ConversationService:
    db_manager = DatabaseManager()
    return ConversationService(AiChatRepository(db_manager.db_path))


def get_page_context_assembler() -> PageContextAssembler:
    return PageContextAssembler(db_manager=DatabaseManager())


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
) -> list[dict]:
    return [thread.model_dump(mode="json") for thread in service.list_threads(user_id=user_id)]


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
