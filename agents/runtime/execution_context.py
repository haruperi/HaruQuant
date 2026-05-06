"""Execution context for HaruQuant agents."""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, Optional, Tuple


@dataclass(frozen=True)
class AgentExecutionContext:
    workflow_id: str
    correlation_id: str
    session_id: Optional[str] = None
    model: Optional[str] = None
    allowed_tools: Tuple[str, ...] = field(default_factory=tuple)
    prompt_version_id: Optional[str] = None
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class AgentExecutionResult:
    workflow_id: str
    correlation_id: str
    agent_name: str
    status: str
    output_payload: Dict[str, Any]
    tool_calls: list[dict[str, Any]] = field(default_factory=list)
    latency_ms: int = 0
    metadata: Dict[str, Any] = field(default_factory=dict)
