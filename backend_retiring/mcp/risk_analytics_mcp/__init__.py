"""Governed MCP wrapper over the legacy risk analytics module."""

from .server import RiskAnalyticsMCPServer, create_risk_analytics_mcp_server
from .tools import RISK_ANALYTICS_TOOL_SPECS, RiskAnalyticsTools

__all__ = [
    "RISK_ANALYTICS_TOOL_SPECS",
    "RiskAnalyticsMCPServer",
    "RiskAnalyticsTools",
    "create_risk_analytics_mcp_server",
]
