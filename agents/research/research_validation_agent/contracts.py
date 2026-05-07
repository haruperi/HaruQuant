"""Contracts for the Research Validation Agent."""

from __future__ import annotations

from pydantic import BaseModel, Field

from agents.research.shared.contracts import ResearchReportArtifact, ResearchRequestPayload


class ResearchValidationAgentPayload(ResearchRequestPayload):
    """Validated payload accepted by Research Validation Agent."""


class ResearchValidationAgentArtifact(ResearchReportArtifact):
    """Report artifact produced by Research Validation Agent."""

    report_type: str = "research_validation_report"


class ResearchValidationAgentToolResult(BaseModel):
    source: str
    value: dict = Field(default_factory=dict)
