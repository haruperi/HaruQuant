"""CEO refusal rules for unsafe executive requests."""

REFUSAL_RULES = {
    "bypass_risk_governor": ("bypass risk", "bypass riskgovernor", "ignore riskgovernor"),
    "bypass_kill_switch": ("bypass kill switch", "ignore kill switch"),
    "hide_audit_or_losses": ("hide audit", "delete audit", "hide loss", "hide broker error"),
    "execute_without_approval": ("without approval", "no approval token", "ignore board"),
    "fabricate_evidence": ("fake backtest", "fabricate", "invent performance"),
    "deploy_unreviewed_live": ("deploy unreviewed", "skip review", "skip paper"),
    "planner_public_action": ("planner agent execute", "planner should trade", "ask planner directly"),
}


def refusal_reasons(request: str) -> list[str]:
    lowered = request.lower()
    return [rule for rule, terms in REFUSAL_RULES.items() if any(term in lowered for term in terms)]


def build_refusal(*, request: str, reasons: list[str]) -> dict:
    return {
        "memo_type": "rejection",
        "request": request,
        "decision": "rejected",
        "reasons": reasons,
        "policy_basis": "Executive refusal policy",
        "safer_alternative": "Use a governed workflow with evidence, RiskGovernor review, audit logging, and Board approval where required.",
        "next_valid_workflow_step": "Create a governed action draft or request evidence review.",
    }
