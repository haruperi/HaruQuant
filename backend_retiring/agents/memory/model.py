"""Memory data models — semantic, episodic, and procedural memory."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any


def _now() -> datetime:
    return datetime.now(timezone.utc)


@dataclass(frozen=True)
class SemanticMemory:
    """Facts, concepts, and relationships — retrieved by semantic similarity."""
    memory_id: str
    content: str
    category: str  # "market", "strategy", "risk", "compliance", ...
    embedding: list[float] = field(default_factory=list)
    importance: float = 0.5  # 0.0-1.0, determines retention priority
    created_at: datetime = field(default_factory=_now)
    last_accessed: datetime = field(default_factory=_now)
    access_count: int = 0


@dataclass(frozen=True)
class EpisodicMemory:
    """Past decisions, outcomes, and lessons — retrieved by context similarity."""
    memory_id: str
    workflow_id: str
    agent_name: str
    goal: str
    decision: str
    outcome: str  # "success", "failure", "partial"
    lesson: str | None = None
    metadata: dict[str, Any] = field(default_factory=dict)
    created_at: datetime = field(default_factory=_now)


@dataclass(frozen=True)
class ProceduralMemory:
    """How to do things — tool preferences, workflow patterns, learned shortcuts."""
    memory_id: str
    pattern_name: str
    description: str
    steps: list[str] = field(default_factory=list)
    success_rate: float = 0.0  # Historical success rate
    usage_count: int = 0
    last_used: datetime = field(default_factory=_now)
