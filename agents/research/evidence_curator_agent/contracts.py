"""Contracts for the Evidence Curator Agent."""

from __future__ import annotations

from pydantic import BaseModel, Field

from agents.research.shared.contracts import ResearchReportArtifact, ResearchRequestPayload


class EvidenceCuratorAgentPayload(ResearchRequestPayload):
    """Validated payload accepted by Evidence Curator Agent."""


class EvidenceCuratorAgentArtifact(ResearchReportArtifact):
    """Report artifact produced by Evidence Curator Agent."""

    report_type: str = "evidence_curator_report"


class EvidenceCuratorAgentToolResult(BaseModel):
    source: str
    value: dict = Field(default_factory=dict)
