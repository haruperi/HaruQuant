"""User-facing executive response templates."""

from __future__ import annotations


def portfolio_memo_template(*, request: str, evidence_refs: list[str] | None = None) -> dict:
    return {
        "memo_type": "portfolio_memo",
        "request": request,
        "decision": "portfolio_review_required",
        "summary": "Portfolio decisions require lifecycle state, risk constraints, allocation evidence, execution health, and audit status.",
        "required_sections": [
            "portfolio_state",
            "strategy_lifecycle_state",
            "allocation_constraints",
            "risk_governor_constraints",
            "recommended_changes",
            "board_approval_requirement",
        ],
        "evidence_refs": evidence_refs or [],
    }


def clarification_template(*, missing_inputs: list[str]) -> dict:
    return {
        "memo_type": "clarification",
        "decision": "needs_more_context",
        "what_is_missing": missing_inputs,
        "why_it_matters": "The CEO cannot safely route or conclude the workflow without these fields.",
        "safe_default_option": "Start with an informational review and no live-side effects.",
    }


def governed_action_draft_template(*, request: str, evidence_refs: list[str] | None = None) -> dict:
    return {
        "memo_type": "governed_action_draft",
        "request": request,
        "decision": "draft_only",
        "summary": "This is a governed draft. It is not an approval and does not execute any action.",
        "required_gates": ["RiskGovernor", "audit_logging", "Board approval if live capital or live execution is affected"],
        "evidence_refs": evidence_refs or [],
    }
