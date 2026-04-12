"""Regime stability helpers for Market Structure."""

from __future__ import annotations

from collections import Counter
from typing import Any, Dict, List, Optional

import numpy as np
import pandas as pd

from backend.services.research.config import MarketStructureConfig
from backend.services.research.data.models import PreparedDataset
from backend.services.research.market_structure import build_market_structure_profile


def _stability_label(agreement_rate: float, score_std: float, cfg: MarketStructureConfig) -> str:
    if agreement_rate >= 0.8 and score_std <= cfg.stability_score_std_max:
        return "HIGH"
    if agreement_rate >= 0.6 and score_std <= cfg.stability_score_std_max * 1.5:
        return "MEDIUM"
    return "LOW"


def _build_slices(prepared: PreparedDataset, mode: str, cfg: MarketStructureConfig) -> List[pd.DataFrame]:
    data = prepared.data
    if mode == "early_middle_late":
        block_count = max(2, int(cfg.stability_block_count))
        rows_per_block = len(data) // block_count if block_count > 0 else 0
        if rows_per_block < cfg.stability_min_bars_per_block:
            return []
        frames = []
        for idx in range(block_count):
            start = idx * rows_per_block
            end = len(data) if idx == block_count - 1 else (idx + 1) * rows_per_block
            frames.append(data.iloc[start:end].copy())
        return frames
    if mode == "monthly":
        return [frame.copy() for _, frame in data.groupby(pd.Grouper(freq="MS")) if len(frame) >= cfg.stability_min_bars_per_block]
    if mode == "quarterly":
        return [frame.copy() for _, frame in data.groupby(pd.Grouper(freq="QS")) if len(frame) >= cfg.stability_min_bars_per_block]
    return []


def build_market_structure_stability_report(
    prepared: PreparedDataset,
    *,
    symbol: str,
    timeframe: str,
    data_source: str,
    range_by: str,
    start_date: Optional[str] = None,
    end_date: Optional[str] = None,
    number_of_bars: Optional[int] = None,
    config: Optional[MarketStructureConfig] = None,
) -> Dict[str, Any]:
    cfg = config or MarketStructureConfig()
    mode_reports: List[Dict[str, Any]] = []

    for mode in cfg.stability_modes:
        slices = _build_slices(prepared, mode, cfg)
        if len(slices) < 2:
            continue
        block_summaries: List[Dict[str, Any]] = []
        confidence_scores: List[float] = []
        for idx, block_df in enumerate(slices):
            block_prepared = PreparedDataset(
                data=block_df,
                report=prepared.report,
                schema=prepared.schema,
            )
            profile = build_market_structure_profile(
                block_prepared,
                symbol=symbol,
                timeframe=timeframe,
                data_source=data_source,
                range_by=range_by,
                start_date=start_date,
                end_date=end_date,
                number_of_bars=len(block_df) if number_of_bars is None else None,
                config=cfg,
            )
            summary = profile.summary
            block_summaries.append(
                {
                    "block": idx + 1,
                    "rows": len(block_df),
                    "start": block_df.index.min().isoformat(),
                    "end": block_df.index.max().isoformat(),
                    "verdict": summary.get("verdict"),
                    "direction": summary.get("direction"),
                    "final_score": float(summary.get("final_score") or 0.0),
                    "decision_confidence_score": float(summary.get("decision_confidence_score") or 0.0),
                }
            )
            confidence_scores.append(float(summary.get("decision_confidence_score") or 0.0))

        verdicts = [str(block["verdict"] or "MIXED") for block in block_summaries]
        directions = [str(block["direction"] or "neutral") for block in block_summaries]
        final_scores = [float(block["final_score"]) for block in block_summaries]
        dominant_verdict_count = Counter(verdicts).most_common(1)[0][1] if verdicts else 0
        dominant_direction_count = Counter(directions).most_common(1)[0][1] if directions else 0
        agreement_rate = dominant_verdict_count / len(block_summaries) if block_summaries else 0.0
        direction_agreement_rate = dominant_direction_count / len(block_summaries) if block_summaries else 0.0
        score_std = float(np.std(final_scores)) if final_scores else 0.0
        confidence_drift = float(np.std(confidence_scores)) if confidence_scores else 0.0
        mode_reports.append(
            {
                "mode": mode,
                "is_evaluable": True,
                "block_count": len(block_summaries),
                "agreement_rate": agreement_rate,
                "direction_agreement_rate": direction_agreement_rate,
                "final_score_std": score_std,
                "confidence_drift": confidence_drift,
                "stability": _stability_label(agreement_rate, score_std, cfg),
                "blocks": block_summaries,
            }
        )

    if not mode_reports:
        return {
            "is_evaluable": False,
            "block_count": 0,
            "evaluated_blocks": 0,
            "agreement_rate": 0.0,
            "final_score_std": 0.0,
            "direction_agreement_rate": 0.0,
            "confidence_drift": 0.0,
            "stability": "INSUFFICIENT_DATA",
            "blocks": [],
            "modes": [],
        }
    agreement_rate = float(np.mean([report["agreement_rate"] for report in mode_reports]))
    direction_agreement_rate = float(np.mean([report["direction_agreement_rate"] for report in mode_reports]))
    score_std = float(np.mean([report["final_score_std"] for report in mode_reports]))
    confidence_drift = float(np.mean([report["confidence_drift"] for report in mode_reports]))
    primary = mode_reports[0]

    return {
        "is_evaluable": True,
        "block_count": int(primary["block_count"]),
        "evaluated_blocks": sum(int(report["block_count"]) for report in mode_reports),
        "agreement_rate": agreement_rate,
        "final_score_std": score_std,
        "direction_agreement_rate": direction_agreement_rate,
        "confidence_drift": confidence_drift,
        "stability": _stability_label(agreement_rate, score_std, cfg),
        "blocks": list(primary["blocks"]),
        "modes": mode_reports,
    }
