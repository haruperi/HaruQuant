"""Evaluator for Planner Agent route plans."""

from .deterministic_policy import validate_agent_plan


def evaluate_plan(plan) -> dict:
    policy = validate_agent_plan(plan)
    checks = {
        "has_intent": bool(plan.intent),
        "has_allowed_agents": bool(plan.allowed_agents),
        "has_expected_outputs": bool(plan.expected_outputs),
        "has_evidence_requirements": bool(plan.evidence_requirements),
        "policy_valid": policy["valid"],
    }
    return {"passed": all(checks.values()), "checks": checks, "policy": policy}


__all__ = ["evaluate_plan"]
