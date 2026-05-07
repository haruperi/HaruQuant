from agents.portfolio.shared.contracts import AuditFinding

def test_audit_finding_serializes():
    assert AuditFinding(severity="info", rule="r", message="m").rule == "r"
