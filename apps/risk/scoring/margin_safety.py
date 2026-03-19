"""Margin safety score."""

from __future__ import annotations

from typing import List

from .base import ScoreContext, ScoreRow
from .normalization import confidence_from_inputs, confidence_label, inverse_ratio_score


class MarginSafetyScore:
    family_name = "margin_safety"

    def compute(self, context: ScoreContext) -> List[ScoreRow]:
        margin_used_frac = float(context.snapshot.summary.get("margin_used_frac", 0.0) or 0.0)
        score = inverse_ratio_score(margin_used_frac, good=0.1, bad=0.7)
        confidence = confidence_from_inputs(1)
        return [
            ScoreRow(
                family=self.family_name,
                score_key="margin_safety_score",
                score_value=score,
                confidence=confidence,
                confidence_label=confidence_label(confidence),
                explanation="Scores margin headroom from used-margin fraction.",
                context={"margin_used_frac": margin_used_frac},
            )
        ]
