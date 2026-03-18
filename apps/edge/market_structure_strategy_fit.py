"""Strategy-fit mapping for Market Structure outputs."""

from __future__ import annotations

from typing import Any, Dict, List


def _bounded(value: float) -> float:
    return max(0.0, min(100.0, float(value)))


def build_strategy_fit(summary: Dict[str, Any]) -> Dict[str, Any]:
    trend_bias = float(summary.get("trend_bias_score") or 0.0)
    reversion_bias = float(summary.get("reversion_bias_score") or 0.0)
    chop_score = float(summary.get("chop_score") or 0.0)
    trend_confidence = float(summary.get("trend_confidence_score") or 0.0)
    reversion_confidence = float(summary.get("reversion_confidence_score") or 0.0)
    continuation = float(summary.get("continuation_after_pullback_rate") or 0.0) * 100.0
    breakout_follow = float(summary.get("breakout_follow_probability") or 0.0) * 100.0
    false_break = float(summary.get("false_break_frequency") or 0.0) * 100.0
    reentry = float(summary.get("reentry_probability") or 0.0) * 100.0
    whipsaw = float(summary.get("whipsaw_rate") or 0.0) * 100.0
    zscore_reentry = float(summary.get("zscore_reentry_rate") or 0.0) * 100.0

    candidates: List[Dict[str, Any]] = [
        {
            "archetype": "breakout_trend_following",
            "fit_score": _bounded(trend_bias * 0.55 + trend_confidence * 0.20 + breakout_follow * 0.25 - chop_score * 0.20),
            "rationale": "Best when trend bias is strong and breakouts continue cleanly.",
        },
        {
            "archetype": "pullback_continuation",
            "fit_score": _bounded(trend_bias * 0.45 + trend_confidence * 0.20 + continuation * 0.25 + breakout_follow * 0.10 - chop_score * 0.15),
            "rationale": "Best when pullbacks resolve back into the dominant trend.",
        },
        {
            "archetype": "range_fade",
            "fit_score": _bounded(reversion_bias * 0.45 + reversion_confidence * 0.20 + false_break * 0.15 + reentry * 0.20 - trend_bias * 0.10),
            "rationale": "Best when breakouts frequently fail and price returns into the range.",
        },
        {
            "archetype": "mean_reversion_fade",
            "fit_score": _bounded(reversion_bias * 0.40 + reversion_confidence * 0.20 + zscore_reentry * 0.25 + false_break * 0.15 - trend_bias * 0.10),
            "rationale": "Best when deviations tend to snap back quickly toward the mean.",
        },
        {
            "archetype": "avoid_choppy_conditions",
            "fit_score": _bounded(chop_score * 0.55 + whipsaw * 0.25 + (100.0 - max(trend_bias, reversion_bias)) * 0.20),
            "rationale": "Best when both trend and reversion edge are weak relative to chop and whipsaw.",
        },
    ]

    candidates.sort(key=lambda item: float(item["fit_score"]), reverse=True)
    return {
        "primary": candidates[0] if candidates else None,
        "alternatives": candidates[1:3],
        "all": candidates,
    }
