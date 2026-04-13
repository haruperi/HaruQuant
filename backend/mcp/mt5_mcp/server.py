"""MT5 MCP server with wired read-only and mutating tools."""

from __future__ import annotations

from typing import Any

from backend.mcp.mt5_mcp.client import MT5Client

from .models import MCPToolSpec
from .tools import (
    MUTATING_TOOL_SPECS,
    READ_ONLY_TOOL_SPECS,
    LegacyMT5GatewayAdapter,
    MT5MutatingTools,
    MT5ReadOnlyTools,
)


class MT5MCPServer:
    """MT5 MCP server with tool specs and callable tool implementations."""

    def __init__(
        self,
        tools: tuple[MCPToolSpec, ...] = (),
        read_only_tools: MT5ReadOnlyTools | None = None,
        mutating_tools: MT5MutatingTools | None = None,
    ) -> None:
        self._tools = tools
        self._read_only = read_only_tools
        self._mutating = mutating_tools
        self._started = False

    @property
    def name(self) -> str:
        return "mt5_mcp"

    @property
    def started(self) -> bool:
        return self._started

    @property
    def read_only_tools(self) -> MT5ReadOnlyTools | None:
        return self._read_only

    @property
    def mutating_tools(self) -> MT5MutatingTools | None:
        return self._mutating

    def startup(self) -> "MT5MCPServer":
        self._started = True
        return self

    def list_tools(self) -> tuple[MCPToolSpec, ...]:
        return self._tools

    def call_tool(self, tool_name: str, arguments: dict[str, Any]) -> Any:
        """Execute a tool by name with given arguments.

        Routes to read-only or mutating tools based on tool name.
        Raises KeyError if tool not found.
        """
        # Try read-only tools first
        if self._read_only is not None:
            handler = getattr(self._read_only, tool_name, None)
            if handler is not None:
                return handler(**arguments)

        # Try mutating tools
        if self._mutating is not None:
            handler = getattr(self._mutating, tool_name, None)
            if handler is not None:
                return handler(**arguments)

        raise KeyError(f"Tool '{tool_name}' not found on MT5 MCP server")


def create_mt5_mcp_server() -> MT5MCPServer:
    """Create the MT5 MCP server with tool specs but no gateway (specs-only mode)."""
    return MT5MCPServer(tools=READ_ONLY_TOOL_SPECS + MUTATING_TOOL_SPECS)


def create_legacy_mt5_mcp_server(*, client: MT5Client | None = None) -> MT5MCPServer:
    """Create a governed MT5 MCP server backed by the legacy MT5 client.

    Wires both read-only and mutating tools through the LegacyMT5GatewayAdapter.
    """
    gateway = client or MT5Client()
    adapter = LegacyMT5GatewayAdapter(client=gateway)
    read_only = MT5ReadOnlyTools(gateway=adapter)
    mutating = MT5MutatingTools(gateway=adapter)
    return MT5MCPServer(
        tools=READ_ONLY_TOOL_SPECS + MUTATING_TOOL_SPECS,
        read_only_tools=read_only,
        mutating_tools=mutating,
    )


__all__ = [
    "MCPToolSpec",
    "MT5MCPServer",
    "create_legacy_mt5_mcp_server",
    "create_mt5_mcp_server",
]
