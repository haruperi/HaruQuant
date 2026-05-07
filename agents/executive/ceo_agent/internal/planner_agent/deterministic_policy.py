"""Deterministic validation for internal Planner output."""

from __future__ import annotations

from agents.executive.ceo_agent.shared.planner_contracts import PlannerOutput
from agents.executive.ceo_agent.shared.routing import forbidden_tools, unknown_workflow


def validate_planner_output(output: PlannerOutput) -> dict:
    reasons: list[str] = []
    if unknown_workflow(output.workflow_type) and unknown_workflow(output.intent):
        reasons.append("unknown_workflow")
    blocked_tools = forbidden_tools(output.backend_tools_to_run)
    if blocked_tools:
        reasons.append("forbidden_backend_tools")
    if output.intent == "execution_proposal" and not output.requires_risk_governor:
        reasons.append("execution_requires_risk_governor")
    if output.requires_board_approval and not output.requires_human_confirmation:
        reasons.append("board_approval_requires_human_confirmation")
    return {
        "valid": not reasons,
        "reasons": reasons or ["planner_output_valid"],
        "blocked_tools": blocked_tools,
    }
