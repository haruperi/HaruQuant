"""Minimal backtest MCP server shell."""

from __future__ import annotations

from backend.mcp.mt5_mcp.models import MCPToolSpec

from .tools import BACKTEST_TOOL_SPECS

from backend.common.logger import logger

class BacktestMCPServer:
    """Thin MCP server shell for the legacy simulation boundary."""

    def __init__(self, tools: tuple[MCPToolSpec, ...] = ()) -> None:
        self._tools = tools
        self._started = False

    @property
    def name(self) -> str:
        return "backtest_mcp"

    @property
    def started(self) -> bool:
        return self._started

    def startup(self) -> "BacktestMCPServer":
        self._started = True
        return self

    def list_tools(self) -> tuple[MCPToolSpec, ...]:
        return self._tools


def create_backtest_mcp_server() -> BacktestMCPServer:
    """Create the governed backtest MCP wrapper over legacy simulation services."""

    return BacktestMCPServer(tools=BACKTEST_TOOL_SPECS)


__all__ = [
    "BacktestMCPServer",
    "create_backtest_mcp_server",
]
