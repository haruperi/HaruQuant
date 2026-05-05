from __future__ import annotations

import pytest

from services.risk import PositionExposure
from services.risk.portfolio import generate_resize_proposal


def test_generate_resize_proposal_builds_advisory_action() -> None:
    proposal = generate_resize_proposal(
        position=PositionExposure(
            symbol="EURUSD",
            currency="USD",
            strategy_family="trend",
            notional_exposure=1000.0,
            direction="buy",
        ),
        target_notional_exposure=750.0,
    )

    assert proposal.action_type == "resize"
    assert proposal.advisory_only is True
    assert proposal.symbol == "EURUSD"
    assert proposal.target_size == {"current": 1000.0, "target": 750.0}
    assert proposal.affected_symbols == ("EURUSD",)


def test_generate_resize_proposal_rejects_negative_target_size() -> None:
    with pytest.raises(ValueError, match="non-negative"):
        generate_resize_proposal(
            position=PositionExposure(
                symbol="EURUSD",
                currency="USD",
                strategy_family="trend",
                notional_exposure=1000.0,
                direction="buy",
            ),
            target_notional_exposure=-1.0,
        )
