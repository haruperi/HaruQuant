"""Kill switch and incident generation."""

from __future__ import annotations

from typing import Any

from agents._persistence import utc_stamp, write_json_artifact


class KillSwitchService:
    def evaluate(self, snapshot: dict[str, Any]) -> dict[str, Any]:
        triggers: list[str] = []
        checks = {
            "daily_loss": snapshot.get("daily_loss", 0.0) > snapshot.get("max_daily_loss", 0.03),
            "weekly_loss": snapshot.get("weekly_loss", 0.0) > snapshot.get("max_weekly_loss", 0.06),
            "account_drawdown": snapshot.get("account_drawdown", 0.0) > snapshot.get("max_account_drawdown", 0.12),
            "strategy_drawdown": snapshot.get("strategy_drawdown", 0.0) > snapshot.get("max_strategy_drawdown", 0.08),
            "broker_connection": snapshot.get("broker_connection", "healthy") != "healthy",
            "spread_spike": snapshot.get("spread", 0.0) > snapshot.get("max_spread", 2.0),
            "slippage_spike": snapshot.get("slippage", 0.0) > snapshot.get("max_slippage", 1.0),
            "repeated_order_failures": snapshot.get("repeated_order_failures", 0) > 2,
            "audit_logger_health": snapshot.get("audit_logger_health", "healthy") != "healthy",
            "risk_governor_health": snapshot.get("risk_governor_health", "healthy") != "healthy",
        }
        triggers = [name for name, failed in checks.items() if failed]
        status = "triggered" if triggers else "healthy"
        incident = {
            "status": status,
            "triggers": triggers,
            "disable_new_orders": bool(triggers),
            "close_positions_allowed_by_policy": bool(triggers and snapshot.get("close_positions_on_trigger", False)),
            "incident_report": None,
        }
        if triggers:
            incident["incident_report"] = write_json_artifact("reports/risk", f"kill-switch-{utc_stamp()}.json", incident)
        return incident


__all__ = ["KillSwitchService"]
