"""Evaluator for Optimization Comparator Agent responses."""

from __future__ import annotations

from agents._shared.base_contracts import AgentResponse
from agents.simulation.shared.simulation_agent import evaluate_simulation_response


def evaluate_response(response: AgentResponse) -> dict[str, object]:
    return evaluate_simulation_response(response, "optimization_comparator_agent")
