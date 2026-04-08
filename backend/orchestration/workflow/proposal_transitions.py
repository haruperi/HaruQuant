"""Trade proposal transition rules."""

from __future__ import annotations

from .states import ProposalState


PROPOSAL_TRANSITIONS: dict[ProposalState, frozenset[ProposalState]] = {
    ProposalState.DRAFT: frozenset(
        {
            ProposalState.EVIDENCE_PENDING,
            ProposalState.READY_FOR_RISK,
            ProposalState.REJECTED,
            ProposalState.EXPIRED,
        }
    ),
    ProposalState.EVIDENCE_PENDING: frozenset(
        {
            ProposalState.READY_FOR_RISK,
            ProposalState.REJECTED,
            ProposalState.EXPIRED,
        }
    ),
    ProposalState.READY_FOR_RISK: frozenset(
        {
            ProposalState.APPROVED,
            ProposalState.APPROVED_WITH_LIMITS,
            ProposalState.REJECTED,
            ProposalState.EXPIRED,
        }
    ),
    ProposalState.APPROVED: frozenset(
        {
            ProposalState.EXECUTION_PENDING,
            ProposalState.EXPIRED,
        }
    ),
    ProposalState.APPROVED_WITH_LIMITS: frozenset(
        {
            ProposalState.EXECUTION_PENDING,
            ProposalState.EXPIRED,
        }
    ),
    ProposalState.REJECTED: frozenset(),
    ProposalState.EXPIRED: frozenset(),
    ProposalState.EXECUTION_PENDING: frozenset(
        {
            ProposalState.SENT,
            ProposalState.EXECUTION_FAILED,
            ProposalState.EXPIRED,
        }
    ),
    ProposalState.SENT: frozenset(
        {
            ProposalState.ACKNOWLEDGED,
            ProposalState.PARTIALLY_FILLED,
            ProposalState.FILLED,
            ProposalState.EXECUTION_FAILED,
        }
    ),
    ProposalState.ACKNOWLEDGED: frozenset(
        {
            ProposalState.PARTIALLY_FILLED,
            ProposalState.FILLED,
            ProposalState.EXECUTION_FAILED,
        }
    ),
    ProposalState.PARTIALLY_FILLED: frozenset(
        {
            ProposalState.FILLED,
            ProposalState.CLOSED,
            ProposalState.EXECUTION_FAILED,
        }
    ),
    ProposalState.FILLED: frozenset(
        {
            ProposalState.CLOSED,
        }
    ),
    ProposalState.EXECUTION_FAILED: frozenset(
        {
            ProposalState.CLOSED,
        }
    ),
    ProposalState.CLOSED: frozenset(),
}


def is_allowed_proposal_transition(
    from_state: ProposalState,
    to_state: ProposalState,
) -> bool:
    """Return whether a proposal state transition is allowed."""

    return to_state in PROPOSAL_TRANSITIONS[from_state]
