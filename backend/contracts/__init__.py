"""Shared contract primitives for the agentic migration."""

from .common import CanonicalEnvelope, Environment, OperatingMode, Originator, OriginatorType
from .schema_registry import RegistryStatus, SchemaRegistryRecord
from .schema_registry_persistence import (
    SCHEMA_REGISTRY_TABLE,
    SchemaRegistryRow,
    record_to_row,
    row_to_record,
)
from .schema_registry_seeds import INITIAL_SCHEMA_SEEDS, load_initial_schema_registry_seeds
from .schema_registry_service import SchemaRegistryResolutionError, SchemaRegistryService
from .schema_registry_validator import ContractValidationError, validate_contract_payload
from .serialization import (
    canonical_json_dumps,
    canonical_json_loads,
    deserialize_contract,
    serialize_contract,
)

__all__ = [
    "CanonicalEnvelope",
    "Environment",
    "OperatingMode",
    "Originator",
    "OriginatorType",
    "RegistryStatus",
    "SchemaRegistryRecord",
    "SCHEMA_REGISTRY_TABLE",
    "SchemaRegistryRow",
    "SchemaRegistryResolutionError",
    "SchemaRegistryService",
    "ContractValidationError",
    "INITIAL_SCHEMA_SEEDS",
    "canonical_json_dumps",
    "canonical_json_loads",
    "deserialize_contract",
    "load_initial_schema_registry_seeds",
    "record_to_row",
    "row_to_record",
    "serialize_contract",
    "validate_contract_payload",
]
