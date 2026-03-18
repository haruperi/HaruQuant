"""Top-level calibration helpers for Market Structure verdict thresholds."""

from __future__ import annotations

from dataclasses import asdict, dataclass
from itertools import product
from typing import Any, Dict, Iterable, List, Sequence


@dataclass(frozen=True)
class MarketStructureCalibrationCandidate:
    bias_verdict_min_gap: float
    trend_confidence_min: float
    reversion_confidence_min: float
    reversion_score_weight: float
    chop_score_weight: float

    def to_dict(self) -> Dict[str, float]:
        return asdict(self)


def classify_with_candidate(
    *,
    trend_bias_score: float,
    reversion_bias_score: float,
    trend_confidence_score: float,
    reversion_confidence_score: float,
    candidate: MarketStructureCalibrationCandidate,
) -> str:
    if trend_bias_score - reversion_bias_score >= candidate.bias_verdict_min_gap:
        if trend_confidence_score < candidate.trend_confidence_min:
            return "MIXED"
        return "TREND_BIASED"
    if reversion_bias_score - trend_bias_score >= candidate.bias_verdict_min_gap:
        if reversion_confidence_score < candidate.reversion_confidence_min:
            return "MIXED"
        return "REVERSION_BIASED"
    return "MIXED"


def build_calibration_grid() -> List[MarketStructureCalibrationCandidate]:
    gap_options: Sequence[float] = (10.0, 15.0, 20.0)
    trend_conf_options: Sequence[float] = (30.0, 35.0, 40.0)
    reversion_conf_options: Sequence[float] = (30.0, 35.0, 40.0)
    reversion_weight_options: Sequence[float] = (0.65, 0.75, 0.85)
    candidates: List[MarketStructureCalibrationCandidate] = []

    for gap, trend_conf, reversion_conf, reversion_weight in product(
        gap_options,
        trend_conf_options,
        reversion_conf_options,
        reversion_weight_options,
    ):
        chop_weight = 1.0 - reversion_weight
        candidates.append(
            MarketStructureCalibrationCandidate(
                bias_verdict_min_gap=gap,
                trend_confidence_min=trend_conf,
                reversion_confidence_min=reversion_conf,
                reversion_score_weight=reversion_weight,
                chop_score_weight=chop_weight,
            )
        )
    return candidates


def evaluate_calibration_candidates(
    run_rows: Iterable[Dict[str, Any]],
    validation_rows: Iterable[Dict[str, Any]],
) -> Dict[str, Any]:
    validation_map = {
        int(row["run_id"]): row
        for row in validation_rows
        if row.get("realized_verdict") and row.get("realized_verdict") != "INSUFFICIENT_DATA"
    }
    candidates = build_calibration_grid()
    results: List[Dict[str, Any]] = []

    for candidate in candidates:
        evaluated = 0
        matched = 0
        trend_hits = 0
        reversion_hits = 0
        mixed_hits = 0

        for run in run_rows:
            run_id = int(run.get("run_id") or 0)
            validation = validation_map.get(run_id)
            if not validation:
                continue
            summary = run.get("summary") or {}
            trend_bias_base = float(summary.get("trend_bias_score") or 0.0)
            reversion_score = float(summary.get("reversion_score") or summary.get("reversion_bias_score") or 0.0)
            chop_score = float(summary.get("chop_score") or 0.0)
            reversion_confidence = float(summary.get("reversion_confidence_score") or 0.0)
            reversion_mix = (
                reversion_score * candidate.reversion_score_weight
                + chop_score * candidate.chop_score_weight
            ) / max(1e-9, candidate.reversion_score_weight + candidate.chop_score_weight)
            reversion_bias = reversion_mix * (reversion_confidence / 100.0)

            predicted = classify_with_candidate(
                trend_bias_score=trend_bias_base,
                reversion_bias_score=reversion_bias,
                trend_confidence_score=float(summary.get("trend_confidence_score") or 0.0),
                reversion_confidence_score=reversion_confidence,
                candidate=candidate,
            )
            realized = str(validation.get("realized_verdict") or "MIXED")
            evaluated += 1
            if predicted == realized:
                matched += 1
            if predicted == "TREND_BIASED" and realized == "TREND_BIASED":
                trend_hits += 1
            elif predicted == "REVERSION_BIASED" and realized == "REVERSION_BIASED":
                reversion_hits += 1
            elif predicted == "MIXED" and realized == "MIXED":
                mixed_hits += 1

        accuracy = matched / evaluated if evaluated else 0.0
        results.append(
            {
                "settings": candidate.to_dict(),
                "evaluated_runs": evaluated,
                "matched_runs": matched,
                "accuracy": accuracy,
                "trend_hits": trend_hits,
                "reversion_hits": reversion_hits,
                "mixed_hits": mixed_hits,
            }
        )

    results.sort(
        key=lambda item: (
            float(item.get("accuracy") or 0.0),
            int(item.get("matched_runs") or 0),
            -float((item.get("settings") or {}).get("bias_verdict_min_gap") or 0.0),
        ),
        reverse=True,
    )
    return {
        "total_candidates": len(results),
        "best": results[0] if results else None,
        "rows": results[:10],
    }

