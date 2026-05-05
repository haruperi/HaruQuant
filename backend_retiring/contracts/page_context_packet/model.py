"""PageContextPacket canonical contract models."""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator

from backend_retiring.contracts.common import CanonicalEnvelope, Originator


PageType = Literal[
    "dashboard",
    "strategy_detail",
    "backtest_detail",
    "optimization_detail",
    "portfolio_risk",
    "live_trading",
    "data_workspace",
    "operator_workflow",
    "generic",
]

TrustLevel = Literal["system_state", "derived_summary", "fallback"]


class EntityRef(BaseModel):
    model_config = ConfigDict(extra="forbid")

    type: str = Field(min_length=1)
    id: str = Field(min_length=1)
    label: str | None = None


class ContextFreshness(BaseModel):
    model_config = ConfigDict(extra="forbid")

    observed_at: datetime
    staleness_seconds: int = Field(ge=0)

    @field_validator("observed_at")
    @classmethod
    def _validate_observed_at(cls, value: datetime) -> datetime:
        if value.tzinfo is None:
            return value.replace(tzinfo=timezone.utc)
        return value.astimezone(timezone.utc)


class ContextAuthority(BaseModel):
    model_config = ConfigDict(extra="forbid")

    source: str = Field(min_length=1)
    trust_level: TrustLevel


class ContextSummary(BaseModel):
    model_config = ConfigDict(extra="forbid")

    headline: str = Field(min_length=1)
    bullets: list[str] = Field(default_factory=list, max_length=8)


class PageContextPayload(BaseModel):
    model_config = ConfigDict(extra="forbid")

    route: str = Field(min_length=1)
    page_type: PageType
    page_title: str | None = None
    entity_refs: list[EntityRef] = Field(default_factory=list)
    context_revision: str = Field(min_length=1)
    generated_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    freshness: ContextFreshness
    authority: ContextAuthority
    summary: ContextSummary
    payload: dict[str, Any] = Field(default_factory=dict)

    @field_validator("generated_at")
    @classmethod
    def _validate_generated_at(cls, value: datetime) -> datetime:
        if value.tzinfo is None:
            return value.replace(tzinfo=timezone.utc)
        return value.astimezone(timezone.utc)


class PageContextPacket(CanonicalEnvelope):
    """Canonical envelope specialization for page-aware context packets."""

    contract_type: Literal["PageContextPacket"] = "PageContextPacket"
    payload: PageContextPayload


__all__ = [
    "ContextAuthority",
    "ContextFreshness",
    "ContextSummary",
    "EntityRef",
    "Originator",
    "PageContextPacket",
    "PageContextPayload",
    "PageType",
    "TrustLevel",
]
