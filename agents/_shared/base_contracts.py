"""Shared contracts used by HaruQuant agents."""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Any

from pydantic import BaseModel, Field


class AgentStatus(str, Enum):
    SUCCESS = "success"
    REJECTED = "rejected"
    NEEDS_MORE_CONTEXT = "needs_more_context"
    ERROR = "error"


class ConfidenceLevel(str, Enum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"


class RiskLevel(str, Enum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class EvidenceItem(BaseModel):
    source: str
    description: str
    value: Any | None = None
    confidence: ConfidenceLevel = ConfidenceLevel.MEDIUM


class AgentRequest(BaseModel):
    request_id: str
    user_id: str = "operator"
    agent_name: str
    task: str
    payload: dict[str, Any] = Field(default_factory=dict)
    constraints: dict[str, Any] = Field(default_factory=dict)


class AgentContext(BaseModel):
    session_id: str | None = None
    portfolio_state: dict[str, Any] = Field(default_factory=dict)
    market_state: dict[str, Any] = Field(default_factory=dict)
    strategy_state: dict[str, Any] = Field(default_factory=dict)
    risk_state: dict[str, Any] = Field(default_factory=dict)
    page_context: dict[str, Any] = Field(default_factory=dict)


class LLMAnalysis(BaseModel):
    summary: str
    observations: list[str] = Field(default_factory=list)
    risks: list[str] = Field(default_factory=list)
    suggestions: list[str] = Field(default_factory=list)
    raw_model_output: str | None = None


class AgentDecision(BaseModel):
    status: AgentStatus
    decision: str
    confidence: ConfidenceLevel
    risk_level: RiskLevel
    allowed_actions: list[str] = Field(default_factory=list)
    blocked_actions: list[str] = Field(default_factory=list)
    reasons: list[str] = Field(default_factory=list)


class AgentResponse(BaseModel):
    request_id: str
    agent_name: str
    status: AgentStatus
    evidence: list[EvidenceItem] = Field(default_factory=list)
    llm_analysis: LLMAnalysis | None = None
    decision: AgentDecision
    artifacts: dict[str, Any] = Field(default_factory=dict)
    audit: dict[str, Any] = Field(default_factory=dict)


@dataclass(frozen=True)
class AgentRunContext:
    workflow_id: str
    task_id: str
    user_request: str
    actor_id: str = "operator"
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class AgentRunResult:
    agent_name: str
    status: str
    output: dict[str, Any] = field(default_factory=dict)
    observations: list[dict[str, Any]] = field(default_factory=list)
    decisions: list[dict[str, Any]] = field(default_factory=list)
    evidence_refs: list[str] = field(default_factory=list)
    failure_reason: str | None = None


__all__ = [
    "AgentContext",
    "AgentDecision",
    "AgentRequest",
    "AgentResponse",
    "AgentRunContext",
    "AgentRunResult",
    "AgentStatus",
    "ConfidenceLevel",
    "EvidenceItem",
    "LLMAnalysis",
    "RiskLevel",
]
