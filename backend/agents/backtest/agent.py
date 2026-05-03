"""Backtest Department facade over the governed backtest MCP wrapper."""

from backend.mcp.backtest_mcp import (
    BACKTEST_TOOL_SPECS,
    BacktestCoordinatorView,
    BacktestMCPServer,
    BacktestRuntimeView,
    create_backtest_mcp_server,
)

BACKTEST_DEPARTMENT = "backtest"

__all__ = [
    "BACKTEST_DEPARTMENT",
    "BACKTEST_TOOL_SPECS",
    "BacktestCoordinatorView",
    "BacktestMCPServer",
    "BacktestRuntimeView",
    "create_backtest_mcp_server",
]
