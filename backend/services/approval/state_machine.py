"""Approval state machine."""

from __future__ import annotations

from apps.core import PolicyError

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


class ApprovalStateMachine:
    """Deterministic approval transition validator."""

    def validate(self, from_state: ApprovalState, to_state: ApprovalState) -> None:
        if to_state not in APPROVAL_TRANSITIONS[from_state]:
            raise PolicyError(
                "approval_transition_not_allowed",
                "Approval transition is not allowed.",
                details={"from_state": from_state.value, "to_state": to_state.value},
            )
