"""Cost tracking per trace and span (Playbook §17)."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional


@dataclass
class CostEntry:
    trace_id: str = ""
    span_id: str = ""
    model: str = ""
    input_tokens: int = 0
    output_tokens: int = 0
    cost_usd: float = 0.0


class CostTracker:
    """Track and aggregate costs per trace and span."""

    def __init__(self, cost_per_input_token: float = 0.0, cost_per_output_token: float = 0.0) -> None:
        self._entries: List[CostEntry] = []
        self._cost_per_input_token = cost_per_input_token
        self._cost_per_output_token = cost_per_output_token

    def record(
        self,
        trace_id: str,
        span_id: str = "",
        model: str = "",
        input_tokens: int = 0,
        output_tokens: int = 0,
    ) -> CostEntry:
        cost = (input_tokens * self._cost_per_input_token) + (
            output_tokens * self._cost_per_output_token
        )
        entry = CostEntry(
            trace_id=trace_id,
            span_id=span_id,
            model=model,
            input_tokens=input_tokens,
            output_tokens=output_tokens,
            cost_usd=cost,
        )
        self._entries.append(entry)
        return entry

    def total_cost(self, trace_id: str = "") -> float:
        if trace_id:
            return sum(e.cost_usd for e in self._entries if e.trace_id == trace_id)
        return sum(e.cost_usd for e in self._entries)

    def total_tokens(self, trace_id: str = "") -> Dict[str, int]:
        if trace_id:
            entries = [e for e in self._entries if e.trace_id == trace_id]
        else:
            entries = self._entries
        return {
            "input": sum(e.input_tokens for e in entries),
            "output": sum(e.output_tokens for e in entries),
        }

    def entries(self, trace_id: str = "") -> List[CostEntry]:
        if trace_id:
            return [e for e in self._entries if e.trace_id == trace_id]
        return list(self._entries)

    @property
    def entry_count(self) -> int:
        return len(self._entries)

    def clear(self) -> None:
        self._entries.clear()
