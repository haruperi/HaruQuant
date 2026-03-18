"""Validation helpers for Market Structure forward-outcome reporting."""

from __future__ import annotations

from typing import Any, Dict, List

import numpy as np
import pandas as pd


def _pip_size(symbol: str) -> float:
    return 0.01 if symbol.upper().endswith("JPY") else 0.0001


def confidence_bucket(score: Any) -> str:
    try:
        value = float(score)
    except (TypeError, ValueError):
        return "unknown"
    if value >= 70:
        return "high"
    if value >= 45:
        return "medium"
    return "low"


def label_realized_market_behavior(
    df: pd.DataFrame,
    *,
    symbol: str,
    close_col: str = "Close",
    high_col: str = "High",
    low_col: str = "Low",
) -> Dict[str, float | str]:
    """Classify the realized future window as trend, reversion, or mixed."""
    if len(df) < 5:
        return {
            "realized_verdict": "INSUFFICIENT_DATA",
            "net_move_pips": 0.0,
            "path_pips": 0.0,
            "efficiency": 0.0,
            "reversion_ratio": 0.0,
            "flip_rate": 0.0,
            "avg_range_pips": 0.0,
            "max_excursion_pips": 0.0,
            "continuation_label": "unknown",
            "range_reentry_label": "unknown",
            "breakout_failure_label": "unknown",
            "chop_label": "unknown",
        }

    pip = _pip_size(symbol)
    close = df[close_col].astype(float)
    high = df[high_col].astype(float)
    low = df[low_col].astype(float)

    start = float(close.iloc[0])
    end = float(close.iloc[-1])
    diffs = close.diff().dropna()
    path = float(diffs.abs().sum())
    net = abs(end - start)
    efficiency = net / path if path > 0 else 0.0
    excursions = (close - start).abs()
    max_excursion = float(excursions.max()) if len(excursions) else 0.0
    reversion_ratio = net / max_excursion if max_excursion > 0 else 0.0
    flip_count = 0
    sign = np.sign(diffs.to_numpy(dtype=float))
    for idx in range(1, len(sign)):
        if sign[idx] != 0 and sign[idx - 1] != 0 and sign[idx] != sign[idx - 1]:
            flip_count += 1
    flip_rate = float(flip_count / max(1, len(sign) - 1))
    avg_range_pips = float(((high - low) / pip).mean()) if len(df) else 0.0
    net_move_pips = net / pip
    max_excursion_pips = max_excursion / pip
    move_floor = max(10.0, avg_range_pips * 1.5)

    if efficiency >= 0.55 and net_move_pips >= move_floor:
        verdict = "TREND_BIASED"
    elif reversion_ratio <= 0.35 and flip_rate >= 0.35 and max_excursion_pips >= move_floor:
        verdict = "REVERSION_BIASED"
    else:
        verdict = "MIXED"

    continuation_label = "high" if efficiency >= 0.55 and net_move_pips >= move_floor else "low"
    range_reentry_label = "high" if reversion_ratio <= 0.35 else "low"
    breakout_failure_label = "high" if reversion_ratio <= 0.45 and flip_rate >= 0.30 else "low"
    chop_label = "high" if flip_rate >= 0.35 and efficiency <= 0.40 else "low"

    return {
        "realized_verdict": verdict,
        "net_move_pips": float(net_move_pips),
        "path_pips": float(path / pip),
        "efficiency": float(efficiency),
        "reversion_ratio": float(reversion_ratio),
        "flip_rate": float(flip_rate),
        "avg_range_pips": float(avg_range_pips),
        "max_excursion_pips": float(max_excursion_pips),
        "continuation_label": continuation_label,
        "range_reentry_label": range_reentry_label,
        "breakout_failure_label": breakout_failure_label,
        "chop_label": chop_label,
    }


def build_validation_summary(rows: List[Dict[str, Any]]) -> Dict[str, Any]:
    evaluated_rows = [row for row in rows if row.get("realized_verdict") != "INSUFFICIENT_DATA"]
    total = len(evaluated_rows)
    correct = sum(1 for row in evaluated_rows if row.get("matched"))
    by_bucket: Dict[str, Dict[str, int]] = {}
    by_predicted: Dict[str, Dict[str, int]] = {}
    by_symbol: Dict[str, Dict[str, int]] = {}
    by_timeframe: Dict[str, Dict[str, int]] = {}
    by_realized: Dict[str, Dict[str, int]] = {}

    for row in evaluated_rows:
        bucket = str(row.get("confidence_bucket") or "unknown")
        predicted = str(row.get("predicted_verdict") or "unknown")
        symbol = str(row.get("symbol") or "unknown")
        timeframe = str(row.get("timeframe") or "unknown")
        realized = str(row.get("realized_verdict") or "MIXED")
        bucket_entry = by_bucket.setdefault(bucket, {"total": 0, "correct": 0})
        bucket_entry["total"] += 1
        if row.get("matched"):
            bucket_entry["correct"] += 1

        predicted_entry = by_predicted.setdefault(
            predicted,
            {"total": 0, "trend_hits": 0, "reversion_hits": 0, "mixed_hits": 0},
        )
        predicted_entry["total"] += 1
        if realized == "TREND_BIASED":
            predicted_entry["trend_hits"] += 1
        elif realized == "REVERSION_BIASED":
            predicted_entry["reversion_hits"] += 1
        else:
            predicted_entry["mixed_hits"] += 1

        symbol_entry = by_symbol.setdefault(symbol, {"total": 0, "correct": 0})
        symbol_entry["total"] += 1
        if row.get("matched"):
            symbol_entry["correct"] += 1

        timeframe_entry = by_timeframe.setdefault(timeframe, {"total": 0, "correct": 0})
        timeframe_entry["total"] += 1
        if row.get("matched"):
            timeframe_entry["correct"] += 1

        realized_entry = by_realized.setdefault(realized, {"total": 0, "correct": 0})
        realized_entry["total"] += 1
        if row.get("matched"):
            realized_entry["correct"] += 1

    return {
        "evaluated_runs": total,
        "matched_runs": correct,
        "accuracy": (correct / total) if total else 0.0,
        "by_confidence_bucket": by_bucket,
        "by_predicted_verdict": by_predicted,
        "by_symbol": by_symbol,
        "by_timeframe": by_timeframe,
        "by_realized_verdict": by_realized,
    }
