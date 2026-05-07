"""Overall risk quality score."""

from __future__ import annotations

from typing import List

from .base import ScoreContext, ScoreRow
from .normalization import confidence_from_inputs, confidence_label


class OverallRiskQualityScore:
    family_name = "overall_risk_quality"

    def compute(self, context: ScoreContext) -> List[ScoreRow]:
        rows = context.shared.get("score_rows") or []
        component_keys = {
            "portfolio_health_score",
            "concentration_score",
            "diversification_score",
            "leverage_safety_score",
            "margin_safety_score",
            "stress_resilience_score",
            "regime_alignment_score",
            "governance_compliance_score",
        }
        components = [row for row in rows if getattr(row, "score_key", "") in component_keys]
        if not components:
            return []
        score = sum(float(row.score_value) for row in components) / len(components)
        confidence = confidence_from_inputs(len(components))
        return [
            ScoreRow(
                family=self.family_name,
                score_key="overall_risk_quality_score",
                score_value=score,
                confidence=confidence,
                confidence_label=confidence_label(confidence),
                explanation="Weighted equally from the core component risk scores.",
                context={"components": {row.score_key: row.score_value for row in components}},
            )
        ]
