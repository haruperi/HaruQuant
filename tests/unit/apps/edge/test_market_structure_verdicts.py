from __future__ import annotations

from backend.services.research.market_structure import _final_verdict


def test_final_verdict_returns_trend_biased_when_gap_and_confidence_clear_thresholds():
    verdict = _final_verdict(
        62.0,
        30.0,
        55.0,
        40.0,
        bias_verdict_min_gap=15.0,
        trend_confidence_min=35.0,
        reversion_confidence_min=35.0,
    )
    assert verdict == "TREND_BIASED"


def test_final_verdict_returns_reversion_biased_when_gap_and_confidence_clear_thresholds():
    verdict = _final_verdict(
        18.0,
        48.0,
        50.0,
        60.0,
        bias_verdict_min_gap=15.0,
        trend_confidence_min=35.0,
        reversion_confidence_min=35.0,
    )
    assert verdict == "REVERSION_BIASED"


def test_final_verdict_returns_mixed_when_gap_is_too_small():
    verdict = _final_verdict(
        42.0,
        33.0,
        70.0,
        70.0,
        bias_verdict_min_gap=15.0,
        trend_confidence_min=35.0,
        reversion_confidence_min=35.0,
    )
    assert verdict == "MIXED"


def test_final_verdict_returns_mixed_when_trend_confidence_is_too_low():
    verdict = _final_verdict(
        60.0,
        20.0,
        25.0,
        80.0,
        bias_verdict_min_gap=15.0,
        trend_confidence_min=35.0,
        reversion_confidence_min=35.0,
    )
    assert verdict == "MIXED"


def test_final_verdict_returns_mixed_when_reversion_confidence_is_too_low():
    verdict = _final_verdict(
        12.0,
        55.0,
        80.0,
        20.0,
        bias_verdict_min_gap=15.0,
        trend_confidence_min=35.0,
        reversion_confidence_min=35.0,
    )
    assert verdict == "MIXED"
