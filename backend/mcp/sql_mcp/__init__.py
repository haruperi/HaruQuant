"""Governed MCP wrapper over legacy SQL access."""

from .server import SQLMCPServer, create_sql_mcp_server
from .tools import SQLMCPAccessError, SQLQueryResult, SQLReadOnlyTools

__all__ = [
    "SQLMCPAccessError",
    "SQLMCPServer",
    "SQLQueryResult",
    "SQLReadOnlyTools",
    "create_sql_mcp_server",
]
