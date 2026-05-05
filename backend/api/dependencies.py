"""Dependency wiring for the migration-era operator API."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from haruquant.utils import logger
from haruquant.utils import RuntimeSettings, load_runtime_settings
from backend.contracts import SchemaRegistryService, load_initial_schema_registry_seeds
from backend.data.database import (
    GovernanceRepository,
    apply_pending_migrations,
    default_migrations_dir,
)
from haruquant.risk import PolicyResolver


@dataclass(frozen=True)
class OperatorApiDependencies:
    """Shared service container for the operator API skeleton."""

    settings: RuntimeSettings
    schema_registry: SchemaRegistryService
    policy_resolver: PolicyResolver
    governance_repository: GovernanceRepository


def resolve_sqlite_database_path(database_url: str) -> Path:
    """Resolve the SQLite database path from a runtime database URL."""

    if not database_url.startswith("sqlite:///"):
        raise ValueError("Only sqlite database URLs are supported by the operator API skeleton.")
    return Path(database_url.replace("sqlite:///", "", 1))


def build_operator_api_dependencies(
    *,
    settings: RuntimeSettings | None = None,
) -> OperatorApiDependencies:
    """Construct the minimum dependency set needed by the operator API."""

    runtime_settings = settings or load_runtime_settings()
    database_path = resolve_sqlite_database_path(runtime_settings.database_url)
    database_path.parent.mkdir(parents=True, exist_ok=True)
    apply_pending_migrations(database_path, default_migrations_dir())
    return OperatorApiDependencies(
        settings=runtime_settings,
        schema_registry=SchemaRegistryService(load_initial_schema_registry_seeds()),
        policy_resolver=PolicyResolver(bundles=()),
        governance_repository=GovernanceRepository(database_path),
    )
