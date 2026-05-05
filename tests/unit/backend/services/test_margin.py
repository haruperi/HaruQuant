from __future__ import annotations

import pytest

from services.risk import (
    calculate_drawdown_state,
    calculate_margin_utilization,
    calculate_volatility_adjusted_size,
)


def test_calculate_margin_utilization_returns_free_margin_ratio():
    result = calculate_margin_utilization(
        balance=10000.0,
        equity=9800.0,
        free_margin=7000.0,
        margin_used=3000.0,
    )

    assert result.balance == 10000.0
    assert result.equity == 9800.0
    assert result.utilization_ratio == pytest.approx(0.3)


def test_calculate_margin_utilization_handles_zero_denominator():
    result = calculate_margin_utilization(
        balance=0.0,
        equity=0.0,
        free_margin=0.0,
        margin_used=0.0,
    )

    assert result.utilization_ratio == 0.0


def test_calculate_volatility_adjusted_size_scales_down_when_volatility_rises():
    result = calculate_volatility_adjusted_size(
        base_size=2.0,
        reference_volatility=10.0,
        observed_volatility=20.0,
    )

    assert result.volatility_ratio == pytest.approx(0.5)
    assert result.adjusted_size == pytest.approx(1.0)


def test_calculate_volatility_adjusted_size_applies_bounds():
    result = calculate_volatility_adjusted_size(
        base_size=1.0,
        reference_volatility=10.0,
        observed_volatility=1.0,
        max_scale=1.5,
    )

    assert result.volatility_ratio == pytest.approx(1.5)
    assert result.adjusted_size == pytest.approx(1.5)


def test_calculate_drawdown_state_classifies_restricted_band():
    result = calculate_drawdown_state(
        peak_equity=10000.0,
        current_equity=8300.0,
    )

    assert result.drawdown_amount == pytest.approx(1700.0)
    assert result.drawdown_ratio == pytest.approx(0.17)
    assert result.band == "restricted"
