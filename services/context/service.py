"""Ephemeral page-context assembly for AI Chat turns."""

from __future__ import annotations

from services.context.builders import build_page_context
from services.schemas.chat import ChatTurnRequest, PageContext


class PageContextService:
    """Builds compact page context without persisting it as durable memory."""

    def from_chat_request(self, request: ChatTurnRequest) -> PageContext:
        return build_page_context(
            route=request.context_route,
            page_title=request.context_page_title,
            session_id=request.context_session_id,
            symbol=request.context_symbol,
            timeframe=request.context_timeframe,
            dom_snapshot=request.context_dom,
            page_intelligence=request.context_page_intelligence,
        )


class ContextAssembler(PageContextService):
    """Canonical context assembler alias used by route and chat services."""

