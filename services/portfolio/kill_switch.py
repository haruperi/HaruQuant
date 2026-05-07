"""Portfolio kill switch with fail-closed live execution controls."""
from __future__ import annotations
from datetime import datetime, timezone
from typing import Any
from agents._shared.persistence import utc_stamp, write_json_artifact

class PortfolioKillSwitch:
    def __init__(self) -> None:
        self.state = "healthy"
        self.trigger_reason: str | None = None
        self.triggered_at: str | None = None
    def evaluate(self, snapshot: dict[str, Any]) -> dict[str, Any]:
        triggers = [name for name, active in {
            "critical_audit_failure": snapshot.get("critical_audit_failure"),
            "risk_governor_unavailable": snapshot.get("risk_governor_available", True) is False,
            "audit_logging_unavailable": snapshot.get("audit_logging_available", True) is False,
            "broker_heartbeat_failed": snapshot.get("broker_heartbeat") == "failed",
        }.items() if active]
        return self.trigger(";".join(triggers)) if triggers else {"state": self.state, "triggered": self.state != "healthy", "reason": self.trigger_reason}
    def trigger(self, reason: str) -> dict[str, Any]:
        self.state, self.trigger_reason, self.triggered_at = "triggered", reason, datetime.now(timezone.utc).isoformat()
        payload = {"state": self.state, "triggered": True, "reason": reason, "triggered_at": self.triggered_at, "resume_allowed": False}
        payload["audit_uri"] = write_json_artifact("reports/logs/portfolio", f"kill-switch-{utc_stamp()}.json", payload)
        return payload
    def resume(self, *, approval_id: str | None = None) -> dict[str, Any]:
        if not approval_id:
            return {"state": self.state, "status": "blocked", "reason": "resume_requires_approval"}
        self.state, self.trigger_reason, self.triggered_at = "healthy", None, None
        return {"state": self.state, "status": "resumed", "approval_id": approval_id}
