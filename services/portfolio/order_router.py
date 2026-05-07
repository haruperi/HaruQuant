"""Deterministic order router for guarded live execution."""
from __future__ import annotations
from datetime import datetime, timezone
from typing import Any
from agents._shared.persistence import utc_stamp, write_json_artifact

class OrderRouter:
    component_name = "order_router"
    def route_order(self, *, order: dict[str, Any], approval_token: dict[str, Any] | None, live_config: dict[str, Any], broker_status: dict[str, Any], kill_switch_status: str) -> dict[str, Any]:
        reasons: list[str] = []
        if not approval_token:
            reasons.append("missing_risk_approval_token")
        elif approval_token.get("decision") not in {"approved", "approved_with_reduced_size"}:
            reasons.append("risk_approval_not_approved")
        if not live_config.get("global_live_mode", False):
            reasons.append("live_mode_disabled")
        strategy_config = live_config.get("strategies", {}).get(order.get("strategy_id"), {})
        if strategy_config.get("state") not in {"micro_live", "limited_live", "normal_live", "live"}:
            reasons.append("strategy_not_live")
        if kill_switch_status != "healthy":
            reasons.append("kill_switch_not_healthy")
        if broker_status.get("heartbeat") != "healthy":
            reasons.append("broker_heartbeat_failed")
        if order.get("side") not in {"buy", "sell"}:
            reasons.append("mismatched_side")
        result = {"status": "rejected" if reasons else "accepted", "reasons": reasons, "order": order, "timestamp": datetime.now(timezone.utc).isoformat()}
        result["audit_uri"] = write_json_artifact("reports/logs/execution", f"order-router-{utc_stamp()}.json", result)
        return result
