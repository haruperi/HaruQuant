"""CEO-facing memo templates for the HaruQuant agentic firm."""

from __future__ import annotations

from typing import Any


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
    "rejection_template",
    "research_memo_template",
    "risk_memo_template",
    "strategy_proposal_template",
]
