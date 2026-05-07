"""Strategy Creation scoring helpers."""

from __future__ import annotations

from pydantic import BaseModel, Field


class StrategyCreationScorecard(BaseModel):
    spec_completeness: float = Field(default=1.0, ge=0.0, le=1.0)
    template_compliance: float = Field(default=1.0, ge=0.0, le=1.0)
    lookahead_safety: float = Field(default=1.0, ge=0.0, le=1.0)
    risk_compatibility: float = Field(default=1.0, ge=0.0, le=1.0)
    test_completeness: float = Field(default=1.0, ge=0.0, le=1.0)


def readiness_score(scorecard: StrategyCreationScorecard) -> float:
    return round(
        0.25 * scorecard.spec_completeness
        + 0.25 * scorecard.template_compliance
        + 0.20 * scorecard.lookahead_safety
        + 0.15 * scorecard.risk_compatibility
        + 0.15 * scorecard.test_completeness,
        4,
    )
