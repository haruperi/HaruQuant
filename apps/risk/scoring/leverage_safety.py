"""Leverage safety score."""

from __future__ import annotations

from typing import List

from .base import ScoreContext, ScoreRow
from .normalization import confidence_from_inputs, confidence_label, inverse_ratio_score


class LeverageSafetyScore:
    family_name = "leverage_safety"

    def compute(self, context: ScoreContext) -> List[ScoreRow]:
        gross_leverage = float(context.snapshot.summary.get("gross_leverage", 0.0) or 0.0)
        score = inverse_ratio_score(gross_leverage, good=1.0, bad=10.0)
        confidence = confidence_from_inputs(1)
        return [
            ScoreRow(
                family=self.family_name,
                score_key="leverage_safety_score",
                score_value=score,
                confidence=confidence,
                confidence_label=confidence_label(confidence),
                explanation="Scores leverage safety from gross leverage relative to equity.",
                context={"gross_leverage": gross_leverage},
            )
        ]
