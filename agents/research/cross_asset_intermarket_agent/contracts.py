"""Contracts for the Cross-Asset / Intermarket Agent."""

from __future__ import annotations

from pydantic import BaseModel, Field

from agents.research.shared.contracts import ResearchReportArtifact, ResearchRequestPayload


class CrossAssetIntermarketAgentPayload(ResearchRequestPayload):
    """Validated payload accepted by Cross-Asset / Intermarket Agent."""


class CrossAssetIntermarketAgentArtifact(ResearchReportArtifact):
    """Report artifact produced by Cross-Asset / Intermarket Agent."""

    report_type: str = "cross_asset_intermarket_report"


class CrossAssetIntermarketAgentToolResult(BaseModel):
    source: str
    value: dict = Field(default_factory=dict)
