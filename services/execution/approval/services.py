"""Approval creation and voting services."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
import sqlite3

from services.utils import ErrorDescriptor, ValidationError, generate_id
from backend.data.database import ApprovalRecord, ApprovalVoteRecord, GovernanceRepository

from .models import ApprovalState


_APPROVAL_REQUIRED_COUNT_INVALID = ErrorDescriptor(
    code=4001,
    name="APPROVAL_REQUIRED_COUNT_INVALID",
    message="Approval creation requires a positive required_count.",
)
_APPROVAL_EXPIRY_REQUIRED = ErrorDescriptor(
    code=4002,
    name="APPROVAL_EXPIRY_REQUIRED",
    message="Approval creation requires an expiry timestamp.",
)
_APPROVAL_DUPLICATE_VOTER = ErrorDescriptor(
    code=4003,
    name="APPROVAL_DUPLICATE_VOTER",
    message="An approver may vote only once per approval.",
)
_APPROVAL_NOT_FOUND = ErrorDescriptor(
    code=4004,
    name="APPROVAL_NOT_FOUND",
    message="Approval request not found.",
)


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
                _APPROVAL_REQUIRED_COUNT_INVALID,
            )
        if request.expires_at is None:
            raise ValidationError(
                _APPROVAL_EXPIRY_REQUIRED,
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
                _APPROVAL_DUPLICATE_VOTER,
            )

        try:
            vote = self.repository.add_vote(
                approval_id=request.approval_id,
                approver_role=request.approver_role,
                approver_id=request.approver_id,
                decision=request.decision,
                reason_code=request.reason_code,
                rationale=request.rationale,
            )
            self._refresh_approval_state(request.approval_id)
            return vote
        except sqlite3.IntegrityError as exc:
            raise ValidationError(
                _APPROVAL_DUPLICATE_VOTER,
            ) from exc

    def _refresh_approval_state(self, approval_id: str) -> None:
        approval = self.repository.get_approval(approval_id)
        if approval is None:
            raise ValidationError(_APPROVAL_NOT_FOUND)
        votes = self.repository.list_votes(approval_id)
        decisions = [vote.decision.strip().lower() for vote in votes]
        approve_count = sum(1 for decision in decisions if decision == "approve")
        has_reject = any(decision == "reject" for decision in decisions)
        next_state = ApprovalState.PENDING.value
        decided_at = None
        if has_reject:
            next_state = ApprovalState.REJECTED.value
            decided_at = datetime.now(timezone.utc).isoformat()
        elif approve_count >= approval.required_count:
            next_state = ApprovalState.APPROVED.value
            decided_at = datetime.now(timezone.utc).isoformat()
        elif approve_count > 0:
            next_state = ApprovalState.PARTIALLY_APPROVED.value
        if next_state != approval.state or decided_at != approval.decided_at:
            self.repository.update_approval_state(
                approval_id=approval_id,
                state=next_state,
                decided_at=decided_at,
            )
