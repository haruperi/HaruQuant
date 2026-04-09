from __future__ import annotations

import pytest

from backend.services import enforce_portfolio_advisory_only, generate_resize_proposal, PositionExposure


def test_enforce_portfolio_advisory_only_allows_advisory_path() -> None:
    proposal = generate_resize_proposal(
        position=PositionExposure(
            symbol="EURUSD",
            currency="USD",
            strategy_family="trend",
            notional_exposure=1000.0,
            direction="buy",
        ),
        target_notional_exposure=800.0,
    )

    returned = enforce_portfolio_advisory_only(
        proposal,
        requested_live_execution=False,
    )

    assert returned is proposal


def test_enforce_portfolio_advisory_only_rejects_live_execution_request() -> None:
    proposal = generate_resize_proposal(
        position=PositionExposure(
            symbol="EURUSD",
            currency="USD",
            strategy_family="trend",
            notional_exposure=1000.0,
            direction="buy",
        ),
        target_notional_exposure=800.0,
    )

    with pytest.raises(ValueError, match="advisory-only"):
        enforce_portfolio_advisory_only(
            proposal,
            requested_live_execution=True,
        )
