"""Minimal SQL MCP server shell."""

from __future__ import annotations

from backend.mcp.mt5_mcp.models import MCPToolSpec

from .tools import SQL_TOOL_SPECS


class SQLMCPServer:
    """Thin MCP server shell for governed SQL access."""

    def __init__(self, tools: tuple[MCPToolSpec, ...] = ()) -> None:
        self._tools = tools
        self._started = False

    @property
    def name(self) -> str:
        return "sql_mcp"

    @property
    def started(self) -> bool:
        return self._started

    def startup(self) -> "SQLMCPServer":
        self._started = True
        return self

    def list_tools(self) -> tuple[MCPToolSpec, ...]:
        return self._tools


def create_sql_mcp_server() -> SQLMCPServer:
    """Create the governed SQL MCP wrapper."""

    return SQLMCPServer(tools=SQL_TOOL_SPECS)


__all__ = [
    "SQLMCPServer",
    "create_sql_mcp_server",
]
