"""Phase 0 route-context registry and generic page-context assembler."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone

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


@dataclass(frozen=True)
class RouteContextDescriptor:
    route_pattern: str
    page_type: PageType
    builder_name: str


DEFAULT_ROUTE_CONTEXT_REGISTRY: tuple[RouteContextDescriptor, ...] = (
    RouteContextDescriptor("/dashboard", "dashboard", "DashboardContextBuilder"),
    RouteContextDescriptor("/strategies/", "strategy_detail", "StrategyDetailContextBuilder"),
    RouteContextDescriptor("/backtests/", "backtest_detail", "BacktestDetailContextBuilder"),
    RouteContextDescriptor("/optimization", "optimization_detail", "OptimizationContextBuilder"),
    RouteContextDescriptor("/portfolio", "portfolio_risk", "PortfolioRiskContextBuilder"),
    RouteContextDescriptor("/live", "live_trading", "LiveTradingContextBuilder"),
    RouteContextDescriptor("/data", "data_workspace", "DataWorkspaceContextBuilder"),
    RouteContextDescriptor("/operator/workflows", "operator_workflow", "OperatorWorkflowContextBuilder"),
)


class PageContextAssembler:
    """Build generic phase-0 page context packets from frozen route contracts."""

    def __init__(self, registry: tuple[RouteContextDescriptor, ...] | None = None) -> None:
        self._registry = registry or DEFAULT_ROUTE_CONTEXT_REGISTRY

    @property
    def registry(self) -> tuple[RouteContextDescriptor, ...]:
        return self._registry

    def resolve_page_type(self, route: str) -> PageType:
        normalized = route.lower()
        for descriptor in self._registry:
            if descriptor.route_pattern in normalized:
                return descriptor.page_type
        return "generic"

    def builder_name_for_route(self, route: str) -> str:
        normalized = route.lower()
        for descriptor in self._registry:
            if descriptor.route_pattern in normalized:
                return descriptor.builder_name
        return "GenericContextBuilder"

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
                freshness=ContextFreshness(
                    observed_at=now,
                    staleness_seconds=0,
                ),
                authority=ContextAuthority(
                    source=f"backend.services.ai_chat.context_service:{builder_name}",
                    trust_level="fallback" if page_type == "generic" else "derived_summary",
                ),
                summary=ContextSummary(
                    headline=(
                        "Generic chat context applied"
                        if page_type == "generic"
                        else f"{page_type.replace('_', ' ').title()} context applied"
                    ),
                    bullets=[
                        f"builder={builder_name}",
                        f"route={route}",
                    ],
                ),
                payload={},
            ),
        )


__all__ = [
    "DEFAULT_ROUTE_CONTEXT_REGISTRY",
    "PageContextAssembler",
    "RouteContextDescriptor",
]
