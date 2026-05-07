"""Contracts for the CEO Agent."""

from __future__ import annotations

from typing import Any, Protocol

from agents._shared.schemas import AgentPlan


class CEOResponseSynthesizer(Protocol):
    def synthesize(
        self,
        *,
        request: str,
        planner_result: AgentPlan,
        agent_outputs: dict[str, Any],
        evidence_refs: list[str],
    ) -> tuple[str, str]:
        ...


__all__ = ["CEOResponseSynthesizer"]
