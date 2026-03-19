"""Regime alignment score."""

from __future__ import annotations

from typing import List

from .base import ScoreContext, ScoreRow
from .normalization import clamp_score, confidence_from_inputs, confidence_label


class RegimeAlignmentScore:
    family_name = "regime_alignment"

    def compute(self, context: ScoreContext) -> List[ScoreRow]:
        summary = context.snapshot.summary
        regime_name = str(summary.get("regime_name", "UNKNOWN") or "UNKNOWN")
        confidence_value = float(summary.get("regime_confidence", 0.0) or 0.0)
        governance_decision = str(summary.get("governance_decision", "") or "")
        base_score = 100.0
        if regime_name == "STRESS":
            base_score -= 35.0
        if governance_decision == "REJECT":
            base_score -= 15.0
        if str(summary.get("liquidity_regime", "")) == "STRESSED":
            base_score -= 10.0
        score = clamp_score(base_score * (0.7 + 0.3 * confidence_value))
        confidence = confidence_from_inputs(2)
        return [
            ScoreRow(
                family=self.family_name,
                score_key="regime_alignment_score",
                score_value=score,
                confidence=confidence,
                confidence_label=confidence_label(confidence),
                explanation="Penalizes stress/crisis regime states and governance tightening context.",
                context={
                    "regime_name": regime_name,
                    "regime_confidence": confidence_value,
                    "governance_decision": governance_decision,
                    "liquidity_regime": summary.get("liquidity_regime"),
                },
            )
        ]
