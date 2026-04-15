"""Minimal optimization MCP server shell."""

from __future__ import annotations

from backend.mcp.mt5_mcp.models import MCPToolSpec

from .tools import OPTIMIZATION_TOOL_SPECS

from backend.common.logger import logger

class OptimizationMCPServer:
    """Thin MCP server shell for the legacy optimization boundary."""

    def __init__(self, tools: tuple[MCPToolSpec, ...] = ()) -> None:
        self._tools = tools
        self._started = False

    @property
    def name(self) -> str:
        return "optimization_mcp"

    @property
    def started(self) -> bool:
        return self._started

    def startup(self) -> "OptimizationMCPServer":
        self._started = True
        return self

    def list_tools(self) -> tuple[MCPToolSpec, ...]:
        return self._tools


def create_optimization_mcp_server() -> OptimizationMCPServer:
    """Create the governed optimization MCP wrapper."""

    return OptimizationMCPServer(tools=OPTIMIZATION_TOOL_SPECS)


__all__ = [
    "OptimizationMCPServer",
    "create_optimization_mcp_server",
]
