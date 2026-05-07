"""Contracts for the Strategy Hypothesis Agent."""

from __future__ import annotations

from pydantic import BaseModel, Field

from agents.research.shared.contracts import ResearchReportArtifact, ResearchRequestPayload


class StrategyHypothesisAgentPayload(ResearchRequestPayload):
    """Validated payload accepted by Strategy Hypothesis Agent."""


class StrategyHypothesisAgentArtifact(ResearchReportArtifact):
    """Report artifact produced by Strategy Hypothesis Agent."""

    report_type: str = "strategy_hypothesis_report"


class StrategyHypothesisAgentToolResult(BaseModel):
    source: str
    value: dict = Field(default_factory=dict)
