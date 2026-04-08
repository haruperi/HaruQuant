"""Shared contract primitives for the agentic migration."""

from .common import CanonicalEnvelope, Environment, OperatingMode, Originator, OriginatorType
from .schema_registry import RegistryStatus, SchemaRegistryRecord
from .schema_registry_persistence import (
    SCHEMA_REGISTRY_TABLE,
    SchemaRegistryRow,
    record_to_row,
    row_to_record,
)
from .schema_registry_service import SchemaRegistryResolutionError, SchemaRegistryService
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
    "canonical_json_dumps",
    "canonical_json_loads",
    "deserialize_contract",
    "record_to_row",
    "row_to_record",
    "serialize_contract",
]
