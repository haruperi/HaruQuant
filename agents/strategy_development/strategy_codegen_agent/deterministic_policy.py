"""Deterministic policy for the Strategy Codegen Agent."""

from __future__ import annotations

from agents._shared.base_contracts import AgentDecision
from agents.strategy_development.shared.strategy_agent import build_code_package, build_strategy_spec, make_strategy_decision, parse_payload, review_package

from .service import CONFIG


def make_final_decision(request) -> AgentDecision:
    payload = parse_payload(request)
    spec = build_strategy_spec(payload, CONFIG.agent_name)
    code = build_code_package(spec)
    review = review_package(spec, code)
    return make_strategy_decision(CONFIG, payload, spec, review)
