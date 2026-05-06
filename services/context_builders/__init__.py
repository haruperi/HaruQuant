"""Route-to-context registry for AI Chat page context."""

from __future__ import annotations

from services.context_builders.backtest_detail import build_backtest_detail_context
from services.context_builders.base import infer_page_type
from services.context_builders.dashboard import build_dashboard_context
from services.context_builders.data_workspace import build_data_workspace_context
from services.context_builders.generic import build_generic_context
from services.context_builders.live_trading import build_live_trading_context
from services.context_builders.operator_workflow import build_operator_workflow_context
from services.context_builders.optimization import build_optimization_context
from services.context_builders.portfolio_risk import build_portfolio_risk_context
from services.context_builders.strategy_detail import build_strategy_detail_context


ROUTE_CONTEXT_REGISTRY = {
    "dashboard": build_dashboard_context,
    "strategy_detail": build_strategy_detail_context,
    "backtest_detail": build_backtest_detail_context,
    "optimization_detail": build_optimization_context,
    "portfolio_risk": build_portfolio_risk_context,
    "live_trading": build_live_trading_context,
    "data_workspace": build_data_workspace_context,
    "operator_workflow": build_operator_workflow_context,
    "generic": build_generic_context,
}


def get_context_builder(route: str | None, page_type_hint: str | None = None):
    page_type = infer_page_type(route, page_type_hint)
    return ROUTE_CONTEXT_REGISTRY.get(page_type, build_generic_context), page_type


__all__ = ["ROUTE_CONTEXT_REGISTRY", "get_context_builder"]
