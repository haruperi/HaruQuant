"""Builders for compact AI chat page context."""

from __future__ import annotations

from services.context_builders import get_context_builder
from services.schemas.chat import PageContext


def build_page_context(
    *,
    route: str | None = None,
    page_title: str | None = None,
    session_id: int | None = None,
    symbol: str | None = None,
    timeframe: str | None = None,
    dom_snapshot: dict[str, object] | None = None,
    page_intelligence: dict[str, object] | None = None,
) -> PageContext:
    identity = dict((page_intelligence or {}).get("pageIdentity") or {})
    page_type_hint = str(identity.get("pageType") or "") or None
    builder, _page_type = get_context_builder(route, page_type_hint)
    return builder(
        route=route,
        page_title=page_title,
        session_id=session_id,
        symbol=symbol,
        timeframe=timeframe,
        dom_snapshot=dom_snapshot,
        page_intelligence=page_intelligence,
    )
