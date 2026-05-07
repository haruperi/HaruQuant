"""Contracts for the Market Intelligence Agent."""

from __future__ import annotations

from pydantic import BaseModel, Field

from agents.research.shared.contracts import ResearchReportArtifact, ResearchRequestPayload


class MarketIntelligenceAgentPayload(ResearchRequestPayload):
    """Validated payload accepted by Market Intelligence Agent."""


class MarketIntelligenceAgentArtifact(ResearchReportArtifact):
    """Report artifact produced by Market Intelligence Agent."""

    report_type: str = "market_intelligence_report"


class MarketIntelligenceAgentToolResult(BaseModel):
    source: str
    value: dict = Field(default_factory=dict)
