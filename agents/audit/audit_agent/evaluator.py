def evaluate_response(result) -> dict:
    checks = {"has_findings": "findings" in result.output, "has_audit": bool(result.output.get("audit_ref"))}
    return {"passed": all(checks.values()), "checks": checks}
