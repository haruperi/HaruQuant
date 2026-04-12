"""MT5 MCP boundary exports."""

from .auth import MT5ToolAuthorizationError, MT5ToolAuthorizer
from .client import ConnectionState, MT5Api, MT5Client, get_mt5_api
from .models import MCPToolSpec
from .normalization import normalize_broker_response
from .server import MT5MCPServer, create_legacy_mt5_mcp_server, create_mt5_mcp_server
from .tools import (
    LegacyMT5GatewayAdapter,
    MT5MutatingTools,
    MT5ReadOnlyTools,
    reject_stale_execution_inputs,
)
from .util import MT5Utils, TicksGen, timeframe_seconds

__all__ = [
    "ConnectionState",
    "MCPToolSpec",
    "LegacyMT5GatewayAdapter",
    "MT5Api",
    "MT5Client",
    "MT5MutatingTools",
    "MT5MCPServer",
    "MT5ReadOnlyTools",
    "MT5ToolAuthorizationError",
    "MT5ToolAuthorizer",
    "MT5Utils",
    "TicksGen",
    "create_legacy_mt5_mcp_server",
    "create_mt5_mcp_server",
    "get_mt5_api",
    "normalize_broker_response",
    "reject_stale_execution_inputs",
    "timeframe_seconds",
]
