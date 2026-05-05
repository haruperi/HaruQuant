"""Scorecard engine built on normalized risk snapshots."""

from __future__ import annotations

from typing import Any, Dict, Optional

from services.risk.metrics import RiskSnapshot
from services.risk.scoring import RiskScorecard, ScoreContext
from services.risk.scoring.registry import ScoreRegistry, build_default_score_registry


class RiskScorecardEngine:
    """Build an explainable scorecard from a normalized risk snapshot."""

    def __init__(self, registry: Optional[ScoreRegistry] = None):
        self.registry = registry or build_default_score_registry()

    def build_scorecard(
        self,
        snapshot: RiskSnapshot,
        shared: Optional[Dict[str, Any]] = None,
    ) -> RiskScorecard:
        base_shared = dict(shared or {})
        rows = []
        for family in self.registry.families:
            family_context = ScoreContext(snapshot=snapshot, shared={**base_shared, "score_rows": list(rows)})
            rows.extend(family.compute(family_context))
        summary = self._build_summary(snapshot, rows)
        return RiskScorecard(snapshot=snapshot, score_rows=rows, summary=summary)

    def _build_summary(self, snapshot: RiskSnapshot, rows) -> Dict[str, Any]:
        summary: Dict[str, Any] = {
            "as_of": snapshot.summary.get("as_of"),
            "score_count": len(rows),
        }
        for row in rows:
            summary[row.score_key] = row.score_value
            if row.score_key == "overall_risk_quality_score":
                summary["overall_confidence"] = row.confidence
                summary["overall_confidence_label"] = row.confidence_label
        return summary
