"""Shared evaluation helpers for HaruQuant agents."""

from __future__ import annotations

from agents._shared.base_contracts import AgentResponse, AgentStatus


def evaluate_response_envelope(response: AgentResponse) -> dict[str, object]:
    checks = {
        "has_request_id": bool(response.request_id),
        "has_agent_name": bool(response.agent_name),
        "status_valid": response.status in AgentStatus,
        "has_decision": bool(response.decision.decision),
        "has_audit": bool(response.audit),
    }
    return {"passed": all(checks.values()), "checks": checks}


__all__ = ["evaluate_response_envelope"]
