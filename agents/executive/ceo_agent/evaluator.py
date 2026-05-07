"""Evaluator for CEO Agent outputs and governance boundaries."""

from __future__ import annotations

from typing import Any


def evaluate_ceo_response(response: Any) -> dict:
    data = response.model_dump() if hasattr(response, "model_dump") else response
    audit = data.get("audit", {}) if isinstance(data, dict) else {}
    decision = data.get("decision", {}) if isinstance(data, dict) else {}
    blocked = decision.get("blocked_actions", []) if isinstance(decision, dict) else getattr(decision, "blocked_actions", [])
    checks = {
        "has_response_envelope": isinstance(data, dict),
        "has_planner_output": bool(data.get("planner_output")) if isinstance(data, dict) else False,
        "has_final_memo": bool(data.get("final_memo")) if isinstance(data, dict) else False,
        "has_decision": bool(decision),
        "has_audit": bool(audit),
        "execution_blocked": "place_trade" in blocked,
        "risk_approval_blocked": "approve_risk" in blocked,
        "llm_not_final_decision": audit.get("llm_used") in {False, None},
    }
    return {"passed": all(checks.values()), "checks": checks}


__all__ = ["evaluate_ceo_response"]
