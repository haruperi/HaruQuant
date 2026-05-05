"""Optimization Department facade.

Imports are lazy to avoid loading heavy optimization execution modules during
package discovery.
"""

OPTIMIZATION_DEPARTMENT = "optimization"
CANONICAL_SOURCES = (
    "services.optimization",
    "backend.mcp.optimization_mcp",
)


def create_department_optimization_mcp_server(*args, **kwargs):
    """Create the governed optimization MCP server lazily."""

    from backend.mcp.optimization_mcp import create_optimization_mcp_server

    return create_optimization_mcp_server(*args, **kwargs)


__all__ = [
    "OPTIMIZATION_DEPARTMENT",
    "CANONICAL_SOURCES",
    "create_department_optimization_mcp_server",
]
