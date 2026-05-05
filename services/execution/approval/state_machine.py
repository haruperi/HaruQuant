"""Approval state machine."""

from __future__ import annotations

from services.utils import ErrorDescriptor, PolicyError

from .models import ApprovalState


APPROVAL_TRANSITIONS: dict[ApprovalState, frozenset[ApprovalState]] = {
    ApprovalState.PENDING: frozenset(
        {
            ApprovalState.PARTIALLY_APPROVED,
            ApprovalState.APPROVED,
            ApprovalState.REJECTED,
            ApprovalState.EXPIRED,
        }
    ),
    ApprovalState.PARTIALLY_APPROVED: frozenset(
        {
            ApprovalState.APPROVED,
            ApprovalState.REJECTED,
            ApprovalState.EXPIRED,
        }
    ),
    ApprovalState.APPROVED: frozenset(),
    ApprovalState.REJECTED: frozenset(),
    ApprovalState.EXPIRED: frozenset(),
}

_APPROVAL_TRANSITION_NOT_ALLOWED = ErrorDescriptor(
    code=4010,
    name="APPROVAL_TRANSITION_NOT_ALLOWED",
    message="Approval transition is not allowed.",
    domain="approval",
)


class ApprovalStateMachine:
    """Deterministic approval transition validator."""

    def validate(self, from_state: ApprovalState, to_state: ApprovalState) -> None:
        if to_state not in APPROVAL_TRANSITIONS[from_state]:
            raise PolicyError(
                _APPROVAL_TRANSITION_NOT_ALLOWED,
                f"Approval transition is not allowed: {from_state.value} -> {to_state.value}.",
            )
