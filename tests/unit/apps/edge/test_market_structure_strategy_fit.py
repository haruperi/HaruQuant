from __future__ import annotations

from haruquant.research import build_strategy_fit


def test_strategy_fit_prefers_breakout_when_trend_signals_dominate():
    fit = build_strategy_fit(
        {
            "trend_bias_score": 80.0,
            "trend_confidence_score": 70.0,
            "reversion_bias_score": 20.0,
            "reversion_confidence_score": 25.0,
            "chop_score": 15.0,
            "continuation_after_pullback_rate": 0.75,
            "breakout_follow_probability": 0.70,
            "false_break_frequency": 0.10,
            "reentry_probability": 0.15,
            "whipsaw_rate": 0.10,
            "zscore_reentry_rate": 0.20,
        }
    )
    assert fit["primary"]["archetype"] in {"breakout_trend_following", "pullback_continuation"}


def test_strategy_fit_prefers_reversion_when_range_signals_dominate():
    fit = build_strategy_fit(
        {
            "trend_bias_score": 18.0,
            "trend_confidence_score": 20.0,
            "reversion_bias_score": 75.0,
            "reversion_confidence_score": 70.0,
            "chop_score": 25.0,
            "continuation_after_pullback_rate": 0.25,
            "breakout_follow_probability": 0.15,
            "false_break_frequency": 0.65,
            "reentry_probability": 0.70,
            "whipsaw_rate": 0.20,
            "zscore_reentry_rate": 0.68,
        }
    )
    assert fit["primary"]["archetype"] in {"range_fade", "mean_reversion_fade"}


def test_strategy_fit_prefers_avoid_when_chop_is_dominant():
    fit = build_strategy_fit(
        {
            "trend_bias_score": 15.0,
            "trend_confidence_score": 20.0,
            "reversion_bias_score": 22.0,
            "reversion_confidence_score": 20.0,
            "chop_score": 85.0,
            "continuation_after_pullback_rate": 0.15,
            "breakout_follow_probability": 0.20,
            "false_break_frequency": 0.35,
            "reentry_probability": 0.30,
            "whipsaw_rate": 0.75,
            "zscore_reentry_rate": 0.25,
        }
    )
    assert fit["primary"]["archetype"] == "avoid_choppy_conditions"
