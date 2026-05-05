"""Structured tool call and result models for native LLM function calling."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from haruquant.utils import logger

@dataclass(frozen=True)
class ToolCall:
    """A single tool call request from the LLM."""
    tool_call_id: str
    tool_name: str
    parameters: dict[str, Any]
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class ToolResult:
    """Result from a tool invocation."""
    tool_call_id: str
    tool_name: str
    output: str
    error: str | None = None
    is_error: bool = False
    token_count: int = 0
    latency_ms: int = 0
