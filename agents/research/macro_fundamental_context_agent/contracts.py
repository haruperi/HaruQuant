"""Contracts for the Macro and Fundamental Context Agent."""

from __future__ import annotations

from pydantic import BaseModel, Field

from agents.research.shared.contracts import ResearchReportArtifact, ResearchRequestPayload


class MacroFundamentalContextAgentPayload(ResearchRequestPayload):
    """Validated payload accepted by Macro and Fundamental Context Agent."""


class MacroFundamentalContextAgentArtifact(ResearchReportArtifact):
    """Report artifact produced by Macro and Fundamental Context Agent."""

    report_type: str = "macro_fundamental_report"


class MacroFundamentalContextAgentToolResult(BaseModel):
    source: str
    value: dict = Field(default_factory=dict)
