"""Canonical output validation for agent runtime results."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from pydantic import BaseModel

from backend.contracts import (
    ContractValidationError,
    SchemaRegistryService,
    load_initial_schema_registry_seeds,
    validate_contract_payload,
)


@dataclass(frozen=True)
class CanonicalValidationResult:
    contract_type: str
    schema_version: str
    validated_model: BaseModel


class CanonicalOutputValidator:
    """Validate agent outputs against the canonical schema registry."""

    def __init__(self, registry: SchemaRegistryService | None = None) -> None:
        self._registry = registry or SchemaRegistryService(load_initial_schema_registry_seeds())

    def validate(self, payload: dict[str, Any]) -> CanonicalValidationResult:
        validated_model = validate_contract_payload(payload, self._registry)
        return CanonicalValidationResult(
            contract_type=str(payload["contract_type"]),
            schema_version=str(payload["schema_version"]),
            validated_model=validated_model,
        )


__all__ = [
    "CanonicalOutputValidator",
    "CanonicalValidationResult",
    "ContractValidationError",
]
