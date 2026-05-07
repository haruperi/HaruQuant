"""Diversification score."""

from __future__ import annotations

from typing import List

from .base import ScoreContext, ScoreRow
from .normalization import confidence_from_inputs, confidence_label, direct_ratio_score


class DiversificationScore:
    family_name = "diversification_score"

    def compute(self, context: ScoreContext) -> List[ScoreRow]:
        summary = context.snapshot.summary
        div_ratio = float(summary.get("diversification_ratio", 0.0) or 0.0)
        effective_bets = float(summary.get("effective_independent_bets", 0.0) or 0.0)
        parts = [
            direct_ratio_score(div_ratio, bad=1.0, good=2.0),
            direct_ratio_score(effective_bets, bad=1.0, good=max(float(len(context.snapshot.state.active_symbols)), 2.0)),
        ]
        score = sum(parts) / len(parts)
        confidence = confidence_from_inputs(len(parts))
        return [
            ScoreRow(
                family=self.family_name,
                score_key="diversification_score",
                score_value=score,
                confidence=confidence,
                confidence_label=confidence_label(confidence),
                explanation="Rewards higher diversification ratio and more effective independent bets.",
                context={"diversification_ratio": div_ratio, "effective_independent_bets": effective_bets},
            )
        ]
