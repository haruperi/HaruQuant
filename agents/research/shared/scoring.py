"""Deterministic scoring helpers for Research Department agents."""

from __future__ import annotations

from pydantic import BaseModel, Field


class ResearchScorecard(BaseModel):
    novelty_score: float = Field(default=0.5, ge=0.0, le=1.0)
    feasibility_score: float = Field(default=0.5, ge=0.0, le=1.0)
    edge_plausibility_score: float = Field(default=0.5, ge=0.0, le=1.0)
    testability_score: float = Field(default=0.5, ge=0.0, le=1.0)
    risk_compatibility_score: float = Field(default=0.5, ge=0.0, le=1.0)
    portfolio_fit_score: float = Field(default=0.5, ge=0.0, le=1.0)
    execution_realism_score: float = Field(default=0.5, ge=0.0, le=1.0)
    robustness_expectation_score: float = Field(default=0.5, ge=0.0, le=1.0)
    data_quality_score: float = Field(default=0.75, ge=0.0, le=1.0)
    evidence_quality_score: float = Field(default=0.75, ge=0.0, le=1.0)
    overfitting_risk_score: float = Field(default=0.5, ge=0.0, le=1.0)
    complexity_score: float = Field(default=0.5, ge=0.0, le=1.0)
    confidence_score: float = Field(default=0.5, ge=0.0, le=1.0)


def calculate_research_score(scorecard: ResearchScorecard) -> float:
    raw = (
        0.15 * scorecard.novelty_score
        + 0.15 * scorecard.feasibility_score
        + 0.20 * scorecard.edge_plausibility_score
        + 0.15 * scorecard.testability_score
        + 0.15 * scorecard.risk_compatibility_score
        + 0.10 * scorecard.portfolio_fit_score
        + 0.10 * scorecard.execution_realism_score
        - 0.10 * scorecard.overfitting_risk_score
        - 0.05 * scorecard.complexity_score
    )
    return max(0.0, min(1.0, round(raw, 4)))
