"""Lower-level metric-band calibration helpers for Market Structure."""

from __future__ import annotations

from dataclasses import asdict, dataclass
from itertools import product
from typing import Any, Dict, Iterable, List, Sequence

from services.research.config import MarketStructureConfig


def _normalize_0_100(value: Any, lo: float, hi: float) -> float:
    try:
        number = float(value)
    except (TypeError, ValueError):
        return 0.0
    if hi <= lo:
        return 0.0
    clipped = max(lo, min(hi, number))
    return float((clipped - lo) / (hi - lo) * 100.0)


def _normalize_penalty(value: Any, lo: float, hi: float) -> float:
    return 100.0 - _normalize_0_100(value, lo, hi)


def _weighted_group_score(rows: Iterable[Dict[str, Any]], group: str, *, clip: float | None = None) -> float:
    group_rows = [row for row in rows if row.get("group") == group]
    if not group_rows:
        return 0.0
    total_weight = sum(float(row.get("weight") or 0.0) for row in group_rows)
    if total_weight <= 0:
        return 0.0
    score = sum(float(row.get("contribution") or 0.0) for row in group_rows) / total_weight
    if clip is None:
        return score
    return max(-clip, min(clip, score))


def _classify(
    *,
    trend_bias_score: float,
    reversion_bias_score: float,
    trend_confidence_score: float,
    reversion_confidence_score: float,
    cfg: MarketStructureConfig,
) -> str:
    if trend_bias_score - reversion_bias_score >= cfg.bias_verdict_min_gap:
        if trend_confidence_score < cfg.trend_confidence_min:
            return "MIXED"
        return "TREND_BIASED"
    if reversion_bias_score - trend_bias_score >= cfg.bias_verdict_min_gap:
        if reversion_confidence_score < cfg.reversion_confidence_min:
            return "MIXED"
        return "REVERSION_BIASED"
    return "MIXED"


@dataclass(frozen=True)
class MarketStructureMetricCalibrationCandidate:
    chain_strength_lo: float
    chain_strength_hi: float
    pullback_depth_lo: float
    pullback_depth_hi: float
    half_life_lo: float
    half_life_hi: float
    false_break_lo: float
    false_break_hi: float
    choppiness_lo: float
    choppiness_hi: float
    direction_flip_lo: float
    direction_flip_hi: float

    def to_dict(self) -> Dict[str, float]:
        return asdict(self)


def build_metric_calibration_grid() -> List[MarketStructureMetricCalibrationCandidate]:
    chain_options: Sequence[tuple[float, float]] = ((1.0, 4.0), (1.0, 5.0), (1.5, 5.0))
    pullback_options: Sequence[tuple[float, float]] = ((0.2, 1.0), (0.2, 1.2), (0.3, 1.2))
    half_life_options: Sequence[tuple[float, float]] = ((2.0, 20.0), (2.0, 30.0), (4.0, 30.0))
    false_break_options: Sequence[tuple[float, float]] = ((0.10, 0.60), (0.15, 0.70), (0.20, 0.80))
    choppiness_options: Sequence[tuple[float, float]] = ((30.0, 60.0), (35.0, 65.0), (40.0, 70.0))
    flip_options: Sequence[tuple[float, float]] = ((0.05, 0.40), (0.05, 0.50), (0.10, 0.50))
    return [
        MarketStructureMetricCalibrationCandidate(
            chain_strength_lo=chain_lo,
            chain_strength_hi=chain_hi,
            pullback_depth_lo=pullback_lo,
            pullback_depth_hi=pullback_hi,
            half_life_lo=half_lo,
            half_life_hi=half_hi,
            false_break_lo=false_lo,
            false_break_hi=false_hi,
            choppiness_lo=chop_lo,
            choppiness_hi=chop_hi,
            direction_flip_lo=flip_lo,
            direction_flip_hi=flip_hi,
        )
        for (chain_lo, chain_hi), (pullback_lo, pullback_hi), (half_lo, half_hi), (false_lo, false_hi), (chop_lo, chop_hi), (flip_lo, flip_hi) in product(
            chain_options,
            pullback_options,
            half_life_options,
            false_break_options,
            choppiness_options,
            flip_options,
        )
    ]


def _recalculate_rows(
    rows: List[Dict[str, Any]],
    candidate: MarketStructureMetricCalibrationCandidate,
) -> List[Dict[str, Any]]:
    updated: List[Dict[str, Any]] = []
    for row in rows:
        item = dict(row)
        key = str(item.get("key") or item.get("score_key") or "")
        raw = item.get("raw_value")
        score = float(item.get("score") or 0.0)

        if key == "chain_strength":
            score = _normalize_0_100(raw, candidate.chain_strength_lo, candidate.chain_strength_hi)
        elif key == "pullback_quality" and isinstance(raw, dict):
            score = (
                (float(raw.get("continuation_rate") or 0.0) * 100.0)
                - (_normalize_0_100(raw.get("depth"), candidate.pullback_depth_lo, candidate.pullback_depth_hi) * 0.5)
            )
        elif key == "mean_reversion_metrics" and isinstance(raw, dict):
            score = (
                _normalize_penalty(raw.get("half_life_bars"), candidate.half_life_lo, candidate.half_life_hi) * 0.3
                + float(raw.get("zscore_reentry_rate") or 0.0) * 100.0 * 0.4
                + float(raw.get("band_reentry_rate") or 0.0) * 100.0 * 0.3
            )
        elif key == "false_break_reentry" and isinstance(raw, dict):
            score = (
                _normalize_0_100(raw.get("false_break_frequency"), candidate.false_break_lo, candidate.false_break_hi) * 0.5
                + _normalize_0_100(raw.get("reentry_probability"), candidate.false_break_lo, candidate.false_break_hi) * 0.5
            )
        elif key == "choppiness_whipsaw" and isinstance(raw, dict):
            score = (
                _normalize_0_100(raw.get("choppiness_index"), candidate.choppiness_lo, candidate.choppiness_hi) * 0.4
                + float(raw.get("whipsaw_rate") or 0.0) * 100.0 * 0.35
                + _normalize_0_100(raw.get("direction_flip_rate"), candidate.direction_flip_lo, candidate.direction_flip_hi) * 0.25
            )

        item["score"] = score
        item["contribution"] = score * float(item.get("weight") or 0.0)
        updated.append(item)
    return updated


def evaluate_metric_calibration_candidates(
    run_rows: Iterable[Dict[str, Any]],
    validation_rows: Iterable[Dict[str, Any]],
    *,
    cfg: MarketStructureConfig | None = None,
) -> Dict[str, Any]:
    cfg = cfg or MarketStructureConfig()
    validation_map = {
        int(row["run_id"]): row
        for row in validation_rows
        if row.get("realized_verdict") and row.get("realized_verdict") != "INSUFFICIENT_DATA"
    }
    candidates = build_metric_calibration_grid()
    results: List[Dict[str, Any]] = []

    for candidate in candidates:
        evaluated = 0
        matched = 0
        for run in run_rows:
            run_id = int(run.get("run_id") or 0)
            validation = validation_map.get(run_id)
            score_rows = list(run.get("score_rows") or [])
            if not validation or not score_rows:
                continue

            recalculated = _recalculate_rows(score_rows, candidate)
            summary = run.get("summary") or {}
            direction_score = max(-100.0, min(100.0, _weighted_group_score(recalculated, "direction", clip=100.0)))
            trend_confidence_score = max(0.0, min(100.0, _weighted_group_score(recalculated, "confidence")))
            reversion_score = max(0.0, min(100.0, _weighted_group_score(recalculated, "reversion")))
            chop_score = max(0.0, min(100.0, _weighted_group_score(recalculated, "chop")))
            score_map = {str(row.get("key") or row.get("score_key") or ""): float(row.get("score") or 0.0) for row in recalculated}
            reversion_confidence_score = max(
                0.0,
                min(
                    100.0,
                    (score_map.get("sample_quality", 0.0) * 0.35)
                    + (score_map.get("range_state_detection", 0.0) * 0.25)
                    + (score_map.get("false_break_reentry", 0.0) * 0.20)
                    + (score_map.get("mean_reversion_metrics", 0.0) * 0.20),
                ),
            )
            trend_bias_score = abs(direction_score) * (trend_confidence_score / 100.0)
            reversion_mix = (
                (reversion_score * cfg.reversion_score_weight) + (chop_score * cfg.chop_score_weight)
            ) / max(1e-9, cfg.reversion_score_weight + cfg.chop_score_weight)
            reversion_bias_score = min(100.0, reversion_mix * (reversion_confidence_score / 100.0))
            predicted = _classify(
                trend_bias_score=trend_bias_score,
                reversion_bias_score=reversion_bias_score,
                trend_confidence_score=trend_confidence_score,
                reversion_confidence_score=reversion_confidence_score,
                cfg=cfg,
            )
            realized = str(validation.get("realized_verdict") or "MIXED")
            evaluated += 1
            if predicted == realized:
                matched += 1

        accuracy = matched / evaluated if evaluated else 0.0
        results.append(
            {
                "settings": candidate.to_dict(),
                "evaluated_runs": evaluated,
                "matched_runs": matched,
                "accuracy": accuracy,
            }
        )

    results.sort(
        key=lambda item: (
            float(item.get("accuracy") or 0.0),
            int(item.get("matched_runs") or 0),
        ),
        reverse=True,
    )
    return {
        "total_candidates": len(results),
        "best": results[0] if results else None,
        "rows": results[:10],
    }
