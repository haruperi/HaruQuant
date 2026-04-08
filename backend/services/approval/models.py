"""Approval domain models."""

from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum


class ApprovalState(StrEnum):
    PENDING = "PENDING"
    PARTIALLY_APPROVED = "PARTIALLY_APPROVED"
    APPROVED = "APPROVED"
    REJECTED = "REJECTED"
    EXPIRED = "EXPIRED"


@dataclass(frozen=True)
class ApprovalRequest:
    approval_id: str
    action_type: str
    target_ref_type: str
    target_ref_id: str
    required_count: int
    state: ApprovalState
    created_by_actor_type: str
    created_by_actor_id: str
    compliance_profile_id: str | None = None
    expires_at: str | None = None
