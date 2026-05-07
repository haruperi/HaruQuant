"""Evaluator for the Strategy Creation Orchestrator Agent."""

from __future__ import annotations

from agents._shared.base_contracts import AgentResponse
from agents.strategy_development.shared.strategy_agent import evaluate_strategy_response

from .service import CONFIG


def evaluate_response(response: AgentResponse) -> dict:
    return evaluate_strategy_response(response, CONFIG.agent_name)
