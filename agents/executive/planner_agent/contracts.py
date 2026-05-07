"""Contracts for the Planner Agent."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol


class RequestClassifier(Protocol):
    def classify(self, *, user_request: str, route_catalog: dict[str, "RouteDefinition"]) -> str | None:
        ...


@dataclass(frozen=True)
class RouteDefinition:
    intent: str
    allowed_agents: list[str]
    expected_outputs: list[str]
    response_mode: str = "governed_artifact"
    task_class: str | None = None
    artifact_expected: bool = True
    risk_level: str = "low"
    requires_board_approval: bool = False
    requires_risk_governor: bool = False
    context_needed: list[str] | None = None
    backend_tools_to_run: list[str] | None = None
    attached_tools: list[str] | None = None
    page_actions_to_plan: list[str] | None = None
    evidence_requirements: list[str] | None = None
    blocked_agents: list[str] | None = None
    needs_clarification: bool = False


__all__ = ["RequestClassifier", "RouteDefinition"]
