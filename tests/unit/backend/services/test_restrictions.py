from __future__ import annotations

from datetime import datetime, timezone

from services.risk import evaluate_regime_restriction
from services.risk import evaluate_session_restrictions
from services.risk import evaluate_operating_mode_compatibility
from services.risk import evaluate_compliance_profile_compatibility
from services.risk import evaluate_spread_slippage_precheck


UTC = timezone.utc


def test_evaluate_regime_restriction_allows_supported_regime():
    result = evaluate_regime_restriction(
        current_regime="trend",
        allowed_regimes=("trend", "breakout"),
    )

    assert result.allowed is True
    assert result.reason_codes == ()


def test_evaluate_regime_restriction_blocks_unsupported_regime():
    result = evaluate_regime_restriction(
        current_regime="mean_reversion",
        allowed_regimes=("trend", "breakout"),
    )

    assert result.allowed is False
    assert result.reason_codes == ("regime_not_allowed",)


def test_evaluate_session_restrictions_blocks_outside_session_window():
    result = evaluate_session_restrictions(
        current_time=datetime(2026, 4, 9, 6, 30, tzinfo=UTC),
        allowed_window=("08:00", "16:00"),
    )

    assert result.allowed is False
    assert result.reason_codes == ("outside_session_window",)


def test_evaluate_session_restrictions_blocks_active_blackout_window():
    result = evaluate_session_restrictions(
        current_time=datetime(2026, 4, 9, 10, 15, tzinfo=UTC),
        allowed_window=("08:00", "16:00"),
        blackout_windows=(("10:00", "10:30"),),
    )

    assert result.allowed is False
    assert result.reason_codes == ("active_blackout_window",)


def test_evaluate_spread_slippage_precheck_reports_threshold_failures():
    result = evaluate_spread_slippage_precheck(
        spread_points=3.0,
        max_spread_points=2.0,
        expected_slippage_points=1.5,
        max_slippage_points=1.0,
    )

    assert result.allowed is False
    assert result.reason_codes == (
        "spread_threshold_exceeded",
        "slippage_threshold_exceeded",
    )


def test_evaluate_operating_mode_compatibility_blocks_mode_mismatch():
    result = evaluate_operating_mode_compatibility(
        workflow_operating_mode="MODE-004",
        allowed_operating_modes=("MODE-001", "MODE-002"),
    )

    assert result.allowed is False
    assert result.reason_codes == ("operating_mode_not_allowed",)


def test_evaluate_compliance_profile_compatibility_blocks_disallowed_profile():
    result = evaluate_compliance_profile_compatibility(
        active_compliance_profile_id="uae_enterprise",
        allowed_compliance_profile_ids=("internal_non_regulated",),
    )

    assert result.allowed is False
    assert result.reason_codes == ("compliance_profile_not_allowed",)
