"""Span model with nested hierarchy (Playbook §16)."""

from __future__ import annotations

import time
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional


@dataclass
class Span:
    """A span within a trace, supporting parent-child nesting."""
    span_id: str = ""
    parent_span_id: Optional[str] = None
    trace_id: str = ""
    name: str = ""
    start_time: float = 0.0
    end_time: float = 0.0
    duration_ms: float = 0.0
    status: str = ""
    attributes: Dict[str, Any] = field(default_factory=dict)
    events: List[Dict[str, Any]] = field(default_factory=list)
    children: List["Span"] = field(default_factory=list)

    def start(self) -> None:
        self.start_time = time.monotonic()

    def end(self, status: str = "ok") -> None:
        self.end_time = time.monotonic()
        self.duration_ms = (self.end_time - self.start_time) * 1000
        self.status = status

    def add_child(self, child: "Span") -> None:
        child.parent_span_id = self.span_id
        child.trace_id = self.trace_id
        self.children.append(child)

    def add_event(self, name: str, **kwargs: Any) -> None:
        self.events.append({"name": name, "timestamp": time.monotonic(), **kwargs})

    def to_dict(self) -> Dict[str, Any]:
        return {
            "span_id": self.span_id,
            "parent_span_id": self.parent_span_id,
            "trace_id": self.trace_id,
            "name": self.name,
            "start_time": self.start_time,
            "end_time": self.end_time,
            "duration_ms": self.duration_ms,
            "status": self.status,
            "attributes": self.attributes,
            "events": self.events,
            "children_count": len(self.children),
        }
