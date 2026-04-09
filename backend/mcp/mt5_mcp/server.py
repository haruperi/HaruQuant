"""Minimal MT5 MCP server skeleton."""

from __future__ import annotations

from apps.mt5 import MT5Client

from .models import MCPToolSpec
from .tools import MUTATING_TOOL_SPECS, READ_ONLY_TOOL_SPECS


class MT5MCPServer:
    """Thin MCP server shell for the MT5 tool boundary."""

    def __init__(self, tools: tuple[MCPToolSpec, ...] = ()) -> None:
        self._tools = tools
        self._started = False

    @property
    def name(self) -> str:
        return "mt5_mcp"

    @property
    def started(self) -> bool:
        return self._started

    def startup(self) -> "MT5MCPServer":
        self._started = True
        return self

    def list_tools(self) -> tuple[MCPToolSpec, ...]:
        return self._tools


def create_mt5_mcp_server() -> MT5MCPServer:
    """Create the initial MT5 MCP server shell with no tools wired yet."""

    return MT5MCPServer(tools=READ_ONLY_TOOL_SPECS + MUTATING_TOOL_SPECS)


def create_legacy_mt5_mcp_server(*, client: MT5Client | None = None) -> MT5MCPServer:
    """Create a governed MT5 MCP server backed by the legacy MT5 client."""

    _ = client or MT5Client()
    return create_mt5_mcp_server()


__all__ = [
    "MCPToolSpec",
    "MT5MCPServer",
    "create_legacy_mt5_mcp_server",
    "create_mt5_mcp_server",
]
