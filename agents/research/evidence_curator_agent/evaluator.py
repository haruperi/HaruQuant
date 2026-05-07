"""Evaluator for the Evidence Curator Agent."""

from __future__ import annotations

from agents._shared.base_contracts import AgentResponse
from agents.research.shared.research_agent import evaluate_research_response

from .service import CONFIG


def evaluate_response(response: AgentResponse) -> dict:
    return evaluate_research_response(response, CONFIG.agent_name)
