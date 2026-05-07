"""Governance compliance score."""

from __future__ import annotations

from typing import List

from .base import ScoreContext, ScoreRow
from .normalization import clamp_score, confidence_from_inputs, confidence_label


class GovernanceComplianceScore:
    family_name = "governance_compliance"

    def compute(self, context: ScoreContext) -> List[ScoreRow]:
        summary = context.snapshot.summary
        status = str(summary.get("compliance_state", "unknown") or "unknown")
        warnings = float(summary.get("governance_warnings_count", 0.0) or 0.0)
        breaches = float(summary.get("governance_breaches_count", 0.0) or 0.0)
        base = {"compliant": 100.0, "warning": 75.0, "breach": 20.0}.get(status, 50.0)
        score = clamp_score(base - (warnings * 5.0) - (breaches * 20.0))
        confidence = confidence_from_inputs(3)
        return [
            ScoreRow(
                family=self.family_name,
                score_key="governance_compliance_score",
                score_value=score,
                confidence=confidence,
                confidence_label=confidence_label(confidence),
                explanation="Scores compliance from governance status, warnings, and breaches.",
                context={"compliance_state": status, "warnings_count": warnings, "breaches_count": breaches},
            )
        ]
