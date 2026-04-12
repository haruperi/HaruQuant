"""Minimal market data MCP server shell."""

from __future__ import annotations

from backend.mcp.mt5_mcp.models import MCPToolSpec

from .tools import MARKET_DATA_TOOL_SPECS


class MarketDataMCPServer:
    """Thin MCP server shell for external market-data providers."""

    def __init__(self, tools: tuple[MCPToolSpec, ...] = ()) -> None:
        self._tools = tools
        self._started = False

    @property
    def name(self) -> str:
        return "market_data_mcp"

    @property
    def started(self) -> bool:
        return self._started

    def startup(self) -> "MarketDataMCPServer":
        self._started = True
        return self

    def list_tools(self) -> tuple[MCPToolSpec, ...]:
        return self._tools


def create_market_data_mcp_server() -> MarketDataMCPServer:
    """Create the governed market-data MCP wrapper."""

    return MarketDataMCPServer(tools=MARKET_DATA_TOOL_SPECS)


__all__ = [
    "MarketDataMCPServer",
    "create_market_data_mcp_server",
]
