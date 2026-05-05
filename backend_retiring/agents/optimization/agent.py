"""Optimization Department facade over optimization MCP and services."""

OPTIMIZATION_DEPARTMENT = "optimization"
CANONICAL_SOURCES = (
    "services.optimization",
    "backend_retiring.mcp.optimization_mcp",
)


def create_department_optimization_mcp_server(*args, **kwargs):
    """Create the governed optimization MCP server lazily."""

    from backend_retiring.mcp.optimization_mcp import create_optimization_mcp_server

    return create_optimization_mcp_server(*args, **kwargs)

__all__ = [
    "OPTIMIZATION_DEPARTMENT",
    "CANONICAL_SOURCES",
    "create_department_optimization_mcp_server",
]
