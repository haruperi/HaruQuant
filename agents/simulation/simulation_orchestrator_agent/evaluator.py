"""Evaluator for Simulation Orchestrator responses."""

from __future__ import annotations

from agents._shared.base_contracts import AgentResponse
from agents.simulation.shared.simulation_agent import evaluate_simulation_response


def evaluate_response(response: AgentResponse) -> dict[str, object]:
    return evaluate_simulation_response(response, "simulation_orchestrator")
