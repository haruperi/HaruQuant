"""Shared canonical envelope models used by all contract families."""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

from pydantic import BaseModel, ConfigDict, Field, field_validator


Environment = str
OperatingMode = str
OriginatorType = str

ENVIRONMENTS = {"dev", "test", "paper", "staging", "prod"}
OPERATING_MODES = {"MODE-000", "MODE-001", "MODE-002", "MODE-003", "MODE-004"}
ORIGINATOR_TYPES = {"user", "agent", "service", "tool", "operator"}


class Originator(BaseModel):
    """Identity metadata for the immediate producer of a canonical contract."""

    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)

    type: OriginatorType
    id: str = Field(min_length=1)

    @field_validator("type")
    @classmethod
    def _validate_type(cls, value: str) -> str:
        normalized = value.lower()
        if normalized not in ORIGINATOR_TYPES:
            raise ValueError(
                f"Unsupported originator type '{value}'. "
                f"Expected one of: {', '.join(sorted(ORIGINATOR_TYPES))}"
            )
        return normalized


class CanonicalEnvelope(BaseModel):
    """Common metadata envelope shared by all canonical contracts."""

    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)

    schema_version: str = "1.0.0"
    contract_type: str = Field(min_length=1)
    workflow_id: str = Field(min_length=1)
    correlation_id: str = Field(min_length=1)
    causation_id: str = Field(min_length=1)
    timestamp_utc: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    originator: Originator
    environment: Environment
    operating_mode: OperatingMode
    payload: dict[str, Any]
    tenant_id: str | None = None
    account_scope_id: str | None = None
    strategy_scope_id: str | None = None
    compliance_profile_id: str | None = None
    content_hash: str | None = None
    signature: str | None = None
    trace_id: str | None = None
    replay_bundle_hint: str | None = None

    @field_validator("environment")
    @classmethod
    def _validate_environment(cls, value: str) -> str:
        normalized = value.lower()
        if normalized not in ENVIRONMENTS:
            raise ValueError(
                f"Unsupported environment '{value}'. "
                f"Expected one of: {', '.join(sorted(ENVIRONMENTS))}"
            )
        return normalized

    @field_validator("operating_mode")
    @classmethod
    def _validate_operating_mode(cls, value: str) -> str:
        normalized = value.upper()
        if normalized not in OPERATING_MODES:
            raise ValueError(
                f"Unsupported operating mode '{value}'. "
                f"Expected one of: {', '.join(sorted(OPERATING_MODES))}"
            )
        return normalized

    @field_validator("timestamp_utc")
    @classmethod
    def _validate_timestamp_utc(cls, value: datetime) -> datetime:
        if value.tzinfo is None:
            return value.replace(tzinfo=timezone.utc)
        return value.astimezone(timezone.utc)
