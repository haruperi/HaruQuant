from __future__ import annotations

from backend.services.risk import evaluate_regime_restriction


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
