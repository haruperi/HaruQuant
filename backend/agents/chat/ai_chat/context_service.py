"""Page-context builders and assembler for route-aware AI chat context."""

from __future__ import annotations

from dataclasses import dataclass, replace
from datetime import datetime, timezone
import hashlib
import json
import re
from typing import Protocol
from uuid import uuid4

from backend.contracts.common import Originator
from backend.contracts.page_context_packet.model import (
    ContextAuthority,
    ContextFreshness,
    ContextSummary,
    EntityRef,
    PageContextPacket,
    PageContextPayload,
    PageType,
)
from backend.data.database.sqlite.database_operations import DatabaseManager
from services.execution.performance.snapshot_cache import HotSnapshotCache, SnapshotCacheEntry
from services.strategy.catalog import StrategyCatalogService

# Define TTLs for different page types
PAGE_CONTEXT_TTL: dict[PageType, int] = {
    "dashboard": 30,
    "strategy_detail": 300,
    "backtest_detail": 300,
    "optimization_detail": 300,
    "portfolio_risk": 60,
    "live_trading": 15,
    "data_workspace": 600,
    "operator_workflow": 60,
    "generic": 60,
}


@dataclass(frozen=True)
class RouteContextDescriptor:
    route_pattern: str
    page_type: PageType
    builder_name: str


DEFAULT_ROUTE_CONTEXT_REGISTRY: tuple[RouteContextDescriptor, ...] = (
    RouteContextDescriptor("/dashboard", "dashboard", "DashboardContextBuilder"),
    RouteContextDescriptor("/strategies/", "strategy_detail", "StrategyDetailContextBuilder"),
    RouteContextDescriptor("/backtests/", "backtest_detail", "BacktestDetailContextBuilder"),
    RouteContextDescriptor("/performance", "backtest_detail", "BacktestDetailContextBuilder"),
    RouteContextDescriptor("/optimization", "optimization_detail", "OptimizationContextBuilder"),
    RouteContextDescriptor("/portfolio", "portfolio_risk", "PortfolioRiskContextBuilder"),
    RouteContextDescriptor("/risk", "portfolio_risk", "PortfolioRiskContextBuilder"),
    RouteContextDescriptor("/live", "live_trading", "LiveTradingContextBuilder"),
    RouteContextDescriptor("/edge", "data_workspace", "DataWorkspaceContextBuilder"),
    RouteContextDescriptor("/market", "data_workspace", "DataWorkspaceContextBuilder"),
    RouteContextDescriptor("/data", "data_workspace", "DataWorkspaceContextBuilder"),
    RouteContextDescriptor("/operator", "operator_workflow", "OperatorWorkflowContextBuilder"),
)


@dataclass(frozen=True)
class BuiltContext:
    page_type: PageType
    page_title: str | None
    entity_refs: list[EntityRef]
    summary: ContextSummary
    payload: dict[str, object]
    trust_level: str
    builder_name: str


class ContextBuilder(Protocol):
    page_type: PageType
    builder_name: str

    def build(
        self,
        *,
        route: str,
        user_id: int,
        page_title: str | None = None,
        page_state: dict[str, object] | None = None,
    ) -> BuiltContext:
        ...


class BaseContextBuilder:
    page_type: PageType = "generic"
    builder_name = "GenericContextBuilder"

    def __init__(self, db_manager: DatabaseManager, strategy_catalog: StrategyCatalogService) -> None:
        self.db = db_manager
        self.strategy_catalog = strategy_catalog

    def build(
        self,
        *,
        route: str,
        user_id: int,
        page_title: str | None = None,
        page_state: dict[str, object] | None = None,
    ) -> BuiltContext:
        page_state = page_state or {}
        dom = page_state.get("dom") if isinstance(page_state.get("dom"), dict) else {}
        headings = dom.get("headings") if isinstance(dom.get("headings"), list) else []
        title = str(dom.get("title") or page_title or "Current page").strip()
        excerpt = str(dom.get("text_excerpt") or "").strip()
        tables = dom.get("tables") if isinstance(dom.get("tables"), list) else []
        semantic_blocks = dom.get("semantic_blocks") if isinstance(dom.get("semantic_blocks"), list) else []
        headline = "This page does not have a specialized chat context yet"
        bullets = [
            "No dashboard, strategy, backtest, optimization, portfolio, or live session was detected from the current route.",
            "Open a more specific HaruQuant workspace page for grounded metrics and entity-aware answers.",
        ]
        payload: dict[str, object] = {"route": route}
        if title or headings or excerpt:
            headline = f"Captured current UI context for {title}"
            bullets = []
            if headings:
                bullets.append(f"visible_headings={', '.join(str(item) for item in headings[:4])}")
            if tables:
                first_table = tables[0] if isinstance(tables[0], dict) else {}
                headers = first_table.get("headers") if isinstance(first_table.get("headers"), list) else []
                rows = first_table.get("rows") if isinstance(first_table.get("rows"), list) else []
                if headers:
                    bullets.append(f"table_headers={', '.join(str(item) for item in headers[:4])}")
                if rows:
                    first_row = rows[0] if isinstance(rows[0], list) else []
                    if first_row:
                        bullets.append(f"first_row={', '.join(str(item) for item in first_row[:4])}")
            if semantic_blocks:
                bullets.append(f"semantic_blocks={len(semantic_blocks)}")
            if excerpt:
                bullets.append(f"visible_text_excerpt={excerpt[:180]}")
            bullets.append(f"route={route}")
            payload["dom"] = dom
        return BuiltContext(
            page_type=self.page_type,
            page_title=page_title or title,
            entity_refs=[],
            summary=ContextSummary(
                headline=headline,
                bullets=bullets[:5],
            ),
            payload=payload,
            trust_level="fallback",
            builder_name=self.builder_name,
        )

    @staticmethod
    def _extract_first_int(route: str) -> int | None:
        match = re.search(r"/(\d+)(?:/|$)", route)
        return int(match.group(1)) if match else None


class DashboardContextBuilder(BaseContextBuilder):
    page_type = "dashboard"
    builder_name = "DashboardContextBuilder"

    def build(
        self,
        *,
        route: str,
        user_id: int,
        page_title: str | None = None,
        page_state: dict[str, object] | None = None,
    ) -> BuiltContext:
        sessions = self.db.get_user_live_sessions(user_id) or []
        active_sessions = [session for session in sessions if str(session.get("status", "")).lower() in {"running", "paused"}]
        active_strategy_count = 0
        session_refs: list[EntityRef] = []
        for session in active_sessions:
            session_id = int(session["session_id"])
            session_refs.append(
                EntityRef(
                    type="live_session",
                    id=str(session_id),
                    label=str(session.get("session_name") or f"Session {session_id}"),
                )
            )
            active_strategy_count += len(self.db.get_session_strategies(session_id) or [])

        return BuiltContext(
            page_type=self.page_type,
            page_title=page_title or "Dashboard",
            entity_refs=session_refs[:4],
            summary=ContextSummary(
                headline=f"Dashboard monitoring {active_strategy_count} active strategies",
                bullets=[
                    f"active_sessions={len(active_sessions)}",
                    f"configured_sessions={len(sessions)}",
                    f"route={route}",
                ],
            ),
            payload={
                "active_session_count": len(active_sessions),
                "configured_session_count": len(sessions),
                "active_strategy_count": active_strategy_count,
            },
            trust_level="system_state",
            builder_name=self.builder_name,
        )


class StrategyDetailContextBuilder(BaseContextBuilder):
    page_type = "strategy_detail"
    builder_name = "StrategyDetailContextBuilder"

    def build(
        self,
        *,
        route: str,
        user_id: int,
        page_title: str | None = None,
        page_state: dict[str, object] | None = None,
    ) -> BuiltContext:
        strategy_id = self._extract_first_int(route)
        if strategy_id is None:
            return super().build(route=route, user_id=user_id, page_title=page_title, page_state=page_state)
        try:
            strategy = self.strategy_catalog.get_strategy(strategy_id, user_id=user_id)
        except Exception:
            return super().build(route=route, user_id=user_id, page_title=page_title, page_state=page_state)

        bullets = [
            f"status={strategy.get('status') or 'unknown'}",
            f"lifecycle={strategy.get('lifecycle_state') or 'unknown'}",
            f"active_version={strategy.get('active_version') or 'n/a'}",
        ]
        if strategy.get("category"):
            bullets.append(f"category={strategy['category']}")

        return BuiltContext(
            page_type=self.page_type,
            page_title=page_title or str(strategy.get("name") or f"Strategy {strategy_id}"),
            entity_refs=[
                EntityRef(
                    type="strategy",
                    id=str(strategy_id),
                    label=str(strategy.get("name") or f"Strategy {strategy_id}"),
                )
            ],
            summary=ContextSummary(
                headline=f"Strategy detail for {strategy.get('name') or f'Strategy {strategy_id}'}",
                bullets=bullets[:5],
            ),
            payload={
                "strategy_id": strategy_id,
                "name": strategy.get("name"),
                "status": strategy.get("status"),
                "category": strategy.get("category"),
                "lifecycle_state": strategy.get("lifecycle_state"),
                "active_version": strategy.get("active_version"),
                "strategy_family": strategy.get("strategy_family"),
            },
            trust_level="system_state",
            builder_name=self.builder_name,
        )


class BacktestDetailContextBuilder(BaseContextBuilder):
    page_type = "backtest_detail"
    builder_name = "BacktestDetailContextBuilder"

    def build(
        self,
        *,
        route: str,
        user_id: int,
        page_title: str | None = None,
        page_state: dict[str, object] | None = None,
    ) -> BuiltContext:
        backtest_id = self._extract_first_int(route)
        if backtest_id is None:
            return super().build(route=route, user_id=user_id, page_title=page_title, page_state=page_state)
        run = self.db.get_backtest_run(backtest_id)
        if not run:
            return super().build(route=route, user_id=user_id, page_title=page_title, page_state=page_state)

        return BuiltContext(
            page_type=self.page_type,
            page_title=page_title or f"Backtest {backtest_id}",
            entity_refs=[
                EntityRef(type="backtest", id=str(backtest_id), label=f"Backtest {backtest_id}")
            ],
            summary=ContextSummary(
                headline=f"Backtest {backtest_id} is {run.get('status') or 'unknown'}",
                bullets=[
                    f"strategy_id={run.get('strategy_id') or 'n/a'}",
                    f"total_trades={run.get('total_trades') or 0}",
                    f"created_at={run.get('created_at') or 'unknown'}",
                ],
            ),
            payload={
                "backtest_id": backtest_id,
                "status": run.get("status"),
                "strategy_id": run.get("strategy_id"),
                "strategy_version_id": run.get("strategy_version_id"),
                "total_trades": run.get("total_trades"),
                "symbols": run.get("symbols"),
                "timeframes": run.get("timeframes"),
            },
            trust_level="system_state",
            builder_name=self.builder_name,
        )


class OptimizationContextBuilder(BaseContextBuilder):
    page_type = "optimization_detail"
    builder_name = "OptimizationContextBuilder"

    def build(
        self,
        *,
        route: str,
        user_id: int,
        page_title: str | None = None,
        page_state: dict[str, object] | None = None,
    ) -> BuiltContext:
        optimization_id = self._extract_first_int(route)
        if optimization_id is None:
            return super().build(route=route, user_id=user_id, page_title=page_title, page_state=page_state)
        run = self.db.get_optimization_run(optimization_id)
        if not run:
            return super().build(route=route, user_id=user_id, page_title=page_title, page_state=page_state)
        return BuiltContext(
            page_type=self.page_type,
            page_title=page_title or f"Optimization {optimization_id}",
            entity_refs=[
                EntityRef(type="optimization", id=str(optimization_id), label=f"Optimization {optimization_id}")
            ],
            summary=ContextSummary(
                headline=f"Optimization {optimization_id} is {run.get('status') or 'unknown'}",
                bullets=[
                    f"method={run.get('method') or run.get('optimization_type') or 'unknown'}",
                    f"strategy_id={run.get('strategy_id') or 'n/a'}",
                    f"best_score={run.get('best_score') or 'n/a'}",
                ],
            ),
            payload={
                "optimization_id": optimization_id,
                "status": run.get("status"),
                "strategy_id": run.get("strategy_id"),
                "method": run.get("method") or run.get("optimization_type"),
                "best_score": run.get("best_score"),
                "best_parameters": run.get("best_parameters"),
            },
            trust_level="system_state",
            builder_name=self.builder_name,
        )


class PortfolioRiskContextBuilder(BaseContextBuilder):
    page_type = "portfolio_risk"
    builder_name = "PortfolioRiskContextBuilder"

    def build(
        self,
        *,
        route: str,
        user_id: int,
        page_title: str | None = None,
        page_state: dict[str, object] | None = None,
    ) -> BuiltContext:
        sessions = self.db.get_user_live_sessions(user_id) or []
        running_sessions = [session for session in sessions if str(session.get("status", "")).lower() == "running"]
        return BuiltContext(
            page_type=self.page_type,
            page_title=page_title or "Portfolio and Risk",
            entity_refs=[],
            summary=ContextSummary(
                headline=f"Portfolio context spans {len(running_sessions)} running sessions",
                bullets=[
                    f"total_sessions={len(sessions)}",
                    "risk snapshot integration pending deeper engine wiring",
                    f"route={route}",
                ],
            ),
            payload={
                "running_session_count": len(running_sessions),
                "session_ids": [session.get("session_id") for session in running_sessions[:5]],
            },
            trust_level="derived_summary",
            builder_name=self.builder_name,
        )


class LiveTradingContextBuilder(BaseContextBuilder):
    page_type = "live_trading"
    builder_name = "LiveTradingContextBuilder"

    def build(
        self,
        *,
        route: str,
        user_id: int,
        page_title: str | None = None,
        page_state: dict[str, object] | None = None,
    ) -> BuiltContext:
        page_state = page_state or {}
        session_id = page_state.get("session_id")
        if not isinstance(session_id, int):
            session_id = self._extract_first_int(route)
        symbol = str(page_state.get("symbol") or "").upper() or None
        timeframe = str(page_state.get("timeframe") or "").upper() or None
        if session_id is not None:
            session = self.db.get_live_session(session_id)
            if session:
                strategies = self.db.get_session_strategies(session_id) or []
                entity_refs = [
                    EntityRef(
                        type="live_session",
                        id=str(session_id),
                        label=str(session.get("session_name") or f"Live Session {session_id}"),
                    )
                ]
                bullets = [
                    f"broker={session.get('broker_name') or 'n/a'}",
                    f"strategies={len(strategies)}",
                    f"mode={session.get('trading_mode') or 'n/a'}",
                ]
                if symbol:
                    entity_refs.append(EntityRef(type="symbol", id=symbol, label=symbol))
                    bullets.append(f"chart_symbol={symbol}")
                if timeframe:
                    bullets.append(f"chart_timeframe={timeframe}")
                return BuiltContext(
                    page_type=self.page_type,
                    page_title=page_title or str(session.get("session_name") or f"Live Session {session_id}"),
                    entity_refs=entity_refs,
                    summary=ContextSummary(
                        headline=(
                            f"Live session {session.get('session_name') or session_id} is {session.get('status') or 'unknown'}"
                            if not (symbol and timeframe)
                            else f"Live session {session.get('session_name') or session_id} is {session.get('status') or 'unknown'} with chart focus on {symbol} {timeframe}"
                        ),
                        bullets=bullets[:6],
                    ),
                    payload={
                        "session_id": session_id,
                        "status": session.get("status"),
                        "broker_name": session.get("broker_name"),
                        "trading_mode": session.get("trading_mode"),
                        "strategy_count": len(strategies),
                        "symbol": symbol,
                        "timeframe": timeframe,
                    },
                    trust_level="system_state",
                    builder_name=self.builder_name,
                )

        sessions = self.db.get_user_live_sessions(user_id) or []
        bullets = [
            f"running={sum(1 for session in sessions if str(session.get('status', '')).lower() == 'running')}",
            f"paused={sum(1 for session in sessions if str(session.get('status', '')).lower() == 'paused')}",
            f"route={route}",
        ]
        payload: dict[str, object] = {"session_count": len(sessions)}
        headline = f"Live trading overview across {len(sessions)} sessions"
        if symbol:
            payload["symbol"] = symbol
            bullets.append(f"chart_symbol={symbol}")
        if timeframe:
            payload["timeframe"] = timeframe
            bullets.append(f"chart_timeframe={timeframe}")
        if symbol and timeframe:
            headline = f"Live trading overview with chart focus on {symbol} {timeframe}"
        return BuiltContext(
            page_type=self.page_type,
            page_title=page_title or "Live Trading",
            entity_refs=[],
            summary=ContextSummary(
                headline=headline,
                bullets=bullets[:6],
            ),
            payload=payload,
            trust_level="derived_summary",
            builder_name=self.builder_name,
        )


class DataWorkspaceContextBuilder(BaseContextBuilder):
    page_type = "data_workspace"
    builder_name = "DataWorkspaceContextBuilder"

    def build(
        self,
        *,
        route: str,
        user_id: int,
        page_title: str | None = None,
        page_state: dict[str, object] | None = None,
    ) -> BuiltContext:
        return BuiltContext(
            page_type=self.page_type,
            page_title=page_title or "Data Workspace",
            entity_refs=[],
            summary=ContextSummary(
                headline="Data workspace context active",
                bullets=[
                    "data-source level context remains compact in chat packets",
                    f"route={route}",
                ],
            ),
            payload={"workspace_route": route},
            trust_level="derived_summary",
            builder_name=self.builder_name,
        )


class OperatorWorkflowContextBuilder(BaseContextBuilder):
    page_type = "operator_workflow"
    builder_name = "OperatorWorkflowContextBuilder"

    def build(
        self,
        *,
        route: str,
        user_id: int,
        page_title: str | None = None,
        page_state: dict[str, object] | None = None,
    ) -> BuiltContext:
        return BuiltContext(
            page_type=self.page_type,
            page_title=page_title or "Operator Workflow",
            entity_refs=[],
            summary=ContextSummary(
                headline="Operator workflow context active",
                bullets=[
                    "operator queue and workflow status can be discussed safely",
                    f"route={route}",
                ],
            ),
            payload={"operator_route": route},
            trust_level="derived_summary",
            builder_name=self.builder_name,
        )


class GenericContextBuilder(BaseContextBuilder):
    page_type = "generic"
    builder_name = "GenericContextBuilder"


class PageContextAssembler:
    """Build route-aware page context packets for the AI chatbot."""

    def __init__(
        self,
        db_manager: DatabaseManager | None = None,
        strategy_catalog: StrategyCatalogService | None = None,
        registry: tuple[RouteContextDescriptor, ...] | None = None,
        cache: HotSnapshotCache[BuiltContext] | None = None,
    ) -> None:
        self.db_manager = db_manager or DatabaseManager()
        self.strategy_catalog = strategy_catalog or StrategyCatalogService(db_manager=self.db_manager)
        self._registry = registry or DEFAULT_ROUTE_CONTEXT_REGISTRY
        self._cache = cache or HotSnapshotCache()
        self._builders: dict[PageType, ContextBuilder] = {
            "dashboard": DashboardContextBuilder(self.db_manager, self.strategy_catalog),
            "strategy_detail": StrategyDetailContextBuilder(self.db_manager, self.strategy_catalog),
            "backtest_detail": BacktestDetailContextBuilder(self.db_manager, self.strategy_catalog),
            "optimization_detail": OptimizationContextBuilder(self.db_manager, self.strategy_catalog),
            "portfolio_risk": PortfolioRiskContextBuilder(self.db_manager, self.strategy_catalog),
            "live_trading": LiveTradingContextBuilder(self.db_manager, self.strategy_catalog),
            "data_workspace": DataWorkspaceContextBuilder(self.db_manager, self.strategy_catalog),
            "operator_workflow": OperatorWorkflowContextBuilder(self.db_manager, self.strategy_catalog),
            "generic": GenericContextBuilder(self.db_manager, self.strategy_catalog),
        }

    @property
    def registry(self) -> tuple[RouteContextDescriptor, ...]:
        return self._registry

    def resolve_page_type(self, route: str) -> PageType:
        normalized = route.lower()
        if normalized == "/":
            return "dashboard"
        for descriptor in self._registry:
            if descriptor.route_pattern in normalized:
                return descriptor.page_type
        return "generic"

    @staticmethod
    def _resolve_page_type_hint(page_state: dict[str, object]) -> PageType | None:
        hint = page_state.get("page_type_hint")
        if not isinstance(hint, str):
            return None
        normalized = hint.strip()
        if normalized in {
            "dashboard",
            "strategy_detail",
            "backtest_detail",
            "optimization_detail",
            "portfolio_risk",
            "live_trading",
            "data_workspace",
            "operator_workflow",
            "generic",
        }:
            return normalized  # type: ignore[return-value]
        return None

    def builder_name_for_route(self, route: str) -> str:
        return self._builders[self.resolve_page_type(route)].builder_name

    def assemble_generic_context(
        self,
        *,
        route: str,
        workflow_id: str,
        correlation_id: str,
        causation_id: str,
        page_title: str | None = None,
        entity_refs: list[EntityRef] | None = None,
    ) -> PageContextPacket:
        now = datetime.now(timezone.utc)
        page_type = self.resolve_page_type(route)
        builder_name = self.builder_name_for_route(route)
        return PageContextPacket(
            workflow_id=workflow_id,
            correlation_id=correlation_id,
            causation_id=causation_id,
            originator=Originator(type="service", id="context_service"),
            environment="paper",
            operating_mode="MODE-001",
            payload=PageContextPayload(
                route=route,
                page_type=page_type,
                page_title=page_title,
                entity_refs=entity_refs or [],
                context_revision=f"ctx_{now.strftime('%Y%m%d%H%M%S')}",
                generated_at=now,
                freshness=ContextFreshness(observed_at=now, staleness_seconds=0),
                authority=ContextAuthority(
                    source=f"backend.agents.chat.ai_chat.context_service:{builder_name}",
                    trust_level="fallback" if page_type == "generic" else "derived_summary",
                ),
                summary=ContextSummary(
                    headline=(
                        "Generic chat context applied"
                        if page_type == "generic"
                        else f"{page_type.replace('_', ' ').title()} context applied"
                    ),
                    bullets=[f"builder={builder_name}", f"route={route}"],
                ),
                payload={},
            ),
        )

    def assemble_context(
        self,
        *,
        route: str,
        user_id: int,
        page_title: str | None = None,
        page_state: dict[str, object] | None = None,
    ) -> PageContextPacket:
        now = datetime.now(timezone.utc)
        page_state = page_state or {}
        page_type = self._resolve_page_type_hint(page_state) or self.resolve_page_type(route)
        
        # Try cache first
        page_state_key = hashlib.sha1(
            json.dumps(page_state, sort_keys=True, default=str).encode("utf-8")
        ).hexdigest()[:12]
        cache_key = f"ctx:{user_id}:{route}:{page_title or ''}:{page_state_key}"
        cached = self._cache.get(cache_key)
        if cached:
            built = cached.snapshot
        else:
            builder = self._builders[page_type]
            built = builder.build(route=route, user_id=user_id, page_title=page_title, page_state=page_state)
            built = self._augment_with_page_intelligence(built=built, page_state=page_state)
            # Store in cache
            ttl = PAGE_CONTEXT_TTL.get(page_type, 60)
            self._cache.put(
                SnapshotCacheEntry(
                    key=cache_key,
                    snapshot=built,
                    observed_at=now,
                    max_age_seconds=ttl,
                )
            )

        return PageContextPacket(
            workflow_id=f"context_{uuid4().hex}",
            correlation_id=f"corr_{uuid4().hex}",
            causation_id=f"ctxreq_{uuid4().hex}",
            originator=Originator(type="service", id="context_service"),
            environment="paper",
            operating_mode="MODE-001",
            payload=PageContextPayload(
                route=route,
                page_type=built.page_type,
                page_title=built.page_title,
                entity_refs=built.entity_refs,
                context_revision=f"ctx_{now.strftime('%Y%m%d%H%M%S')}_{uuid4().hex[:8]}",
                generated_at=now,
                freshness=ContextFreshness(observed_at=now, staleness_seconds=0),
                authority=ContextAuthority(
                    source=f"backend.agents.chat.ai_chat.context_service:{built.builder_name}",
                    trust_level=built.trust_level,
                ),
                summary=built.summary,
                payload=built.payload,
            ),
        )

    @staticmethod
    def _augment_with_page_intelligence(*, built: BuiltContext, page_state: dict[str, object]) -> BuiltContext:
        page_intelligence = page_state.get("page_intelligence")
        if not isinstance(page_intelligence, dict):
            return built

        payload = dict(built.payload)
        payload["page_intelligence"] = page_intelligence

        summary = built.summary
        bullets = list(summary.bullets)
        metric_count = _safe_len(page_intelligence.get("visibleMetrics"))
        table_count = _safe_len(page_intelligence.get("visibleTables"))
        chart_count = _safe_len(page_intelligence.get("visibleCharts"))
        action_count = _safe_len(page_intelligence.get("actionAffordances"))
        intelligence_bullets = [
            f"registered_metrics={metric_count}" if metric_count else "",
            f"registered_tables={table_count}" if table_count else "",
            f"registered_charts={chart_count}" if chart_count else "",
            f"registered_actions={action_count}" if action_count else "",
        ]
        bullets.extend(item for item in intelligence_bullets if item)

        return replace(
            built,
            summary=ContextSummary(
                headline=summary.headline,
                bullets=bullets[:8],
            ),
            payload=payload,
            trust_level="system_state" if built.trust_level == "fallback" else built.trust_level,
        )


def _safe_len(value: object) -> int:
    return len(value) if isinstance(value, list) else 0


__all__ = [
    "DEFAULT_ROUTE_CONTEXT_REGISTRY",
    "PageContextAssembler",
    "RouteContextDescriptor",
]
