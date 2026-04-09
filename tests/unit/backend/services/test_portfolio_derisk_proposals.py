from __future__ import annotations

import pytest

from backend.services import generate_derisk_proposal


def test_generate_derisk_proposal_builds_advisory_action() -> None:
    proposal = generate_derisk_proposal(
        affected_symbols=("EURUSD", "GBPUSD"),
        target_reduction_ratio=0.35,
    )

    assert proposal.action_type == "de_risk"
    assert proposal.advisory_only is True
    assert proposal.affected_symbols == ("EURUSD", "GBPUSD")
    assert proposal.target_size == {"reduction_ratio": 0.35}


def test_generate_derisk_proposal_validates_inputs() -> None:
    with pytest.raises(ValueError, match="must not be empty"):
        generate_derisk_proposal(
            affected_symbols=(),
            target_reduction_ratio=0.2,
        )

    with pytest.raises(ValueError, match="within"):
        generate_derisk_proposal(
            affected_symbols=("EURUSD",),
            target_reduction_ratio=0.0,
        )
