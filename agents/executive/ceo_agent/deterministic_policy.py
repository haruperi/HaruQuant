"""Deterministic policy for CEO Agent executive decisions."""

from __future__ import annotations

from typing import Any

from agents._shared.schemas import AgentPlan
from agents.executive.ceo_agent.shared.escalation_rules import board_escalation_reasons
from agents.executive.ceo_agent.shared.evidence_requirements import missing_evidence, required_evidence_for
from agents.executive.ceo_agent.shared.executive_contracts import ExecutiveDecision
from agents.executive.ceo_agent.shared.refusal_rules import refusal_reasons
from agents.executive.ceo_agent.shared.routing import forbidden_tools


CEO_ALLOWED_ACTIONS = [
    "answer_general_question",
    "summarize_evidence",
    "delegate_research",
    "delegate_strategy_creation",
    "delegate_backtest",
    "delegate_risk_review",
    "delegate_portfolio_review",
    "delegate_reporting",
    "create_governed_action_draft",
    "create_board_approval_request",
    "request_clarification",
    "refuse_unsafe_request",
]

CEO_BLOCKED_ACTIONS = [
    "place_trade",
    "close_position_directly",
    "cancel_order_directly",
    "approve_risk",
    "override_risk_governor",
    "override_kill_switch",
    "enable_live_trading_directly",
    "increase_live_allocation_without_board_approval",
    "modify_risk_thresholds_without_governance",
    "delete_audit_logs",
    "hide_evidence",
    "call_planner_publicly",
]


def make_executive_decision(
    *,
    request: str,
    planner_result: AgentPlan | None,
    evidence_refs: list[str] | None = None,
    tools_used: list[str] | None = None,
    specialist_responses: dict[str, Any] | None = None,
) -> ExecutiveDecision:
    evidence_refs = evidence_refs or []
    tools_used = tools_used or []
    specialist_responses = specialist_responses or {}
    reasons: list[str] = []
    blocked_actions = list(CEO_BLOCKED_ACTIONS)

    refusal = refusal_reasons(request)
    if refusal:
        return ExecutiveDecision(
            status="rejected",
            decision_type="refusal",
            decision="refuse_unsafe_request",
            confidence="high",
            risk_level="critical",
            blocked_actions=blocked_actions,
            reasons=refusal,
        )

    if planner_result is None:
        return ExecutiveDecision(
            status="needs_more_context",
            decision_type="planner_missing",
            decision="request_clarification",
            confidence="high",
            risk_level="medium",
            allowed_actions=["request_clarification"],
            blocked_actions=blocked_actions,
            reasons=["planner_output_missing"],
        )

    bad_tools = forbidden_tools(tools_used + list(planner_result.backend_tools_to_run))
    if bad_tools:
        return ExecutiveDecision(
            status="blocked",
            decision_type="forbidden_tool_block",
            decision="block_forbidden_tools",
            confidence="high",
            risk_level="critical",
            blocked_actions=blocked_actions + bad_tools,
            reasons=["planner_or_ceo_proposed_forbidden_tool"],
        )

    required = list(planner_result.evidence_requirements or required_evidence_for(planner_result.intent))
    missing = missing_evidence(required, evidence_refs)
    if planner_result.intent not in {"ceo_answer", "ceo_identity", "clarification", "page_action"} and missing:
        return ExecutiveDecision(
            status="needs_more_context",
            decision_type="missing_evidence",
            decision="request_more_evidence",
            confidence="high",
            risk_level=planner_result.risk_level,
            allowed_actions=["request_clarification", "summarize_evidence"],
            blocked_actions=blocked_actions,
            reasons=["required_evidence_missing"],
            required_evidence=required,
            missing_evidence=missing,
            requires_board_approval=planner_result.requires_board_approval,
            requires_risk_governor=planner_result.requires_risk_governor,
            requires_human_confirmation=planner_result.requires_board_approval,
        )

    escalation = board_escalation_reasons(request, risk_level=planner_result.risk_level)
    if planner_result.requires_board_approval or escalation:
        return ExecutiveDecision(
            status="blocked",
            decision_type="board_escalation",
            decision="create_board_approval_request",
            confidence="high",
            risk_level=planner_result.risk_level,
            allowed_actions=["create_board_approval_request", "create_governed_action_draft"],
            blocked_actions=blocked_actions,
            reasons=escalation or ["planner_requires_board_approval"],
            required_evidence=required,
            requires_board_approval=True,
            requires_risk_governor=planner_result.requires_risk_governor,
            requires_human_confirmation=True,
        )

    failed_specialists = [
        name
        for name, response in specialist_responses.items()
        if (response.get("status") if isinstance(response, dict) else getattr(response, "status", None)) in {"failed", "blocked", "rejected"}
    ]
    if failed_specialists:
        reasons.append("specialist_failure_or_block")

    return ExecutiveDecision(
        status="completed" if not reasons else "blocked",
        decision_type="executive_workflow",
        decision="produce_final_memo" if not reasons else "explain_blocked_workflow",
        confidence="high" if not reasons else "medium",
        risk_level=planner_result.risk_level,
        allowed_actions=CEO_ALLOWED_ACTIONS if not reasons else ["summarize_evidence", "request_clarification"],
        blocked_actions=blocked_actions,
        reasons=reasons or ["executive_policy_checks_passed"],
        required_evidence=required,
        missing_evidence=[],
        requires_board_approval=planner_result.requires_board_approval,
        requires_risk_governor=planner_result.requires_risk_governor,
        requires_human_confirmation=planner_result.requires_board_approval,
    )


__all__ = ["CEO_ALLOWED_ACTIONS", "CEO_BLOCKED_ACTIONS", "make_executive_decision"]
