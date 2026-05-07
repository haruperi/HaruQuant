"""Evaluator."""

from __future__ import annotations

from agents.risk.shared.risk_agent import evaluate_risk_agent_output


def evaluate_response(output: dict[str, object]) -> dict[str, object]:
    return evaluate_risk_agent_output(output, "risk_limit_audit")
