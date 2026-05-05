from __future__ import annotations

import pytest

from services.risk import (
    PositionExposure,
    calculate_currency_concentration,
    calculate_exposure_summary,
    calculate_strategy_family_concentration,
    calculate_symbol_concentration,
)


def test_calculate_exposure_summary_returns_gross_and_net_exposure():
    positions = (
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
            notional_exposure=600.0,
            direction="sell",
        ),
        PositionExposure(
            symbol="GBPUSD",
            currency="USD",
            strategy_family="trend",
            notional_exposure=250.0,
            direction="buy",
        ),
    )

    summary = calculate_exposure_summary(positions)

    assert summary.gross_exposure == 1850.0
    assert summary.net_exposure == 650.0
    assert summary.position_count == 3


def test_position_exposure_rejects_unknown_direction_when_signed_exposure_requested():
    position = PositionExposure(
        symbol="EURUSD",
        currency="USD",
        strategy_family="trend",
        notional_exposure=1000.0,
        direction="hold",
    )

    try:
        position.signed_exposure
    except ValueError as exc:
        assert "unsupported direction" in str(exc)
    else:
        raise AssertionError("expected ValueError for unsupported direction")


def test_calculate_symbol_concentration_reports_threshold_breach():
    positions = (
        PositionExposure(
            symbol="EURUSD",
            currency="USD",
            strategy_family="trend",
            notional_exposure=800.0,
            direction="buy",
        ),
        PositionExposure(
            symbol="EURUSD",
            currency="USD",
            strategy_family="mean_reversion",
            notional_exposure=200.0,
            direction="sell",
        ),
        PositionExposure(
            symbol="USDJPY",
            currency="JPY",
            strategy_family="carry",
            notional_exposure=500.0,
            direction="buy",
        ),
    )

    result = calculate_symbol_concentration(positions, threshold=0.6)

    assert result.total_gross_exposure == 1500.0
    assert result.concentrations["EURUSD"] == 1000.0 / 1500.0
    assert result.concentrations["USDJPY"] == 500.0 / 1500.0
    assert result.breached_keys == ("EURUSD",)


def test_calculate_currency_concentration_supports_multi_currency_thresholds():
    positions = (
        PositionExposure(
            symbol="EURUSD",
            currency="USD",
            strategy_family="trend",
            notional_exposure=700.0,
            direction="buy",
        ),
        PositionExposure(
            symbol="GBPUSD",
            currency="USD",
            strategy_family="carry",
            notional_exposure=300.0,
            direction="sell",
        ),
        PositionExposure(
            symbol="USDJPY",
            currency="JPY",
            strategy_family="carry",
            notional_exposure=500.0,
            direction="buy",
        ),
    )

    result = calculate_currency_concentration(positions, threshold=0.65)

    assert result.concentrations["USD"] == pytest.approx(1000.0 / 1500.0)
    assert result.concentrations["JPY"] == pytest.approx(500.0 / 1500.0)
    assert result.breached_keys == ("USD",)


def test_calculate_strategy_family_concentration_reports_family_breach():
    positions = (
        PositionExposure(
            symbol="EURUSD",
            currency="USD",
            strategy_family="trend",
            notional_exposure=700.0,
            direction="buy",
        ),
        PositionExposure(
            symbol="GBPUSD",
            currency="USD",
            strategy_family="trend",
            notional_exposure=200.0,
            direction="sell",
        ),
        PositionExposure(
            symbol="USDJPY",
            currency="JPY",
            strategy_family="carry",
            notional_exposure=300.0,
            direction="buy",
        ),
    )

    result = calculate_strategy_family_concentration(positions, threshold=0.7)

    assert result.concentrations["trend"] == pytest.approx(900.0 / 1200.0)
    assert result.concentrations["carry"] == pytest.approx(300.0 / 1200.0)
    assert result.breached_keys == ("trend",)
