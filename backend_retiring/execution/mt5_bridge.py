"""MT5 execution bridge facade over the governed MCP boundary."""

from backend_retiring.mcp.mt5_mcp import *  # noqa: F403
from haruquant.execution import *

MT5_BRIDGE_FACADE = "backend_retiring.execution.mt5_bridge"
