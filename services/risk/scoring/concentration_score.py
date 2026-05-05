"""Concentration score."""

from __future__ import annotations

from typing import List

from .base import ScoreContext, ScoreRow
from .normalization import confidence_from_inputs, confidence_label, inverse_ratio_score


class ConcentrationScore:
    family_name = "concentration_score"

    def compute(self, context: ScoreContext) -> List[ScoreRow]:
        summary = context.snapshot.summary
        top_exposure = float(summary.get("max_single_exposure_frac", 0.0) or 0.0)
        overlap = float(summary.get("hidden_overlap_score", 0.0) or 0.0)
        avg_corr = abs(float(summary.get("average_pair_correlation", 0.0) or 0.0))
        parts = [
            inverse_ratio_score(top_exposure, good=0.15, bad=0.5),
            inverse_ratio_score(overlap, good=0.05, bad=0.4),
            inverse_ratio_score(avg_corr, good=0.15, bad=0.8),
        ]
        score = sum(parts) / len(parts)
        confidence = confidence_from_inputs(len(parts))
        return [
            ScoreRow(
                family=self.family_name,
                score_key="concentration_score",
                score_value=score,
                confidence=confidence,
                confidence_label=confidence_label(confidence),
                explanation="Penalizes single-name concentration, hidden overlap, and high average correlation.",
                context={"max_single_exposure_frac": top_exposure, "hidden_overlap_score": overlap, "average_pair_correlation_abs": avg_corr},
            )
        ]
