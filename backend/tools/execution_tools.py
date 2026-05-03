"""Firm-facing execution tool registry facade."""

from backend.mcp.mt5_mcp import MT5MCPServer, create_mt5_mcp_server
from backend.services.execution import *  # noqa: F403

TOOL_DOMAIN = "execution"

__all__ = [
    "TOOL_DOMAIN",
    "MT5MCPServer",
    "create_mt5_mcp_server",
]
