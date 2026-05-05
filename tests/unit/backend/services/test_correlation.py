from __future__ import annotations

import pytest

from services.risk import CorrelationPair, calculate_correlation_concentration


def test_calculate_correlation_concentration_reports_pair_and_portfolio_values():
    pairs = (
        CorrelationPair(
            left_key="EURUSD",
            right_key="GBPUSD",
            left_weight=0.4,
            right_weight=0.3,
            correlation=0.9,
        ),
        CorrelationPair(
            left_key="EURUSD",
            right_key="USDJPY",
            left_weight=0.4,
            right_weight=0.2,
            correlation=-0.5,
        ),
    )

    result = calculate_correlation_concentration(pairs, threshold=0.1)

    assert result.pair_concentrations["EURUSD:GBPUSD"] == pytest.approx(0.108)
    assert result.pair_concentrations["EURUSD:USDJPY"] == pytest.approx(0.04)
    assert result.portfolio_concentration == pytest.approx(0.148)
    assert result.breached_pairs == ("EURUSD:GBPUSD",)
