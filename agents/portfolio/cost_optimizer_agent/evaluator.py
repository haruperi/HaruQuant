def evaluate_response(result) -> dict:
    checks = {"has_agent_name": bool(result.agent_name), "has_status": bool(result.status), "has_output": isinstance(result.output, dict), "has_audit": bool(result.output.get("audit_ref"))}
    return {"passed": all(checks.values()), "checks": checks}
