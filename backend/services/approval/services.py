"""Approval creation and voting services."""

from __future__ import annotations

from dataclasses import dataclass
import sqlite3

from backend.common import ValidationError, generate_id
from backend.data.database import ApprovalRecord, ApprovalVoteRecord, GovernanceRepository

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


@dataclass(frozen=True)
class ApprovalVoteRequest:
    approval_id: str
    approver_role: str
    approver_id: str
    decision: str
    reason_code: str | None = None
    rationale: str | None = None


class ApprovalVoteService:
    """Persist approval votes while enforcing distinct approver identity."""

    def __init__(self, repository: GovernanceRepository) -> None:
        self.repository = repository

    def vote(self, request: ApprovalVoteRequest) -> ApprovalVoteRecord:
        with self.repository._connect() as connection:  # noqa: SLF001
            existing = connection.execute(
                """
                SELECT 1
                FROM gov_approval_votes
                WHERE approval_id = ? AND approver_id = ?
                """,
                (request.approval_id, request.approver_id),
            ).fetchone()
        if existing is not None:
            raise ValidationError(
                "approval_duplicate_voter",
                "An approver may vote only once per approval.",
            )

        try:
            return self.repository.add_vote(
                approval_id=request.approval_id,
                approver_role=request.approver_role,
                approver_id=request.approver_id,
                decision=request.decision,
                reason_code=request.reason_code,
                rationale=request.rationale,
            )
        except sqlite3.IntegrityError as exc:
            raise ValidationError(
                "approval_duplicate_voter",
                "An approver may vote only once per approval.",
            ) from exc
