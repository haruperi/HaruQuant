from agents.portfolio.shared.contracts import AuditFinding
def audit_policy(records: list[dict]) -> list[AuditFinding]:
    findings: list[AuditFinding] = []
    for record in records:
        if record.get("live_order") and not record.get("risk_approval_token"):
            findings.append(AuditFinding(severity="critical", rule="live_order_requires_risk_token", message="Live order is missing RiskGovernor approval token.", affected_ref=record.get("order_id"), disables_live_trading=True))
        if record.get("direct_bridge_call"):
            findings.append(AuditFinding(severity="critical", rule="order_router_only_bridge_access", message="Broker bridge was called outside Order Router.", affected_ref=record.get("order_id"), disables_live_trading=True))
        if record.get("audit_missing"):
            findings.append(AuditFinding(severity="major", rule="audit_record_required", message="Required audit record is missing.", affected_ref=record.get("order_id")))
    return findings or [AuditFinding(severity="info", rule="portfolio_audit_complete", message="No audit violations detected.")]
