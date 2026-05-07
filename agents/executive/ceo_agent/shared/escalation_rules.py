"""Board escalation rules enforced by CEO deterministic policy."""

BOARD_ESCALATION_TERMS = {
    "enable_live_trading": ("enable live", "live mode", "go live"),
    "connect_live_broker": ("connect broker", "broker activation", "live broker"),
    "promote_to_micro_live": ("promote", "micro-live", "micro live"),
    "increase_live_allocation": ("increase allocation", "increase capital", "scale live"),
    "retire_live_strategy": ("retire live", "retire strategy"),
    "change_risk_thresholds": ("risk threshold", "change risk", "raise risk"),
    "override_kill_switch": ("override kill switch", "reset kill switch"),
    "critical_incident_recovery": ("resume after incident", "critical incident"),
    "production_deployment": ("deploy live", "production deploy"),
}


def board_escalation_reasons(request: str, *, risk_level: str = "low") -> list[str]:
    lowered = request.lower()
    reasons = [name for name, terms in BOARD_ESCALATION_TERMS.items() if any(term in lowered for term in terms)]
    if risk_level == "critical":
        reasons.append("critical_risk_workflow")
    return list(dict.fromkeys(reasons))


def build_board_escalation_packet(*, request: str, reasons: list[str], evidence_refs: list[str]) -> dict:
    return {
        "decision_required": "Human Board approval",
        "proposed_action": request,
        "escalation_reasons": reasons,
        "evidence_reviewed": evidence_refs,
        "risk_governor_status": "required_before_action",
        "expected_benefit": "Requires operator-supplied business case.",
        "key_risks": ["capital_loss", "policy_breach", "operational_incident"],
        "worst_case_impact": "Live capital or audit integrity could be affected.",
        "rollback_plan": "Keep live execution disabled until approval and deterministic gates pass.",
        "approval_expiration": "operator_defined",
        "required_approval_fields": ["approval_id", "approver", "scope", "expires_at"],
    }
