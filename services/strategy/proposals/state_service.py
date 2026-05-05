"""Proposal state transition service."""

from __future__ import annotations

from dataclasses import dataclass

from backend_retiring.orchestration.workflow.proposal_transitions import is_allowed_proposal_transition
from backend_retiring.orchestration.workflow.states import ProposalState


@dataclass(frozen=True)
class ProposalStateTransitionResult:
    """Result of a guarded proposal state transition."""

    previous_state: ProposalState
    next_state: ProposalState
    allowed: bool


class ProposalStateTransitionService:
    """Validate proposal state transitions against the canonical FSM."""

    def transition(
        self,
        *,
        current_state: ProposalState,
        next_state: ProposalState,
    ) -> ProposalStateTransitionResult:
        if not is_allowed_proposal_transition(current_state, next_state):
            raise ValueError(f"illegal proposal transition: {current_state} -> {next_state}")
        return ProposalStateTransitionResult(
            previous_state=current_state,
            next_state=next_state,
            allowed=True,
        )
