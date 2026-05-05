from __future__ import annotations

import pytest

from backend.orchestration.workflow.states import ProposalState
from services.strategy.proposals import ProposalStateTransitionService


def test_proposal_state_transition_service_allows_valid_transition() -> None:
    result = ProposalStateTransitionService().transition(
        current_state=ProposalState.READY_FOR_RISK,
        next_state=ProposalState.APPROVED,
    )
    assert result.allowed is True
    assert result.next_state is ProposalState.APPROVED


def test_proposal_state_transition_service_rejects_invalid_transition() -> None:
    with pytest.raises(ValueError):
        ProposalStateTransitionService().transition(
            current_state=ProposalState.DRAFT,
            next_state=ProposalState.FILLED,
        )
