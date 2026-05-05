"""Firm-facing data tool registry facade."""

from backend.tools.read_only.market import LatestCandleTool, SymbolStatsTool

TOOL_DOMAIN = "data"
CANONICAL_SOURCES = (
    "backend.tools.read_only.market",
    "backend.mcp.market_data_mcp",
    "services.data",
    "services.research.data",
)

__all__ = [
    "TOOL_DOMAIN",
    "CANONICAL_SOURCES",
    "LatestCandleTool",
    "SymbolStatsTool",
]
