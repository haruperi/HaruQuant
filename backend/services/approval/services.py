"""Approval creation and voting services."""

from __future__ import annotations

from dataclasses import dataclass

from apps.core import ValidationError, generate_id
from backend.db import ApprovalRecord, GovernanceRepository

from .models import ApprovalState


@dataclass(frozen=True)
class ApprovalCreateRequest:
    action_type: str
    target_ref_type: str
    target_ref_id: str
    required_count: int
    created_by_actor_type: str
    created_by_actor_id: str
    compliance_profile_id: str | None = None
    expires_at: str | None = None
    metadata_json: str = "{}"


class ApprovalCreationService:
    """Create approval requests with minimal validation."""

    def __init__(self, repository: GovernanceRepository) -> None:
        self.repository = repository

    def create(self, request: ApprovalCreateRequest) -> ApprovalRecord:
        if request.required_count <= 0:
            raise ValidationError(
                "approval_required_count_invalid",
                "Approval creation requires a positive required_count.",
            )
        if request.expires_at is None:
            raise ValidationError(
                "approval_expiry_required",
                "Approval creation requires an expiry timestamp.",
            )

        return self.repository.create_approval(
            approval_id=generate_id("approval"),
            action_type=request.action_type,
            target_ref_type=request.target_ref_type,
            target_ref_id=request.target_ref_id,
            required_count=request.required_count,
            state=ApprovalState.PENDING.value,
            created_by_actor_type=request.created_by_actor_type,
            created_by_actor_id=request.created_by_actor_id,
            compliance_profile_id=request.compliance_profile_id,
            expires_at=request.expires_at,
            metadata_json=request.metadata_json,
        )
