"""CEO-facing memo templates for the HaruQuant agentic firm."""

from __future__ import annotations

from typing import Any

from agents.executive.ceo_agent.shared.response_templates import (
    clarification_template,
    governed_action_draft_template,
    portfolio_memo_template,
)


CEO_POLICY_REFERENCES = (
    "docs/agentic_firm/constitution.md",
    "docs/agentic_firm/risk_policy.md",
    "docs/agentic_firm/agent_permissions.md",
    "docs/agentic_firm/strategy_lifecycle.md",
)

CEO_SYSTEM_INSTRUCTIONS = """
You are HaruQuant AI, the single operator-facing interface for the agentic trading firm.
You act as a CEO/CIO-style orchestrator: clarify goals, delegate work to specialist departments,
require evidence, synthesize final investment memos, and escalate live capital, risk-threshold,
deployment, lifecycle, and policy decisions to the Human Board.

You are not an execution engine. You do not place live trades directly, bypass the RiskGovernor,
alter audit records, change risk thresholds, skip lifecycle gates, or approve your own live deployment.
All live trading, execution, and capital allocation requests require deterministic governance checks,
RiskGovernor approval where applicable, immutable audit logging, and Human Board approval.
""".strip()

CEO_PROMPT_MARKDOWN = """
# HaruQuant CEO Agent

You are HaruQuant AI, the CEO/CIO-style coordinator for the agentic trading firm.

You receive every chat request first. You may clarify, plan, delegate to specialist agents, read approved tools, synthesize final memos, prepare governed drafts, and ask for Human Board approval.

You must not place live trades, bypass RiskGovernor, bypass tool permissions, change risk thresholds, alter audit records, approve your own deployment, or execute any side effect directly from free-form chat.

Prefer current HaruQuant system state over durable chat memory. Treat page context as ephemeral unless the operator explicitly pins it.
""".strip()


def research_memo_template(*, request: str, planner_intent: str, evidence_refs: list[str] | None = None) -> dict[str, Any]:
    return {
        "memo_type": "research_memo",
        "request": request,
        "decision": "research_completed",
        "summary": "Research department work has been routed and evidence must remain attached before any strategy or execution decision.",
        "planner_intent": planner_intent,
        "evidence_refs": evidence_refs or [],
    }


def strategy_proposal_template(*, request: str, evidence_refs: list[str] | None = None) -> dict[str, Any]:
    return {
        "memo_type": "strategy_proposal",
        "request": request,
        "decision": "continue_research_and_validation",
        "summary": "The CEO recommends progressing through strategy specification, review, backtest, and risk review before any deployment.",
        "required_evidence": ["strategy_spec", "strategy_review", "backtest_summary", "risk_review", "audit_trace"],
        "evidence_refs": evidence_refs or [],
    }


def backtest_report_template(*, request: str, evidence_refs: list[str] | None = None) -> dict[str, Any]:
    return {
        "memo_type": "backtest_report",
        "request": request,
        "decision": "diagnose_before_promotion",
        "summary": "Backtest findings require diagnostics, assumptions review, and risk interpretation before lifecycle promotion.",
        "evidence_refs": evidence_refs or [],
    }


def risk_memo_template(*, request: str, evidence_refs: list[str] | None = None) -> dict[str, Any]:
    return {
        "memo_type": "risk_memo",
        "request": request,
        "decision": "risk_review_required",
        "summary": "Risk review must reference policy thresholds, exposure, drawdown, and RiskGovernor constraints.",
        "policy_reference": "docs/agentic_firm/risk_policy.md",
        "evidence_refs": evidence_refs or [],
    }


def board_approval_request_template(*, request: str, reason: str, evidence_refs: list[str] | None = None) -> dict[str, Any]:
    return {
        "memo_type": "board_approval_request",
        "request": request,
        "decision": "escalate_to_board",
        "reason": reason,
        "resume_requirement": "Human Board approval and a valid RiskGovernor approval record are required before proceeding.",
        "evidence_refs": evidence_refs or [],
    }


def rejection_template(*, request: str, reason: str) -> dict[str, Any]:
    return {
        "memo_type": "rejection",
        "request": request,
        "decision": "rejected",
        "reason": reason,
    }


def blocked_by_risk_template(*, request: str, reason: str, evidence_refs: list[str] | None = None) -> dict[str, Any]:
    return {
        "memo_type": "blocked_by_risk",
        "request": request,
        "decision": "blocked",
        "reason": reason,
        "resume_requirement": "Human Board approval and RiskGovernor approval are required before this can resume.",
        "evidence_refs": evidence_refs or [],
    }


__all__ = [
    "backtest_report_template",
    "blocked_by_risk_template",
    "board_approval_request_template",
    "CEO_PROMPT_MARKDOWN",
    "CEO_POLICY_REFERENCES",
    "CEO_SYSTEM_INSTRUCTIONS",
    "clarification_template",
    "governed_action_draft_template",
    "portfolio_memo_template",
    "rejection_template",
    "research_memo_template",
    "risk_memo_template",
    "strategy_proposal_template",
]
