"""Operator API skeleton exports."""

from .auth import OperatorAuthMiddleware, OperatorPrincipal, get_operator_principal, require_operator_role
from .app import app, create_app, get_operator_api_dependencies
from .dependencies import OperatorApiDependencies, build_operator_api_dependencies
from .health import (
    check_app_health,
    check_database_health,
    check_redis_health,
    check_schema_registry_health,
)

__all__ = [
    "OperatorAuthMiddleware",
    "OperatorApiDependencies",
    "OperatorPrincipal",
    "app",
    "build_operator_api_dependencies",
    "check_app_health",
    "check_database_health",
    "check_redis_health",
    "check_schema_registry_health",
    "create_app",
    "get_operator_principal",
    "get_operator_api_dependencies",
    "require_operator_role",
]
