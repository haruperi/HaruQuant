"""Governed MCP wrapper over the legacy simulation module."""

from .server import BacktestMCPServer, create_backtest_mcp_server
from .tools import (
    BACKTEST_TOOL_SPECS,
    BacktestCoordinatorView,
    BacktestRuntimeView,
)

__all__ = [
    "BACKTEST_TOOL_SPECS",
    "BacktestCoordinatorView",
    "BacktestMCPServer",
    "BacktestRuntimeView",
    "create_backtest_mcp_server",
]
