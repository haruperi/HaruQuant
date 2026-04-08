"""Shared contract primitives for the agentic migration."""

from .common import CanonicalEnvelope, Environment, OperatingMode, Originator, OriginatorType
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
    "canonical_json_dumps",
    "canonical_json_loads",
    "deserialize_contract",
    "serialize_contract",
]
