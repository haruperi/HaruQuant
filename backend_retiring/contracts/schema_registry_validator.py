"""Runtime contract validation against the schema registry."""

from __future__ import annotations

from importlib import import_module
from typing import Any

from pydantic import BaseModel, ValidationError

from .schema_registry_service import SchemaRegistryResolutionError, SchemaRegistryService


class ContractValidationError(ValueError):
    """Raised when a contract cannot be validated against the registry."""


def _load_model_type(model_ref: str) -> type[BaseModel]:
    module_name, _, attr_name = model_ref.rpartition(".")
    if not module_name or not attr_name:
        raise ContractValidationError(f"Invalid model reference '{model_ref}'.")

    module = import_module(module_name)
    model_type = getattr(module, attr_name, None)
    if model_type is None or not isinstance(model_type, type) or not issubclass(model_type, BaseModel):
        raise ContractValidationError(f"Model reference '{model_ref}' did not resolve to a Pydantic model.")
    return model_type


def validate_contract_payload(
    payload: dict[str, Any],
    registry: SchemaRegistryService,
) -> BaseModel:
    """Validate a raw contract payload using schema registry metadata."""

    contract_type = payload.get("contract_type")
    schema_version = payload.get("schema_version")

    if not contract_type or not schema_version:
        raise ContractValidationError("Contract payload must include contract_type and schema_version.")

    try:
        record = registry.get_version(contract_type, schema_version)
    except SchemaRegistryResolutionError as exc:
        raise ContractValidationError(str(exc)) from exc

    model_type = _load_model_type(record.pydantic_model_ref)

    try:
        return model_type.model_validate(payload)
    except ValidationError as exc:
        raise ContractValidationError(str(exc)) from exc
