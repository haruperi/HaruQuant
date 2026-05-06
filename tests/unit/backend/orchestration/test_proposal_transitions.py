from services.governance.workflow import (
    ProposalState,
    is_allowed_proposal_transition,
)


def test_proposal_transition_map_allows_expected_lifecycle_paths() -> None:
    assert is_allowed_proposal_transition(ProposalState.DRAFT, ProposalState.EVIDENCE_PENDING)
    assert is_allowed_proposal_transition(ProposalState.READY_FOR_RISK, ProposalState.APPROVED)
    assert is_allowed_proposal_transition(ProposalState.APPROVED, ProposalState.EXECUTION_PENDING)
    assert is_allowed_proposal_transition(ProposalState.SENT, ProposalState.ACKNOWLEDGED)
    assert is_allowed_proposal_transition(ProposalState.PARTIALLY_FILLED, ProposalState.CLOSED)


def test_proposal_transition_map_rejects_invalid_or_terminal_paths() -> None:
    assert not is_allowed_proposal_transition(ProposalState.DRAFT, ProposalState.FILLED)
    assert not is_allowed_proposal_transition(ProposalState.READY_FOR_RISK, ProposalState.SENT)
    assert not is_allowed_proposal_transition(ProposalState.REJECTED, ProposalState.APPROVED)
    assert not is_allowed_proposal_transition(ProposalState.CLOSED, ProposalState.EXECUTION_PENDING)

