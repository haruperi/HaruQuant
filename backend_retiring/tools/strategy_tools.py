"""Firm-facing strategy tool registry facade."""

from backend_retiring.tools.read_only.strategy import StrategyParametersTool

TOOL_DOMAIN = "strategy"
CANONICAL_SOURCES = (
    "services.strategy",
    "services.strategy.governance",
    "services.strategy.design",
    "data.strategies",
)

__all__ = [
    "TOOL_DOMAIN",
    "CANONICAL_SOURCES",
    "StrategyParametersTool",
]
