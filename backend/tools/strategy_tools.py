"""Firm-facing strategy tool registry facade."""

from backend.tools.read_only.strategy import StrategyParametersTool

TOOL_DOMAIN = "strategy"
CANONICAL_SOURCES = (
    "services.strategy",
    "services.strategy.governance",
    "services.strategy.design",
    "backend.data.strategies",
)

__all__ = [
    "TOOL_DOMAIN",
    "CANONICAL_SOURCES",
    "StrategyParametersTool",
]
