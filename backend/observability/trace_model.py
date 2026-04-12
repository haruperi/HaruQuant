"""Trace model with full field coverage (Playbook §16)."""

from __future__ import annotations

import time
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional


@dataclass
class Trace:
    """Full observability trace for a workflow execution."""
    trace_id: str = ""
    session_id: str = ""
    user_id: Optional[int] = None
    tenant_id: Optional[str] = None
    request_id: str = ""
    task_id: str = ""
    workflow_id: str = ""
    step_id: str = ""
    tool_call_id: str = ""
    agent_name: str = ""
    prompt_version: str = ""
    model_name: str = ""
    model_version: str = ""
    latency_ms: float = 0.0
    cost: float = 0.0
    result_status: str = ""
    attributes: Dict[str, Any] = field(default_factory=dict)
    events: List[Dict[str, Any]] = field(default_factory=list)
    _start_time: float = field(default_factory=time.monotonic, repr=False)

    def start(self) -> None:
        self._start_time = time.monotonic()

    def end(self) -> None:
        self.latency_ms = (time.monotonic() - self._start_time) * 1000

    def add_event(self, name: str, **kwargs: Any) -> None:
        self.events.append({"name": name, **kwargs})

    def to_dict(self) -> Dict[str, Any]:
        d = {
            "trace_id": self.trace_id,
            "session_id": self.session_id,
            "user_id": self.user_id,
            "tenant_id": self.tenant_id,
            "request_id": self.request_id,
            "task_id": self.task_id,
            "workflow_id": self.workflow_id,
            "step_id": self.step_id,
            "tool_call_id": self.tool_call_id,
            "agent_name": self.agent_name,
            "prompt_version": self.prompt_version,
            "model_name": self.model_name,
            "model_version": self.model_version,
            "latency_ms": self.latency_ms,
            "cost": self.cost,
            "result_status": self.result_status,
        }
        d.update(self.attributes)
        return d
