"""Builders for compact CEO chat page context."""

from __future__ import annotations

from uuid import uuid4

from services.context.freshness import freshness_payload
from services.schemas.chat import ChatEntityRef, PageContext

PAGE_TYPES = {
    "dashboard",
    "strategy_detail",
    "backtest_detail",
    "optimization_detail",
    "portfolio_risk",
    "live_trading",
    "data_workspace",
    "operator_workflow",
    "generic",
}


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
    entities: list[ChatEntityRef] = []
    if session_id is not None:
        entities.append(ChatEntityRef(type="session", id=str(session_id), label=f"Session {session_id}"))
    if symbol:
        entities.append(ChatEntityRef(type="symbol", id=symbol, label=symbol))
    if timeframe:
        entities.append(ChatEntityRef(type="timeframe", id=timeframe, label=timeframe))

    page_type = "generic"
    identity = {}
    if page_intelligence:
        identity = dict(page_intelligence.get("pageIdentity") or {})
        page_type = str(identity.get("pageType") or page_type)

    return PageContext(
        route=route or str(identity.get("route") or "/"),
        page_type=page_type if page_type in PAGE_TYPES else "generic",  # type: ignore[arg-type]
        page_title=page_title or str(identity.get("title") or "") or None,
        entity_refs=entities,
        context_revision=f"ctx-{uuid4()}",
        freshness=freshness_payload(),
        authority={"source": "ui", "trust_level": "system_state"},
        summary={
            "headline": page_title or str(identity.get("title") or "Current HaruQuant page"),
            "bullets": [value for value in [symbol, timeframe, f"session {session_id}" if session_id else None] if value],
        },
        payload={
            "dom": dom_snapshot or {},
            "page_intelligence": page_intelligence or {},
        },
    )
