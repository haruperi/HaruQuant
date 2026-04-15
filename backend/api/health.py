"""Health checks for the operator API skeleton."""

from __future__ import annotations

from pathlib import Path
import sqlite3

from backend.common.logger import logger
from .dependencies import OperatorApiDependencies


def check_app_health(dependencies: OperatorApiDependencies) -> dict[str, object]:
    """Return a minimal application heartbeat."""

    return {
        "status": "healthy",
        "service": "haruquant-operator-api",
        "environment": dependencies.settings.environment,
    }


def check_database_health(dependencies: OperatorApiDependencies) -> dict[str, object]:
    """Run the smallest possible database connectivity check."""

    database_url = dependencies.settings.database_url
    if not database_url.startswith("sqlite:///"):
        return {
            "status": "unknown",
            "backend": database_url.split(":", 1)[0],
            "detail": "Database health probe is only implemented for sqlite skeleton environments.",
        }

    database_path = Path(database_url.replace("sqlite:///", "", 1))
    database_path.parent.mkdir(parents=True, exist_ok=True)
    with sqlite3.connect(database_path) as connection:
        connection.execute("SELECT 1")

    return {
        "status": "healthy",
        "backend": "sqlite",
        "database_path": str(database_path),
    }


def check_redis_health(dependencies: OperatorApiDependencies) -> dict[str, object]:
    """Report the current event-backend status."""

    if dependencies.settings.event_backend != "redis":
        return {
            "status": "disabled",
            "backend": dependencies.settings.event_backend,
            "detail": "Redis is not the configured event backend.",
        }

    return {
        "status": "unknown",
        "backend": "redis",
        "detail": "Redis probe is not wired yet.",
    }


def check_schema_registry_health(dependencies: OperatorApiDependencies) -> dict[str, object]:
    """Validate that the schema registry has active seeded contracts."""

    contract_types = tuple(dependencies.schema_registry._by_contract_type.keys())
    status = "healthy" if contract_types else "unhealthy"
    return {
        "status": status,
        "registered_contract_types": len(contract_types),
        "contract_types": contract_types,
    }
