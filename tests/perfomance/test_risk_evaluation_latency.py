from __future__ import annotations

from statistics import quantiles
from time import perf_counter

from services.risk import (
    PositionExposure,
    compose_risk_decision,
    calculate_currency_concentration,
    calculate_drawdown_state,
    calculate_exposure_summary,
    calculate_margin_utilization,
    calculate_strategy_family_concentration,
    calculate_symbol_concentration,
    calculate_volatility_adjusted_size,
    evaluate_compliance_profile_compatibility,
    evaluate_operating_mode_compatibility,
    evaluate_regime_restriction,
    evaluate_session_restrictions,
    evaluate_spread_slippage_precheck,
)


def _p95(samples_ms: list[float]) -> float:
    return quantiles(samples_ms, n=100)[94]


def test_risk_eval_p95_under_300ms() -> None:
    positions = (
        PositionExposure("EURUSD", "USD", "fx_momentum", 100_000, "buy"),
        PositionExposure("GBPUSD", "USD", "fx_momentum", 80_000, "sell"),
        PositionExposure("USDJPY", "JPY", "fx_mean_reversion", 50_000, "buy"),
        PositionExposure("XAUUSD", "USD", "metals_breakout", 40_000, "buy"),
    )
    samples_ms: list[float] = []

    for _ in range(250):
        started = perf_counter()
        exposure = calculate_exposure_summary(positions)
        symbol = calculate_symbol_concentration(positions, threshold=0.65)
        currency = calculate_currency_concentration(positions, threshold=0.80)
        family = calculate_strategy_family_concentration(positions, threshold=0.70)
        margin = calculate_margin_utilization(
            balance=100_000,
            equity=99_500,
            free_margin=70_000,
            margin_used=29_500,
        )
        sizing = calculate_volatility_adjusted_size(
            base_size=1.0,
            reference_volatility=0.008,
            observed_volatility=0.010,
        )
        drawdown = calculate_drawdown_state(peak_equity=105_000, current_equity=99_500)
        checks = (
            evaluate_regime_restriction(current_regime="trend", allowed_regimes=("trend", "range")),
            evaluate_session_restrictions(
                current_time=__import__("datetime").datetime(2026, 4, 9, 10, 5),
                allowed_window=("08:00", "17:00"),
            ),
            evaluate_spread_slippage_precheck(
                spread_points=1.2,
                max_spread_points=2.0,
                expected_slippage_points=0.8,
                max_slippage_points=1.5,
            ),
            evaluate_operating_mode_compatibility(
                workflow_operating_mode="MODE-003",
                allowed_operating_modes=("MODE-003", "MODE-004"),
            ),
            evaluate_compliance_profile_compatibility(
                active_compliance_profile_id="comp_uae_enterprise",
                allowed_compliance_profile_ids=("comp_uae_enterprise",),
            ),
        )
        decision = compose_risk_decision(checks=checks)
        elapsed_ms = (perf_counter() - started) * 1000
        samples_ms.append(elapsed_ms)

        assert exposure.position_count == 4
        assert symbol.total_gross_exposure > 0
        assert currency.total_gross_exposure > 0
        assert family.total_gross_exposure > 0
        assert margin.utilization_ratio > 0
        assert sizing.adjusted_size > 0
        assert drawdown.band in {"normal", "elevated", "restricted", "critical"}
        assert decision.decision == "APPROVE"

    assert _p95(samples_ms) <= 300.0

