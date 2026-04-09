from __future__ import annotations

import pytest

from backend.services import generate_rebalance_proposal


def test_generate_rebalance_proposal_normalizes_target_allocations() -> None:
    proposal = generate_rebalance_proposal(
        target_allocations={
            "EURUSD": 60.0,
            "USDJPY": 40.0,
        }
    )

    assert proposal.action_type == "rebalance"
    assert proposal.advisory_only is True
    assert proposal.target_allocations == {
        "EURUSD": pytest.approx(0.6),
        "USDJPY": pytest.approx(0.4),
    }
    assert proposal.affected_symbols == ("EURUSD", "USDJPY")


def test_generate_rebalance_proposal_requires_positive_allocations() -> None:
    with pytest.raises(ValueError, match="positive value"):
        generate_rebalance_proposal(target_allocations={"EURUSD": 0.0})
