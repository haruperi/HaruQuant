"""Stress fragility / resilience score."""

from __future__ import annotations

from typing import List

from .base import ScoreContext, ScoreRow
from .normalization import confidence_from_inputs, confidence_label, inverse_ratio_score


class StressFragilityScore:
    family_name = "stress_fragility"

    def compute(self, context: ScoreContext) -> List[ScoreRow]:
        equity = float(context.snapshot.state.account.equity or 0.0)
        worst_loss = float(context.snapshot.summary.get("worst_scenario_loss", 0.0) or 0.0)
        loss_ratio = (worst_loss / equity) if equity > 0.0 else None
        score = inverse_ratio_score(loss_ratio, good=0.05, bad=0.5)
        confidence = confidence_from_inputs(1)
        return [
            ScoreRow(
                family=self.family_name,
                score_key="stress_resilience_score",
                score_value=score,
                confidence=confidence,
                confidence_label=confidence_label(confidence),
                explanation="Scores resilience from the worst deterministic scenario loss relative to equity.",
                context={"worst_scenario_loss": worst_loss, "worst_scenario_name": context.snapshot.summary.get("worst_scenario_name"), "loss_ratio": loss_ratio},
            )
        ]
