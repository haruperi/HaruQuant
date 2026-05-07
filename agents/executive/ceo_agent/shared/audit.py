"""Executive audit helpers."""

from __future__ import annotations

from typing import Any

from agents._shared.persistence import utc_stamp, write_json_artifact


def build_executive_audit(
    *,
    request_id: str,
    planner_output: dict[str, Any],
    departments_called: list[str],
    agents_called: list[str],
    evidence_refs: list[str],
    missing_evidence: list[str],
    decision: str,
    allowed_actions: list[str],
    blocked_actions: list[str],
) -> dict[str, Any]:
    payload = {
        "request_id": request_id,
        "agent_name": "ceo",
        "ceo_agent_version": "executive_ceo_v1",
        "planner_agent_version": str(planner_output.get("planner_source", "internal_planner_v1")),
        "planner_called": True,
        "planner_plan_id": planner_output.get("conversation_plan_id") or planner_output.get("plan_id"),
        "workflow_type": planner_output.get("task_class") or planner_output.get("workflow_type"),
        "departments_called": departments_called,
        "agents_called": agents_called,
        "tools_called": planner_output.get("backend_tools_to_run", []),
        "evidence_refs": evidence_refs,
        "missing_evidence": missing_evidence,
        "llm_used": False,
        "model_provider": "none",
        "model_name": "deterministic",
        "fallback_used": False,
        "permission_profile": "executive_operator_v1",
        "policy_version": "executive_ceo_policy_v1",
        "prompt_version": "ceo_agent_prompt_v1",
        "board_escalation_required": bool(planner_output.get("requires_board_approval")),
        "risk_governor_required": bool(planner_output.get("requires_risk_governor")),
        "human_confirmation_required": bool(planner_output.get("requires_board_approval")),
        "allowed_actions": allowed_actions,
        "blocked_actions": blocked_actions,
        "final_decision": decision,
        "error_if_any": None,
    }
    payload["audit_ref"] = write_json_artifact("reports/logs/executive", f"ceo-{utc_stamp()}.json", payload)
    return payload
