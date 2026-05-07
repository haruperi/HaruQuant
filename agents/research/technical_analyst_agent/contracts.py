"""Contracts for the Technical Analyst Agent."""

from __future__ import annotations

from pydantic import BaseModel, Field

from agents.research.shared.contracts import ResearchReportArtifact, ResearchRequestPayload


class TechnicalAnalystAgentPayload(ResearchRequestPayload):
    """Validated payload accepted by Technical Analyst Agent."""


class TechnicalAnalystAgentArtifact(ResearchReportArtifact):
    """Report artifact produced by Technical Analyst Agent."""

    report_type: str = "technical_analysis_report"


class TechnicalAnalystAgentToolResult(BaseModel):
    source: str
    value: dict = Field(default_factory=dict)
