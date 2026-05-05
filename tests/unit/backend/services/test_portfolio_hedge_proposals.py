from __future__ import annotations

import pytest

from services.risk import PositionExposure
from services.risk.portfolio import generate_hedge_proposal


def test_generate_hedge_proposal_builds_advisory_hedge_action() -> None:
    proposal = generate_hedge_proposal(
        source_position=PositionExposure(
            symbol="EURUSD",
            currency="USD",
            strategy_family="trend",
            notional_exposure=1000.0,
            direction="buy",
        ),
        hedge_symbols=("USDCHF", "DXY"),
    )

    assert proposal.action_type == "hedge"
    assert proposal.advisory_only is True
    assert proposal.symbol == "EURUSD"
    assert proposal.hedge_symbols == ("USDCHF", "DXY")
    assert proposal.affected_symbols == ("EURUSD", "USDCHF", "DXY")


def test_generate_hedge_proposal_requires_hedge_symbols() -> None:
    with pytest.raises(ValueError, match="must not be empty"):
        generate_hedge_proposal(
            source_position=PositionExposure(
                symbol="EURUSD",
                currency="USD",
                strategy_family="trend",
                notional_exposure=1000.0,
                direction="buy",
            ),
            hedge_symbols=(),
        )
