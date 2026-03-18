"""Backend Edge Lab scorecard builder for automation and snapshot runs."""

from __future__ import annotations

from typing import Any, Dict, Iterable, List, Optional

SCORECARD_SPEC_VERSION = "edge_lab_scorecard_v1"


def _clamp(value: float, lo: float = 0.0, hi: float = 100.0) -> float:
    return max(lo, min(hi, value))


def _mean(values: Iterable[Optional[float]]) -> float:
    clean = [float(value) for value in values if value is not None]
    if not clean:
        return 0.0
    return sum(clean) / len(clean)


def _normalize(value: Optional[float], lo: float, hi: float) -> float:
    if value is None or hi <= lo:
        return 0.0
    return _clamp(((value - lo) / (hi - lo)) * 100.0)


def _score_confidence(value: float) -> str:
    if value >= 70:
        return "High"
    if value >= 45:
        return "Moderate"
    return "Low"


def _warning_if(condition: bool, text: str) -> List[str]:
    return [text] if condition else []


def _input_label(key: str) -> str:
    return key.replace("_", " ")


def _build_dynamic_rationale(
    base: str,
    inputs: Dict[str, Optional[float]],
    warnings: List[str],
) -> str:
    ranked = sorted(
        [(key, value) for key, value in inputs.items() if value is not None],
        key=lambda item: item[1],
        reverse=True,
    )
    strongest = [f"{_input_label(key)} {value:.1f}" for key, value in ranked[:2]]
    weakest = ranked[-1] if ranked else None

    parts = [base]
    if strongest:
        parts.append(f"Strongest inputs: {', '.join(strongest)}.")
    if weakest is not None:
        parts.append(f"Weakest input: {_input_label(weakest[0])} {weakest[1]:.1f}.")
    if warnings:
        parts.append(f"Main warning: {warnings[0]}")
    return " ".join(parts)


def _derive_tradeability(dataset: Dict[str, Any]) -> Optional[Dict[str, float]]:
    rows = list(dataset.get("rows") or [])
    schema = dict(dataset.get("schema") or {})
    spread_key = str(schema.get("spread") or "Spread")
    if not rows:
        return None

    spread_pips: List[float] = []
    range_pips: List[float] = []
    rollover_spread_pips: List[float] = []
    active_flags: List[float] = []

    for row in rows:
        range_value = row.get("range_pips")
        spread_value = row.get(spread_key)
        point_size = row.get("point_size")
        pip_size = row.get("pip_size")

        if isinstance(range_value, (int, float)) and range_value > 0:
            range_pips.append(float(range_value))
            active_flags.append(1.0 if range_value >= 5 else 0.0)

        if (
            isinstance(spread_value, (int, float))
            and isinstance(point_size, (int, float))
            and isinstance(pip_size, (int, float))
            and pip_size > 0
        ):
            spread_in_pips = (float(spread_value) * float(point_size)) / float(pip_size)
            spread_pips.append(spread_in_pips)
            if row.get("is_rollover_hour") is True:
                rollover_spread_pips.append(spread_in_pips)

    avg_spread_pips = _mean(spread_pips)
    avg_range_pips = _mean(range_pips)
    spread_to_range = (
        avg_spread_pips / avg_range_pips if avg_spread_pips > 0 and avg_range_pips > 0 else None
    )
    rollover_spread = _mean(rollover_spread_pips)
    active_rate = _mean(active_flags)

    friction_score = 0.0 if spread_to_range is None else _clamp(100 - ((spread_to_range - 0.05) / 0.2) * 100)
    activity_score = _clamp(active_rate * 100)
    rollover_penalty = (
        _clamp(100 - (((rollover_spread / avg_spread_pips) - 1) / 2) * 100)
        if avg_spread_pips > 0 and rollover_spread > 0
        else 50.0
    )
    volatility_adjusted_burden = (
        (avg_spread_pips / max(1.0, avg_range_pips)) * 100
        if avg_spread_pips > 0 and avg_range_pips > 0
        else None
    )
    tradability_score = _mean(
        [
            friction_score,
            activity_score,
            rollover_penalty,
            None if volatility_adjusted_burden is None else 100 - min(100, volatility_adjusted_burden),
        ]
    )
    return {
        "frictionScore": friction_score,
        "activityScore": activity_score,
        "rolloverPenalty": rollover_penalty,
        "volatilityAdjustedBurden": volatility_adjusted_burden or 0.0,
        "tradabilityScore": tradability_score,
    }


def _derive_readiness(
    *,
    dataset: Dict[str, Any],
    core_metric_profile: Dict[str, Any],
    market_summary: Dict[str, Any],
    overall_confidence: str,
) -> Dict[str, Any]:
    reasons: List[str] = []
    row_count = int((dataset.get("meta") or {}).get("n_rows") or 0)
    warning_count = int((core_metric_profile.get("summary") or {}).get("warning_count") or 0)

    if row_count < 50:
        reasons.append("short_history")
    if market_summary.get("is_valid") is False:
        reasons.append("market_structure_invalid")
    if float(market_summary.get("decision_confidence_score") or 0.0) < 35.0:
        reasons.append("low_decision_confidence")
    if overall_confidence == "Low":
        reasons.append("low_scorecard_confidence")
    if warning_count > 0:
        reasons.append("data_warnings_present")

    if row_count < 50:
        label = "INSUFFICIENT_SAMPLE"
    elif any(reason in reasons for reason in ("market_structure_invalid", "low_decision_confidence", "low_scorecard_confidence")):
        label = "USE_WITH_CAUTION"
    else:
        label = "RESEARCH_READY"

    return {
        "research_ready": label == "RESEARCH_READY",
        "readiness_label": label,
        "readiness_reasons": reasons,
    }


def build_edge_lab_scorecard_report(
    *,
    dataset: Dict[str, Any],
    core_metric_profile: Dict[str, Any],
    seasonality_result: Dict[str, Any],
    market_structure_profile: Dict[str, Any],
    stability: Optional[Dict[str, Any]] = None,
    robustness: Optional[Dict[str, Any]] = None,
) -> Optional[Dict[str, Any]]:
    """Build a deterministic backend scorecard report from progressive Edge Lab outputs."""
    if not dataset or not core_metric_profile or not seasonality_result or not market_structure_profile:
        return None

    tradeability = _derive_tradeability(dataset)
    summary = dict(market_structure_profile.get("summary") or {})
    breakout = dict(summary.get("breakout_analysis") or {})
    regime_inputs = dict(summary.get("regime_score_inputs") or {})

    session_summary = list(seasonality_result.get("session_summary") or [])
    opportunity_windows = dict(seasonality_result.get("opportunity_windows") or {})

    best_session = float((opportunity_windows.get("best_sessions") or [{}])[0].get("opportunity_score") or 0.0)
    best_hour = float((opportunity_windows.get("best_hours") or [{}])[0].get("opportunity_score") or 0.0)
    avg_session_opportunity = _mean(
        [row.get("opportunity_score") for row in session_summary if isinstance(row, dict)]
    )

    stability_agreement = (
        float(stability.get("agreement_rate") or 0.0) * 100
        if stability
        else float(summary.get("decision_confidence_score") or 0.0)
    )
    robustness_agreement = (
        float(robustness.get("verdict_agreement_rate") or 0.0) * 100
        if robustness
        else float(summary.get("decision_confidence_score") or 0.0)
    )

    trendability = _mean(
        [
            summary.get("trend_bias_score"),
            summary.get("trend_confidence_score"),
            float(summary.get("breakout_follow_probability") or 0.0) * 100,
            float(summary.get("continuation_after_pullback_rate") or 0.0) * 100,
            float(regime_inputs.get("favorable_breakout_regime_share") or 0.0) * 100,
        ]
    )
    noise = _mean(
        [
            summary.get("chop_score"),
            float(summary.get("whipsaw_rate") or 0.0) * 100,
            float(summary.get("false_break_frequency") or 0.0) * 100,
            float(regime_inputs.get("low_liquidity_share") or 0.0) * 100,
        ]
    )
    cost_efficiency = _mean(
        [
            None if tradeability is None else tradeability["frictionScore"],
            None if tradeability is None else tradeability["rolloverPenalty"],
            None
            if tradeability is None
            else 100 - min(100, float(tradeability.get("volatilityAdjustedBurden") or 0.0)),
        ]
    )
    mean_reversion = _mean(
        [
            summary.get("reversion_bias_score"),
            summary.get("reversion_confidence_score"),
            float(summary.get("reentry_probability") or 0.0) * 100,
            float(summary.get("zscore_reentry_rate") or 0.0) * 100,
            float(summary.get("band_reentry_rate") or 0.0) * 100,
            float(regime_inputs.get("favorable_reversion_regime_share") or 0.0) * 100,
        ]
    )
    breakout_quality = _mean(
        [
            float(summary.get("breakout_follow_probability") or 0.0) * 100,
            100 - (float(summary.get("false_break_frequency") or 0.0) * 100),
            float(breakout.get("retest_success_rate") or 0.0) * 100,
            _normalize(breakout.get("extension_behavior", {}).get("avg_extension_pips"), 2, 20),
        ]
    )
    session_opportunity = _mean([best_session, best_hour, avg_session_opportunity])
    stability_score = _mean(
        [
            float(summary.get("decision_confidence_score") or 0.0),
            stability_agreement,
            robustness_agreement,
        ]
    )
    tradability = 0.0 if tradeability is None else float(tradeability.get("tradabilityScore") or 0.0)

    rows: List[Dict[str, Any]] = [
        {
            "key": "trendability",
            "label": "Trendability Score",
            "score": trendability,
            "confidence": _score_confidence(float(summary.get("trend_confidence_score") or 0.0)),
            "explanation": "Combines trend bias, trend confidence, follow-through, pullback continuation, and favorable breakout regime share.",
            "inputs": {
                "trend_bias": summary.get("trend_bias_score"),
                "trend_confidence": summary.get("trend_confidence_score"),
                "breakout_follow_through": float(summary.get("breakout_follow_probability") or 0.0) * 100,
                "continuation_after_pullback": float(summary.get("continuation_after_pullback_rate") or 0.0) * 100,
            },
        },
        {
            "key": "noise",
            "label": "Noise Score",
            "score": noise,
            "confidence": _score_confidence(100 - noise),
            "explanation": "Higher means more chop, whipsaw, false-break pressure, and low-liquidity disturbance.",
            "inputs": {
                "chop": summary.get("chop_score"),
                "whipsaw_rate": float(summary.get("whipsaw_rate") or 0.0) * 100,
                "false_break_frequency": float(summary.get("false_break_frequency") or 0.0) * 100,
                "low_liquidity_share": float(regime_inputs.get("low_liquidity_share") or 0.0) * 100,
            },
        },
        {
            "key": "cost_efficiency",
            "label": "Cost Efficiency Score",
            "score": cost_efficiency,
            "confidence": _score_confidence(cost_efficiency),
            "explanation": "Focuses on friction only: spread burden, rollover burden, and volatility-adjusted cost.",
            "inputs": {
                "friction": None if tradeability is None else tradeability["frictionScore"],
                "rollover": None if tradeability is None else tradeability["rolloverPenalty"],
                "vol_adj_cost": None if tradeability is None else tradeability["volatilityAdjustedBurden"],
            },
        },
        {
            "key": "mean_reversion",
            "label": "Mean Reversion Score",
            "score": mean_reversion,
            "confidence": _score_confidence(float(summary.get("reversion_confidence_score") or 0.0)),
            "explanation": "Combines reversion bias, reversion confidence, reentry behavior, and favorable reversion regime share.",
            "inputs": {
                "reversion_bias": summary.get("reversion_bias_score"),
                "reversion_confidence": summary.get("reversion_confidence_score"),
                "reentry_probability": float(summary.get("reentry_probability") or 0.0) * 100,
                "zscore_reentry": float(summary.get("zscore_reentry_rate") or 0.0) * 100,
            },
        },
        {
            "key": "breakout_quality",
            "label": "Breakout Quality Score",
            "score": breakout_quality,
            "confidence": _score_confidence(breakout_quality),
            "explanation": "Measures whether breaks tend to continue, survive retests, and extend enough to be strategy-useful.",
            "inputs": {
                "follow_through": float(summary.get("breakout_follow_probability") or 0.0) * 100,
                "inverse_failure": 100 - (float(summary.get("false_break_frequency") or 0.0) * 100),
                "retest_success": float(breakout.get("retest_success_rate") or 0.0) * 100,
                "extension": _normalize(breakout.get("extension_behavior", {}).get("avg_extension_pips"), 2, 20),
            },
        },
        {
            "key": "session_opportunity",
            "label": "Session Opportunity Score",
            "score": session_opportunity,
            "confidence": _score_confidence(session_opportunity),
            "explanation": "Uses the best session, best hour, and average session opportunity from Seasonality.",
            "inputs": {
                "best_session": best_session,
                "best_hour": best_hour,
                "avg_session_opportunity": avg_session_opportunity,
            },
        },
        {
            "key": "stability",
            "label": "Stability Score",
            "score": stability_score,
            "confidence": _score_confidence(stability_score),
            "explanation": "Combines decision confidence with any available stability and robustness snapshots.",
            "inputs": {
                "decision_confidence": summary.get("decision_confidence_score"),
                "stability_agreement": stability_agreement if stability else None,
                "robustness_agreement": robustness_agreement if robustness else None,
            },
        },
        {
            "key": "tradability",
            "label": "Tradability Score",
            "score": tradability,
            "confidence": _score_confidence(tradability),
            "explanation": "Composite execution friendliness using friction, activity, rollover, and volatility-adjusted burden.",
            "inputs": {
                "tradability": tradability,
                "friction": None if tradeability is None else tradeability["frictionScore"],
                "activity": None if tradeability is None else tradeability["activityScore"],
                "rollover": None if tradeability is None else tradeability["rolloverPenalty"],
            },
        },
    ]

    strategy_candidates: List[Dict[str, Any]] = [
        {
            "archetype": "Trend Breakout",
            "fitScore": _mean(
                [
                    summary.get("trend_bias_score"),
                    summary.get("trend_confidence_score"),
                    float(summary.get("breakout_follow_probability") or 0.0) * 100,
                    float(breakout.get("retest_success_rate") or 0.0) * 100,
                    float(regime_inputs.get("favorable_breakout_regime_share") or 0.0) * 100,
                ]
            ),
            "warnings": [
                *_warning_if(float(summary.get("false_break_frequency") or 0.0) >= 0.45, "False-break frequency is elevated."),
                *_warning_if(float(summary.get("whipsaw_rate") or 0.0) >= 0.35, "Whipsaw pressure can degrade breakout entries."),
                *_warning_if((tradeability or {}).get("frictionScore", 0.0) < 45, "Execution friction is high for breakout-style entries."),
            ],
            "antiFitConditions": [
                *_warning_if(float(summary.get("reversion_bias_score") or 0.0) > float(summary.get("trend_bias_score") or 0.0), "Reversion bias currently dominates trend bias."),
            ],
            "inputs": {
                "trend_bias": summary.get("trend_bias_score"),
                "breakout_follow": float(summary.get("breakout_follow_probability") or 0.0) * 100,
                "retest_success": float(breakout.get("retest_success_rate") or 0.0) * 100,
                "breakout_regime_share": float(regime_inputs.get("favorable_breakout_regime_share") or 0.0) * 100,
            },
            "base": "Best when trend bias is strong, breakouts follow through, and the favorable breakout regime share is high.",
        },
        {
            "archetype": "Trend Pullback Continuation",
            "fitScore": _mean(
                [
                    summary.get("trend_bias_score"),
                    summary.get("trend_confidence_score"),
                    float(summary.get("continuation_after_pullback_rate") or 0.0) * 100,
                    _normalize(summary.get("pullback_leg_count"), 2, 20),
                    stability_agreement,
                ]
            ),
            "warnings": [
                *_warning_if(float(summary.get("continuation_after_pullback_rate") or 0.0) < 0.45, "Pullback continuation rate is weak."),
                *_warning_if(float(summary.get("pullback_leg_count") or 0.0) < 3, "Pullback sample is thin."),
            ],
            "antiFitConditions": [
                *_warning_if(float(summary.get("chop_score") or 0.0) >= 60, "High chop can make pullback structure unreliable."),
            ],
            "inputs": {
                "trend_bias": summary.get("trend_bias_score"),
                "continuation_after_pullback": float(summary.get("continuation_after_pullback_rate") or 0.0) * 100,
                "pullback_count": summary.get("pullback_leg_count"),
                "stability": stability_agreement,
            },
            "base": "Best when the dominant trend survives pullbacks and continuation after pullback stays strong.",
        },
        {
            "archetype": "Mean Reversion Fade",
            "fitScore": _mean(
                [
                    summary.get("reversion_bias_score"),
                    summary.get("reversion_confidence_score"),
                    float(summary.get("zscore_reentry_rate") or 0.0) * 100,
                    float(summary.get("band_reentry_rate") or 0.0) * 100,
                    float(regime_inputs.get("favorable_reversion_regime_share") or 0.0) * 100,
                ]
            ),
            "warnings": [
                *_warning_if(float(summary.get("breakout_follow_probability") or 0.0) >= 0.55, "Breakout continuation is strong enough to punish fades."),
                *_warning_if((tradeability or {}).get("frictionScore", 0.0) < 50, "Costs may consume short-horizon mean-reversion edges."),
            ],
            "antiFitConditions": [
                *_warning_if(float(summary.get("trend_bias_score") or 0.0) >= 60, "Trend bias is too strong for a pure mean-reversion fade."),
            ],
            "inputs": {
                "reversion_bias": summary.get("reversion_bias_score"),
                "zscore_reentry": float(summary.get("zscore_reentry_rate") or 0.0) * 100,
                "band_reentry": float(summary.get("band_reentry_rate") or 0.0) * 100,
                "favorable_reversion_regime_share": float(regime_inputs.get("favorable_reversion_regime_share") or 0.0) * 100,
            },
            "base": "Best when deviations snap back quickly, reentry behavior is frequent, and reversion-favorable regimes dominate.",
        },
        {
            "archetype": "Range Reversion",
            "fitScore": _mean(
                [
                    summary.get("reversion_bias_score"),
                    float(summary.get("reentry_probability") or 0.0) * 100,
                    float(summary.get("false_break_frequency") or 0.0) * 100,
                    _normalize(summary.get("range_duration_bars"), 3, 30),
                    float(breakout.get("retest_success_rate") or 0.0) * 100,
                ]
            ),
            "warnings": [
                *_warning_if(float(summary.get("range_duration_bars") or 0.0) < 4, "Detected ranges are short-lived."),
                *_warning_if(float(summary.get("breakout_follow_probability") or 0.0) > 0.55, "Breakout follow-through is too strong for comfortable range fading."),
            ],
            "antiFitConditions": [
                *_warning_if(float(summary.get("trend_confidence_score") or 0.0) > float(summary.get("reversion_confidence_score") or 0.0) + 15, "Trend confidence dominates reversion confidence."),
            ],
            "inputs": {
                "reversion_bias": summary.get("reversion_bias_score"),
                "reentry_probability": float(summary.get("reentry_probability") or 0.0) * 100,
                "false_break_frequency": float(summary.get("false_break_frequency") or 0.0) * 100,
                "range_duration": summary.get("range_duration_bars"),
            },
            "base": "Best when ranges persist, breakouts fail, and price reenters instead of extending cleanly.",
        },
        {
            "archetype": "Session Breakout",
            "fitScore": _mean(
                [
                    best_session,
                    best_hour,
                    summary.get("trend_bias_score"),
                    float(summary.get("breakout_follow_probability") or 0.0) * 100,
                    None if tradeability is None else tradeability["frictionScore"],
                ]
            ),
            "warnings": [
                *_warning_if(best_session < 55, "Seasonality does not show a clearly strong breakout session."),
                *_warning_if((tradeability or {}).get("frictionScore", 0.0) < 45, "Session breakout edge may be eroded by spread burden."),
            ],
            "antiFitConditions": [
                *_warning_if(float(summary.get("chop_score") or 0.0) >= 65, "High chop undermines clean session breakout execution."),
            ],
            "inputs": {
                "best_session_opportunity": best_session,
                "best_hour_opportunity": best_hour,
                "breakout_follow": float(summary.get("breakout_follow_probability") or 0.0) * 100,
                "friction": None if tradeability is None else tradeability["frictionScore"],
            },
            "base": "Best when seasonality shows obvious opportunity windows and breakout behavior is still structurally supportive.",
        },
        {
            "archetype": "Intraday Scalping",
            "fitScore": _mean(
                [
                    avg_session_opportunity,
                    None if tradeability is None else tradeability["frictionScore"],
                    None if tradeability is None else tradeability["activityScore"],
                    100 - float(summary.get("chop_score") or 0.0),
                ]
            ),
            "warnings": [
                *_warning_if((tradeability or {}).get("frictionScore", 0.0) < 60, "Spread burden is high for scalping."),
                *_warning_if((tradeability or {}).get("activityScore", 0.0) < 45, "Intraday activity is inconsistent."),
            ],
            "antiFitConditions": [
                *_warning_if(float((opportunity_windows.get("dead_sessions") or [{}])[0].get("opportunity_score") or 0.0) > 40, "Low-opportunity windows are not clearly separated from better windows."),
            ],
            "inputs": {
                "avg_session_opportunity": avg_session_opportunity,
                "friction": None if tradeability is None else tradeability["frictionScore"],
                "activity": None if tradeability is None else tradeability["activityScore"],
                "inverse_noise": 100 - float(summary.get("chop_score") or 0.0),
            },
            "base": "Best when intraday opportunity is broad, activity is stable, and friction is low enough for smaller targets.",
        },
        {
            "archetype": "Swing Trend Following",
            "fitScore": _mean(
                [
                    summary.get("trend_bias_score"),
                    summary.get("trend_confidence_score"),
                    stability_agreement,
                    robustness_agreement,
                    _normalize(((breakout.get("extension_behavior") or {}).get("p75_extension_pips")), 5, 35),
                ]
            ),
            "warnings": [
                *_warning_if(stability_agreement < 55, "Trend read is not stable enough across subperiods."),
                *_warning_if(robustness_agreement < 55, "Trend read is sensitive to nearby parameter changes."),
            ],
            "antiFitConditions": [
                *_warning_if(float(summary.get("reversion_bias_score") or 0.0) >= 60, "Reversion bias remains too strong for comfortable swing trend holding."),
            ],
            "inputs": {
                "trend_bias": summary.get("trend_bias_score"),
                "trend_confidence": summary.get("trend_confidence_score"),
                "stability": stability_agreement,
                "robustness": robustness_agreement,
            },
            "base": "Best when trend bias is stable across blocks and nearby parameter changes, with enough extension to hold swings.",
        },
        {
            "archetype": "Volatility Expansion",
            "fitScore": _mean(
                [
                    float(summary.get("breakout_follow_probability") or 0.0) * 100,
                    _normalize(summary.get("range_height_pips"), 5, 50),
                    _normalize(((breakout.get("extension_behavior") or {}).get("avg_extension_pips")), 2, 25),
                    float(regime_inputs.get("high_vol_trend_share") or 0.0) * 100,
                ]
            ),
            "warnings": [
                *_warning_if(float(summary.get("false_break_frequency") or 0.0) >= 0.40, "Too many breaks still fail for a clean expansion profile."),
                *_warning_if((tradeability or {}).get("rolloverPenalty", 0.0) < 45, "Volatility-expansion trades may be hurt by rollover friction."),
            ],
            "antiFitConditions": [
                *_warning_if(float(regime_inputs.get("high_vol_trend_share") or 0.0) < 0.20, "High-volatility trend regimes are too rare."),
            ],
            "inputs": {
                "breakout_follow": float(summary.get("breakout_follow_probability") or 0.0) * 100,
                "range_height": summary.get("range_height_pips"),
                "avg_extension": ((breakout.get("extension_behavior") or {}).get("avg_extension_pips")),
                "high_vol_trend_share": float(regime_inputs.get("high_vol_trend_share") or 0.0) * 100,
            },
            "base": "Best when high-vol trend regimes are frequent and breakout extensions are large enough to exploit expansion moves.",
        },
    ]

    ranked_fit: List[Dict[str, Any]] = []
    for candidate in sorted(strategy_candidates, key=lambda row: row["fitScore"], reverse=True):
        ranked_fit.append(
            {
                "archetype": candidate["archetype"],
                "fitScore": candidate["fitScore"],
                "rationale": _build_dynamic_rationale(candidate["base"], candidate["inputs"], candidate["warnings"]),
                "warnings": candidate["warnings"],
                "antiFitConditions": candidate["antiFitConditions"],
                "inputs": candidate["inputs"],
            }
        )

    final_score = _mean(
        [
            max(trendability, mean_reversion),
            breakout_quality,
            session_opportunity,
            cost_efficiency,
            tradability,
            stability_score,
            100 - noise,
        ]
    )
    final_label = "Low Opportunity"
    if final_score >= 70:
        final_label = "High Opportunity"
    elif final_score >= 45:
        final_label = "Moderate Opportunity"
    overall_confidence = _score_confidence(_mean([row["score"] for row in rows]))
    readiness = _derive_readiness(
        dataset=dataset,
        core_metric_profile=core_metric_profile,
        market_summary=summary,
        overall_confidence=overall_confidence,
    )

    return {
        "rows": rows,
        "finalScore": final_score,
        "finalLabel": final_label,
        "overallConfidence": overall_confidence,
        "scoreSpecVersion": SCORECARD_SPEC_VERSION,
        **readiness,
        "strategyFit": {
            "primary": ranked_fit[0] if ranked_fit else None,
            "ranked": ranked_fit,
        },
    }
