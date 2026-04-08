"""Persistence models for schema registry records."""

from __future__ import annotations

from datetime import datetime
from typing import Any, Mapping

from pydantic import BaseModel, ConfigDict, Field

from .schema_registry import SchemaRegistryRecord


SCHEMA_REGISTRY_TABLE = "schema_registry"


class SchemaRegistryRow(BaseModel):
    """Storage-shaped representation of a schema registry record."""

    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)

    contract_type: str = Field(min_length=1)
    schema_version: str = Field(min_length=1)
    semantic_version: str = Field(min_length=1)
    status: str = Field(min_length=1)
    effective_from: datetime
    deprecated_from: datetime | None = None
    compatibility_policy: str = Field(min_length=1)
    payload_hash: str = Field(min_length=1)
    json_schema_ref: str = Field(min_length=1)
    pydantic_model_ref: str = Field(min_length=1)
    owning_domain_team: str = Field(min_length=1)
    changelog_summary: str = Field(min_length=1)


def record_to_row(record: SchemaRegistryRecord) -> SchemaRegistryRow:
    """Convert a domain record into a persistence-shaped row."""

    return SchemaRegistryRow.model_validate(record.model_dump())


def row_to_record(row: SchemaRegistryRow | Mapping[str, Any]) -> SchemaRegistryRecord:
    """Convert a persistence row or row-like mapping into a domain record."""

    if isinstance(row, SchemaRegistryRow):
        payload = row.model_dump()
    else:
        payload = dict(row)
    return SchemaRegistryRecord.model_validate(payload)
