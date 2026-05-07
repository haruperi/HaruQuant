"""Registry for risk score families."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Iterable, List

from .base import ScoreContext, ScoreFamily, ScoreRow
from .concentration_score import ConcentrationScore
from .diversification_score import DiversificationScore
from .governance_compliance import GovernanceComplianceScore
from .leverage_safety import LeverageSafetyScore
from .margin_safety import MarginSafetyScore
from .overall_risk_quality import OverallRiskQualityScore
from .portfolio_health import PortfolioHealthScore
from .regime_alignment import RegimeAlignmentScore
from .stress_fragility import StressFragilityScore


@dataclass
class ScoreRegistry:
    families: List[ScoreFamily] = field(default_factory=list)

    def register(self, family: ScoreFamily) -> None:
        self.families.append(family)

    def extend(self, families: Iterable[ScoreFamily]) -> None:
        self.families.extend(families)

    def compute_all(self, context: ScoreContext) -> List[ScoreRow]:
        rows: List[ScoreRow] = []
        for family in self.families:
            rows.extend(family.compute(context))
        return rows


def build_default_score_registry() -> ScoreRegistry:
    registry = ScoreRegistry()
    registry.extend(
        [
            PortfolioHealthScore(),
            ConcentrationScore(),
            DiversificationScore(),
            LeverageSafetyScore(),
            MarginSafetyScore(),
            StressFragilityScore(),
            RegimeAlignmentScore(),
            GovernanceComplianceScore(),
            OverallRiskQualityScore(),
        ]
    )
    return registry
