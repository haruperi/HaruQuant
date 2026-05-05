"""Firm-facing data tool registry facade."""

from backend_retiring.tools.read_only.market import LatestCandleTool, SymbolStatsTool

TOOL_DOMAIN = "data"
CANONICAL_SOURCES = (
    "backend_retiring.tools.read_only.market",
    "haruquant.data",
    "services.research.data",
)

__all__ = [
    "TOOL_DOMAIN",
    "CANONICAL_SOURCES",
    "LatestCandleTool",
    "SymbolStatsTool",
]
