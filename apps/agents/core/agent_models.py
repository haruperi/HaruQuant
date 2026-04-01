"""Shared contracts for agent tasks, tool metadata, and structured results."""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from typing import Any, Dict, List, Optional


@dataclass(frozen=True)
class AgentTask:
    """Normalized task envelope passed through the agent layer."""

    task_id: str
    task_type: str
    actor_user_id: int
    actor_role: str
    scope: str
    intent: str
    input_payload: Dict[str, Any] = field(default_factory=dict)
    correlation_id: str = ""
    run_id: str = ""
    approval_mode: str = "auto_read_only"

    def to_dict(self) -> Dict[str, Any]:
        """Return a JSON-serializable representation."""
        return asdict(self)


@dataclass(frozen=True)
class ToolSpec:
    """Typed description of one tool exposed to the agent layer."""

    tool_name: str
    domain: str
    mode: str
    input_schema: Dict[str, Any] = field(default_factory=dict)
    output_schema: Dict[str, Any] = field(default_factory=dict)
    permission_policy: str = "default"
    description: str = ""

    def to_dict(self) -> Dict[str, Any]:
        """Return a JSON-serializable representation."""
        return asdict(self)


@dataclass(frozen=True)
class AgentResult:
    """Structured output emitted by planners, specialists, and workflows."""

    status: str
    summary: str
    evidence: List[Dict[str, Any]] = field(default_factory=list)
    recommendations: List[Dict[str, Any]] = field(default_factory=list)
    required_actions: List[Dict[str, Any]] = field(default_factory=list)
    warnings: List[str] = field(default_factory=list)
    confidence: float = 0.0
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        """Return a JSON-serializable representation."""
        return asdict(self)


@dataclass(frozen=True)
class ToolCallRecord:
    """Audit-friendly record of one logical tool call."""

    tool_name: str
    mode: str
    status: str
    correlation_id: str
    input_ref: Optional[str] = None
    output_ref: Optional[str] = None
    warnings: List[str] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        """Return a JSON-serializable representation."""
        return asdict(self)
