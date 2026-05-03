"""Firm-facing backtest tool registry facade."""

from backend.mcp.backtest_mcp import (
    BACKTEST_TOOL_SPECS,
    BacktestCoordinatorView,
    BacktestMCPServer,
    BacktestRuntimeView,
    create_backtest_mcp_server,
)
from backend.tools.read_only.backtests import BacktestSummaryTool

TOOL_DOMAIN = "backtest"

__all__ = [
    "TOOL_DOMAIN",
    "BACKTEST_TOOL_SPECS",
    "BacktestCoordinatorView",
    "BacktestMCPServer",
    "BacktestSummaryTool",
    "BacktestRuntimeView",
    "create_backtest_mcp_server",
]
