"""Contracts for the Seasonality and Calendar Agent."""

from __future__ import annotations

from pydantic import BaseModel, Field

from agents.research.shared.contracts import ResearchReportArtifact, ResearchRequestPayload


class SeasonalityCalendarAgentPayload(ResearchRequestPayload):
    """Validated payload accepted by Seasonality and Calendar Agent."""


class SeasonalityCalendarAgentArtifact(ResearchReportArtifact):
    """Report artifact produced by Seasonality and Calendar Agent."""

    report_type: str = "seasonality_calendar_report"


class SeasonalityCalendarAgentToolResult(BaseModel):
    source: str
    value: dict = Field(default_factory=dict)
