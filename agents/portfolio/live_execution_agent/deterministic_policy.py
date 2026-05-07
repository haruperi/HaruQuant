"""Deterministic policy helpers for live execution."""


def evaluate_live_execution_gates(request: dict) -> list[str]:
    failures: list[str] = []
    if not request.get("live_mode_enabled", False):
        failures.append("live_mode_disabled")
    if request.get("strategy_state") not in {"micro_live", "limited_live", "normal_live", "live"}:
        failures.append("strategy_not_live")
    if not request.get("approval_token"):
        failures.append("approval_token_missing")
    if request.get("kill_switch_status") != "healthy":
        failures.append("kill_switch_triggered")
    if request.get("broker_heartbeat") != "healthy":
        failures.append("broker_heartbeat_failed")
    if not request.get("audit_logging_available", True):
        failures.append("audit_logging_unavailable")
    if request.get("risk_governor_available", True) is not True:
        failures.append("risk_governor_unavailable")
    return failures
