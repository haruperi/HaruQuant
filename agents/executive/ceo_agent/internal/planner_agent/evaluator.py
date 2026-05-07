"""Evaluator for the internal Planner Agent."""

from .deterministic_policy import validate_planner_output


def evaluate_planner_output(output) -> dict:
    policy = validate_planner_output(output)
    checks = {
        "schema_valid": bool(output.plan_id and output.intent),
        "policy_valid": policy["valid"],
        "has_confidence": bool(output.confidence),
        "no_forbidden_tools": not policy["blocked_tools"],
    }
    return {"passed": all(checks.values()), "checks": checks, "policy": policy}
