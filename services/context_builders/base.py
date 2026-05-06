"""Route-aware page-context builders for AI Chat."""

from __future__ import annotations

from collections.abc import Callable
from uuid import uuid4

from services.context.freshness import freshness_payload
from services.schemas.chat import ChatEntityRef, PageContext


CONTEXT_SCHEMA_VERSION = "page_context.v1"
MAX_CONTEXT_PAYLOAD_CHARS = 12000
MAX_SUMMARY_BULLETS = 8
MAX_TABLES = 3
MAX_TABLE_ROWS = 4
MAX_TABLE_COLUMNS = 6
MAX_SEMANTIC_BLOCKS = 12
MAX_ACTIONS = 40

PageContextBuilder = Callable[..., PageContext]


def normalize_text(value: object, limit: int = 240) -> str:
    text = " ".join(str(value or "").split())
    return text[:limit]


def infer_page_type(route: str | None, page_type_hint: str | None = None) -> str:
    if page_type_hint:
        return page_type_hint
    lowered = (route or "/").lower()
    if "strateg" in lowered:
        return "strategy_detail"
    if "backtest" in lowered or "simulation" in lowered:
        return "backtest_detail"
    if "optimization" in lowered:
        return "optimization_detail"
    if "risk" in lowered or "portfolio" in lowered:
        return "portfolio_risk"
    if "live" in lowered:
        return "live_trading"
    if "data" in lowered or "edge-lab" in lowered:
        return "data_workspace"
    if "operator" in lowered or "workflow" in lowered:
        return "operator_workflow"
    if lowered in {"/", "/dashboard"} or "dashboard" in lowered:
        return "dashboard"
    return "generic"


def compact_dom_snapshot(dom_snapshot: dict[str, object] | None) -> dict[str, object]:
    dom = dict(dom_snapshot or {})
    compact_tables = []
    for table in list(dom.get("tables") or [])[:MAX_TABLES]:
        if not isinstance(table, dict):
            continue
        compact_tables.append(
            {
                "headers": [normalize_text(value, 80) for value in list(table.get("headers") or [])[:MAX_TABLE_COLUMNS]],
                "rows": [
                    [normalize_text(cell, 80) for cell in list(row)[:MAX_TABLE_COLUMNS]]
                    for row in list(table.get("rows") or [])[:MAX_TABLE_ROWS]
                    if isinstance(row, list)
                ],
                "omitted_rows": max(0, len(list(table.get("rows") or [])) - MAX_TABLE_ROWS),
            }
        )

    compact_blocks = []
    for block in list(dom.get("semantic_blocks") or [])[:MAX_SEMANTIC_BLOCKS]:
        if not isinstance(block, dict):
            continue
        compact_blocks.append(
            {
                "id": normalize_text(block.get("id"), 80),
                "blockType": normalize_text(block.get("blockType"), 40),
                "title": normalize_text(block.get("title"), 120) or None,
                "summary": normalize_text(block.get("summary"), 400) or None,
                "keywords": [normalize_text(value, 50) for value in list(block.get("keywords") or [])[:12]],
                "metrics": list(block.get("metrics") or [])[:12],
                "headers": [normalize_text(value, 80) for value in list(block.get("headers") or [])[:MAX_TABLE_COLUMNS]],
            }
        )

    return {
        "title": normalize_text(dom.get("title"), 120) or None,
        "headings": [normalize_text(value, 120) for value in list(dom.get("headings") or [])[:8]],
        "text_excerpt": normalize_text(dom.get("text_excerpt"), 900) or None,
        "tables": compact_tables,
        "semantic_blocks": compact_blocks,
        "actionable_elements": [
            {
                "selector": normalize_text(item.get("selector"), 100),
                "label": normalize_text(item.get("label"), 120),
                "role": normalize_text(item.get("role"), 40),
            }
            for item in list(dom.get("actionable_elements") or [])[:MAX_ACTIONS]
            if isinstance(item, dict)
        ],
        "guardrails": {
            "raw_table_dump_blocked": True,
            "table_rows_per_table": MAX_TABLE_ROWS,
            "semantic_block_limit": MAX_SEMANTIC_BLOCKS,
        },
    }


def compact_page_intelligence(page_intelligence: dict[str, object] | None) -> dict[str, object]:
    intelligence = dict(page_intelligence or {})
    return {
        "pageIdentity": intelligence.get("pageIdentity") or {},
        "primaryEntity": intelligence.get("primaryEntity"),
        "selectedEntities": list(intelligence.get("selectedEntities") or [])[:12],
        "visibleMetrics": list(intelligence.get("visibleMetrics") or [])[:24],
        "visibleTables": [
            {
                **dict(table),
                "rows": list(dict(table).get("rows") or [])[:MAX_TABLE_ROWS],
            }
            for table in list(intelligence.get("visibleTables") or [])[:MAX_TABLES]
            if isinstance(table, dict)
        ],
        "visibleCharts": list(intelligence.get("visibleCharts") or [])[:8],
        "filters": intelligence.get("filters") or {},
        "userSelection": intelligence.get("userSelection") or {},
        "actionAffordances": list(intelligence.get("actionAffordances") or [])[:MAX_ACTIONS],
        "freshness": intelligence.get("freshness") or {},
    }


def entity_refs_from_state(
    *,
    session_id: int | None,
    symbol: str | None,
    timeframe: str | None,
    page_intelligence: dict[str, object] | None,
) -> list[ChatEntityRef]:
    entities: list[ChatEntityRef] = []
    if session_id is not None:
        entities.append(ChatEntityRef(type="session", id=str(session_id), label=f"Session {session_id}"))
    if symbol:
        entities.append(ChatEntityRef(type="symbol", id=symbol, label=symbol))
    if timeframe:
        entities.append(ChatEntityRef(type="timeframe", id=timeframe, label=timeframe))
    for item in list((page_intelligence or {}).get("selectedEntities") or [])[:8]:
        if isinstance(item, dict) and item.get("type") and item.get("id"):
            entities.append(
                ChatEntityRef(
                    type=str(item["type"]),
                    id=str(item["id"]),
                    label=str(item.get("label") or item["id"]),
                )
            )
    return entities


def build_compact_context(
    *,
    route: str | None,
    page_title: str | None,
    page_type: str,
    session_id: int | None = None,
    symbol: str | None = None,
    timeframe: str | None = None,
    dom_snapshot: dict[str, object] | None = None,
    page_intelligence: dict[str, object] | None = None,
    summary_bullets: list[str] | None = None,
    authority_source: str = "ui_observer",
) -> PageContext:
    compact_dom = compact_dom_snapshot(dom_snapshot)
    compact_intelligence = compact_page_intelligence(page_intelligence)
    identity = dict(compact_intelligence.get("pageIdentity") or {})
    title = page_title or normalize_text(identity.get("title"), 120) or normalize_text(compact_dom.get("title"), 120) or "Current HaruQuant page"
    bullets = [normalize_text(value, 180) for value in (summary_bullets or []) if normalize_text(value, 180)]
    if symbol:
        bullets.append(f"Symbol: {symbol}")
    if timeframe:
        bullets.append(f"Timeframe: {timeframe}")
    headings = compact_dom.get("headings")
    if isinstance(headings, list) and headings:
        bullets.append(f"Visible sections: {', '.join(str(value) for value in headings[:4])}")
    bullets = bullets[:MAX_SUMMARY_BULLETS]
    payload = {
        "schema_version": CONTEXT_SCHEMA_VERSION,
        "dom": compact_dom,
        "page_intelligence": compact_intelligence,
        "budget": {
            "max_payload_chars": MAX_CONTEXT_PAYLOAD_CHARS,
            "raw_table_dump_blocked": True,
        },
    }
    payload_text = str(payload)
    if len(payload_text) > MAX_CONTEXT_PAYLOAD_CHARS:
        payload["dom"] = {
            **compact_dom,
            "text_excerpt": normalize_text(compact_dom.get("text_excerpt"), 300),
            "tables": [],
            "semantic_blocks": list(compact_dom.get("semantic_blocks") or [])[:4],
            "guardrails": {
                "raw_table_dump_blocked": True,
                "truncated_for_budget": True,
            },
        }
    return PageContext(
        context_schema_version=CONTEXT_SCHEMA_VERSION,
        route=route or str(identity.get("route") or "/"),
        page_type=page_type,  # type: ignore[arg-type]
        page_title=title,
        entity_refs=entity_refs_from_state(
            session_id=session_id,
            symbol=symbol,
            timeframe=timeframe,
            page_intelligence=compact_intelligence,
        ),
        context_revision=f"ctx-{uuid4()}",
        freshness=freshness_payload(source=authority_source),
        authority={"source": authority_source, "trust_level": "system_state"},
        summary={"headline": title, "bullets": bullets},
        payload=payload,
    )

