"""Contracts for the Research Department Orchestrator Agent."""

from __future__ import annotations

from pydantic import BaseModel, Field

from agents.research.shared.contracts import ResearchReportArtifact, ResearchRequestPayload


class ResearchOrchestratorAgentPayload(ResearchRequestPayload):
    """Validated payload accepted by Research Department Orchestrator Agent."""


class ResearchOrchestratorAgentArtifact(ResearchReportArtifact):
    """Report artifact produced by Research Department Orchestrator Agent."""

    report_type: str = "research_orchestration_report"


class ResearchOrchestratorAgentToolResult(BaseModel):
    source: str
    value: dict = Field(default_factory=dict)
