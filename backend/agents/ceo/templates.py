"""CEO Agent response templates."""

from __future__ import annotations

from typing import Any


def research_memo_template(*, request: str, findings: list[str], evidence_refs: list[str]) -> dict[str, Any]:
    return {
        "memo_type": "research_memo",
        "request": request,
        "findings": findings,
        "evidence_refs": evidence_refs,
        "next_step": "Convert supported findings into a strategy specification or reject weak ideas.",
    }


def strategy_proposal_template(*, request: str, recommendation: str, evidence_refs: list[str]) -> dict[str, Any]:
    return {
        "memo_type": "strategy_proposal",
        "request": request,
        "recommendation": recommendation,
        "evidence_refs": evidence_refs,
        "required_before_trading": ["strategy_review", "backtest", "risk_review", "paper_trading"],
    }


def backtest_report_template(*, request: str, summary: str, evidence_refs: list[str]) -> dict[str, Any]:
    return {
        "memo_type": "backtest_report",
        "request": request,
        "summary": summary,
        "evidence_refs": evidence_refs,
        "decision_options": ["reject", "revise", "robustness_test", "paper_trading_candidate"],
    }


def risk_memo_template(*, request: str, verdict: str, evidence_refs: list[str]) -> dict[str, Any]:
    return {
        "memo_type": "risk_memo",
        "request": request,
        "verdict": verdict,
        "evidence_refs": evidence_refs,
        "binding_note": "LLM risk memos are advisory. RiskGovernor remains the deterministic control.",
    }


def board_approval_request_template(*, request: str, reason: str, evidence_refs: list[str]) -> dict[str, Any]:
    return {
        "memo_type": "board_approval_request",
        "request": request,
        "reason": reason,
        "evidence_refs": evidence_refs,
        "approval_required": True,
    }


def rejection_template(*, request: str, reason: str, evidence_refs: list[str]) -> dict[str, Any]:
    return {
        "memo_type": "rejection",
        "request": request,
        "reason": reason,
        "evidence_refs": evidence_refs,
        "decision": "rejected",
    }


def blocked_by_risk_template(*, request: str, reason: str, evidence_refs: list[str]) -> dict[str, Any]:
    return {
        "memo_type": "blocked_by_risk",
        "request": request,
        "reason": reason,
        "evidence_refs": evidence_refs,
        "decision": "blocked",
        "resume_requirement": "Human Board approval and RiskGovernor clearance are required before proceeding.",
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
