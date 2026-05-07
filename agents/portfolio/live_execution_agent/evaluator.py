def evaluate_response(result) -> dict:
    checks = {"has_status": bool(result.status), "has_output": isinstance(result.output, dict)}
    return {"passed": all(checks.values()), "checks": checks}
