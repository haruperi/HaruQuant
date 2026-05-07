"""Contracts for the News and Sentiment Agent."""

from __future__ import annotations

from pydantic import BaseModel, Field

from agents.research.shared.contracts import ResearchReportArtifact, ResearchRequestPayload


class NewsSentimentAgentPayload(ResearchRequestPayload):
    """Validated payload accepted by News and Sentiment Agent."""


class NewsSentimentAgentArtifact(ResearchReportArtifact):
    """Report artifact produced by News and Sentiment Agent."""

    report_type: str = "news_sentiment_report"


class NewsSentimentAgentToolResult(BaseModel):
    source: str
    value: dict = Field(default_factory=dict)
