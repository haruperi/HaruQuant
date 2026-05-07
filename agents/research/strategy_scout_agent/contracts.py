"""Contracts for the Strategy Scout Agent."""

from __future__ import annotations

from pydantic import BaseModel, Field

from agents.research.shared.contracts import ResearchReportArtifact, ResearchRequestPayload


class StrategyScoutAgentPayload(ResearchRequestPayload):
    """Validated payload accepted by Strategy Scout Agent."""


class StrategyScoutAgentArtifact(ResearchReportArtifact):
    """Report artifact produced by Strategy Scout Agent."""

    report_type: str = "strategy_scout_report"


class StrategyScoutAgentToolResult(BaseModel):
    source: str
    value: dict = Field(default_factory=dict)
