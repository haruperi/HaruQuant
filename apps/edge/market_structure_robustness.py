"""Parameter robustness helpers for Market Structure."""

from __future__ import annotations

from collections import Counter
from dataclasses import replace
from typing import Any, Dict, List, Optional

import numpy as np

from apps.edge.config import MarketStructureConfig
from apps.edge.data.models import PreparedDataset
from apps.edge.market_structure import build_market_structure_profile


def _robustness_label(verdict_agreement_rate: float, score_std: float) -> str:
    if verdict_agreement_rate >= 0.8 and score_std <= 20.0:
        return "HIGH"
    if verdict_agreement_rate >= 0.6 and score_std <= 30.0:
        return "MEDIUM"
    return "LOW"


def build_market_structure_robustness_report(
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
    variants: List[Dict[str, Any]] = []

    for swing_window in cfg.robustness_swing_windows:
        for min_swing_atr in cfg.robustness_min_swing_atrs:
            for range_window in cfg.robustness_range_windows:
                for breakout_horizon in cfg.robustness_breakout_horizons:
                    variant_cfg = replace(
                        cfg,
                        swing_window=int(swing_window),
                        min_swing_atr=float(min_swing_atr),
                        range_window=int(range_window),
                        breakout_horizon=int(breakout_horizon),
                    )
                    profile = build_market_structure_profile(
                        prepared,
                        symbol=symbol,
                        timeframe=timeframe,
                        data_source=data_source,
                        range_by=range_by,
                        start_date=start_date,
                        end_date=end_date,
                        number_of_bars=number_of_bars,
                        config=variant_cfg,
                    )
                    summary = profile.summary
                    variants.append(
                        {
                            "swing_window": int(swing_window),
                            "min_swing_atr": float(min_swing_atr),
                            "range_window": int(range_window),
                            "breakout_horizon": int(breakout_horizon),
                            "verdict": str(summary.get("verdict") or "MIXED"),
                            "direction": str(summary.get("direction") or "neutral"),
                            "final_score": float(summary.get("final_score") or 0.0),
                        }
                    )

    verdicts = [variant["verdict"] for variant in variants]
    directions = [variant["direction"] for variant in variants]
    scores = [float(variant["final_score"]) for variant in variants]
    dominant_verdict_count = Counter(verdicts).most_common(1)[0][1] if verdicts else 0
    dominant_direction_count = Counter(directions).most_common(1)[0][1] if directions else 0
    verdict_agreement_rate = dominant_verdict_count / len(variants) if variants else 0.0
    direction_agreement_rate = dominant_direction_count / len(variants) if variants else 0.0
    score_std = float(np.std(scores)) if scores else 0.0

    return {
        "variant_count": len(variants),
        "verdict_agreement_rate": verdict_agreement_rate,
        "direction_agreement_rate": direction_agreement_rate,
        "final_score_std": score_std,
        "robustness": _robustness_label(verdict_agreement_rate, score_std),
        "variants": variants,
    }
