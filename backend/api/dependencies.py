"""Dependency wiring for the migration-era operator API."""

from __future__ import annotations

from dataclasses import dataclass

from apps.core.settings import RuntimeSettings, load_runtime_settings
from backend.contracts import SchemaRegistryService, load_initial_schema_registry_seeds
from backend.services.policy import PolicyResolver


@dataclass(frozen=True)
class OperatorApiDependencies:
    """Shared service container for the operator API skeleton."""

    settings: RuntimeSettings
    schema_registry: SchemaRegistryService
    policy_resolver: PolicyResolver


def build_operator_api_dependencies(
    *,
    settings: RuntimeSettings | None = None,
) -> OperatorApiDependencies:
    """Construct the minimum dependency set needed by the operator API."""

    runtime_settings = settings or load_runtime_settings()
    return OperatorApiDependencies(
        settings=runtime_settings,
        schema_registry=SchemaRegistryService(load_initial_schema_registry_seeds()),
        policy_resolver=PolicyResolver(bundles=()),
    )
