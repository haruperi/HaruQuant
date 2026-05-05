"""ReplayBundle canonical contract models."""

from __future__ import annotations

from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

from backend_retiring.contracts.common import CanonicalEnvelope, Originator


CompletenessStatus = Literal["complete", "partial", "failed"]


class IntegrityManifest(BaseModel):
    """Minimal integrity manifest metadata for replay packages."""

    model_config = ConfigDict(extra="forbid")

    manifest_hash: str = Field(min_length=1)
    manifest_algorithm: str = Field(min_length=1)


class ReplayBundlePayload(BaseModel):
    """Payload fields for an immutable workflow reconstruction package."""

    model_config = ConfigDict(extra="forbid")

    replay_bundle_id: str = Field(min_length=1)
    workflow_id: str = Field(min_length=1)
    completeness_status: CompletenessStatus
    included_refs: list[str] = Field(default_factory=list)
    integrity_manifest: IntegrityManifest
    export_profile: str = Field(min_length=1)
    generated_at: datetime


class ReplayBundle(CanonicalEnvelope):
    """Canonical envelope specialization for ReplayBundle."""

    contract_type: Literal["ReplayBundle"] = "ReplayBundle"
    payload: ReplayBundlePayload


__all__ = [
    "CompletenessStatus",
    "IntegrityManifest",
    "Originator",
    "ReplayBundle",
    "ReplayBundlePayload",
]
