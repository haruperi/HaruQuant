"""Firm-facing strategy tool registry facade."""

from backend.tools.read_only.strategy import StrategyParametersTool

TOOL_DOMAIN = "strategy"
CANONICAL_SOURCES = (
    "backend.services.strategy",
    "backend.services.strategy_gov",
    "backend.services.strategy.design",
    "backend.data.strategies",
)

__all__ = [
    "TOOL_DOMAIN",
    "CANONICAL_SOURCES",
    "StrategyParametersTool",
]
