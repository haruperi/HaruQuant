"""Deterministic policy helpers for the existing Planner Agent."""

from __future__ import annotations

from agents._shared.schemas import AgentPlan
from agents.executive.ceo_agent.shared.routing import forbidden_tools, unknown_workflow


def validate_agent_plan(plan: AgentPlan) -> dict:
    reasons: list[str] = []
    if unknown_workflow(plan.intent) and unknown_workflow(plan.task_class):
        reasons.append("unknown_workflow")
    blocked_tools = forbidden_tools(plan.backend_tools_to_run)
    if blocked_tools:
        reasons.append("forbidden_backend_tools")
    if plan.intent == "execution_proposal" and not plan.requires_risk_governor:
        reasons.append("execution_requires_risk_governor")
    if plan.requires_board_approval and not plan.requires_audit_log:
        reasons.append("board_workflow_requires_audit")
    return {"valid": not reasons, "reasons": reasons or ["planner_policy_valid"], "blocked_tools": blocked_tools}


__all__ = ["validate_agent_plan"]
