from __future__ import annotations

import pytest

from haruquant.risk import PositionExposure
from haruquant.risk import calculate_marginal_risk_contribution


def test_calculate_marginal_risk_contribution_normalizes_position_shares() -> None:
    contributions = calculate_marginal_risk_contribution(
        (
            PositionExposure(
                symbol="EURUSD",
                currency="USD",
                strategy_family="trend",
                notional_exposure=1000.0,
                direction="buy",
            ),
            PositionExposure(
                symbol="USDJPY",
                currency="JPY",
                strategy_family="carry",
                notional_exposure=500.0,
                direction="sell",
            ),
            PositionExposure(
                symbol="GBPUSD",
                currency="USD",
                strategy_family="trend",
                notional_exposure=500.0,
                direction="buy",
            ),
        )
    )

    assert [item.position_key for item in contributions] == [
        "EURUSD:trend:1",
        "USDJPY:carry:2",
        "GBPUSD:trend:3",
    ]
    assert contributions[0].contribution_ratio == pytest.approx(0.5)
    assert contributions[1].contribution_ratio == pytest.approx(0.25)
    assert contributions[2].contribution_ratio == pytest.approx(0.25)
    assert sum(item.contribution_ratio for item in contributions) == pytest.approx(1.0)


def test_calculate_marginal_risk_contribution_returns_empty_for_zero_gross_exposure() -> None:
    contributions = calculate_marginal_risk_contribution(
        (
            PositionExposure(
                symbol="EURUSD",
                currency="USD",
                strategy_family="trend",
                notional_exposure=0.0,
                direction="buy",
            ),
        )
    )

    assert contributions == ()
