"""Live Execution Agent v1 with hard deterministic gates."""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

from agents._shared import AgentRunContext, AgentRunResult
from execution.order_router import OrderRouter
from risk.governor import RiskGovernor


class LiveExecutionAgent:
    agent_name = "live_execution"

    def __init__(self, *, router: OrderRouter | None = None, governor: RiskGovernor | None = None) -> None:
        self.router = router or OrderRouter()
        self.governor = governor or RiskGovernor()

    def evaluate_safety(self, *, request: dict[str, Any]) -> list[str]:
        failures: list[str] = []
        if not request.get("live_mode_enabled", False):
            failures.append("live_mode_disabled")
        if request.get("strategy_state") not in {"micro_live", "limited_live", "normal_live"}:
            failures.append("strategy_not_live")
        if not request.get("approval_token"):
            failures.append("approval_token_missing")
        elif request.get("approval_token_expired", False):
            failures.append("approval_token_expired")
        if request.get("kill_switch_status") != "healthy":
            failures.append("kill_switch_triggered")
        if request.get("broker_heartbeat") != "healthy":
            failures.append("broker_heartbeat_failed")
        if request.get("spread", 0.0) > request.get("max_spread", 2.0):
            failures.append("spread_too_high")
        if request.get("slippage", 0.0) > request.get("max_slippage", 1.0):
            failures.append("slippage_too_high")
        if not request.get("audit_logging_available", True):
            failures.append("audit_logging_unavailable")
        if request.get("risk_governor_available", True) is not True:
            failures.append("risk_governor_unavailable")
        return failures

    def run(self, *, context: AgentRunContext, task_input: dict[str, Any]) -> AgentRunResult:
        failures = self.evaluate_safety(request=task_input)
        if failures:
            return AgentRunResult(agent_name=self.agent_name, status="blocked", output={"blocked_reasons": failures})
        proposal = task_input.get("trade_proposal", {})
        risk_decision = self.governor.evaluate_trade(
            proposal=proposal,
            portfolio_snapshot=task_input.get("portfolio_snapshot", {}),
            market_snapshot=task_input.get("market_snapshot", {}),
        )
        if risk_decision.decision != "approved":
            return AgentRunResult(agent_name=self.agent_name, status="blocked", output={"risk_governor": risk_decision.__dict__})
        route = self.router.route_order(
            order=proposal,
            approval_token=risk_decision.__dict__,
            live_config=task_input.get("live_config", {}),
            broker_status={"heartbeat": task_input.get("broker_heartbeat", "failed")},
            kill_switch_status=task_input.get("kill_switch_status", "triggered"),
        )
        return AgentRunResult(
            agent_name=self.agent_name,
            status="completed" if route["status"] == "accepted" else "blocked",
            output={
                "order_request": proposal,
                "risk_governor": risk_decision.__dict__,
                "router_response": route,
                "slippage": task_input.get("slippage", 0.0),
                "position_update": {"updated_at": datetime.now(timezone.utc).isoformat()},
                "execution_anomalies": [] if route["status"] == "accepted" else route.get("reasons", []),
            },
        )


__all__ = ["LiveExecutionAgent"]
