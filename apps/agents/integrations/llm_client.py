"""Provider abstraction for the Phase 0 agent scaffold."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, Protocol


class LLMClient(Protocol):
    """Minimal interface expected by workflows that request model output."""

    def complete(self, *, prompt: str, metadata: Dict[str, Any]) -> str:
        """Return a model completion for a small prompt payload."""


@dataclass(frozen=True)
class NoOpLLMClient:
    """Deterministic provider used until a real backend is wired in."""

    provider_name: str = "noop"
    response_prefix: str = "Phase 0 scaffold response"
    fixed_fields: Dict[str, Any] = field(default_factory=dict)

    def complete(self, *, prompt: str, metadata: Dict[str, Any]) -> str:
        """Return a fixed, testable response without external dependencies."""
        task_id = metadata.get("task_id", "unknown-task")
        intent = metadata.get("intent", "unspecified")
        return f"{self.response_prefix}: task={task_id} intent={intent} prompt={prompt}"
