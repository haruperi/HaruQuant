"""Minimal risk analytics MCP server shell."""

from __future__ import annotations

from backend.mcp.mt5_mcp.models import MCPToolSpec

from .tools import RISK_ANALYTICS_TOOL_SPECS

from services.utils.logger import logger

class RiskAnalyticsMCPServer:
    """Thin MCP server shell for the legacy risk analytics boundary."""

    def __init__(self, tools: tuple[MCPToolSpec, ...] = ()) -> None:
        self._tools = tools
        self._started = False

    @property
    def name(self) -> str:
        return "risk_analytics_mcp"

    @property
    def started(self) -> bool:
        return self._started

    def startup(self) -> "RiskAnalyticsMCPServer":
        self._started = True
        return self

    def list_tools(self) -> tuple[MCPToolSpec, ...]:
        return self._tools


def create_risk_analytics_mcp_server() -> RiskAnalyticsMCPServer:
    """Create the governed risk analytics MCP wrapper."""

    return RiskAnalyticsMCPServer(tools=RISK_ANALYTICS_TOOL_SPECS)


__all__ = [
    "RiskAnalyticsMCPServer",
    "create_risk_analytics_mcp_server",
]
