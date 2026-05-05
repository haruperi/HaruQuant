"""Firm-facing execution tool registry facade."""

from backend_retiring.mcp.mt5_mcp import MT5MCPServer, create_mt5_mcp_server

TOOL_DOMAIN = "execution"

__all__ = [
    "TOOL_DOMAIN",
    "MT5MCPServer",
    "create_mt5_mcp_server",
]
