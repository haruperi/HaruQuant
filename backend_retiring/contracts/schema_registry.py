"""Schema registry domain models for canonical contract governance."""

from __future__ import annotations

from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field


RegistryStatus = Literal["draft", "active", "deprecated", "retired"]


class SchemaRegistryRecord(BaseModel):
    """Metadata record for one canonical contract schema version."""

    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)

    contract_type: str = Field(min_length=1)
    schema_version: str = Field(min_length=1)
    semantic_version: str = Field(min_length=1)
    status: RegistryStatus
    effective_from: datetime
    deprecated_from: datetime | None = None
    compatibility_policy: str = Field(min_length=1)
    payload_hash: str = Field(min_length=1)
    json_schema_ref: str = Field(min_length=1)
    pydantic_model_ref: str = Field(min_length=1)
    owning_domain_team: str = Field(min_length=1)
    changelog_summary: str = Field(min_length=1)
