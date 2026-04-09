from __future__ import annotations

from datetime import datetime, timezone

from backend.services.risk import evaluate_regime_restriction
from backend.services.risk import evaluate_session_restrictions


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
