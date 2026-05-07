"""Paper Execution Agent."""

from __future__ import annotations

from typing import Any

from agents._shared import AgentRunContext, AgentRunResult
from execution.paper_broker import PaperBroker
from services.risk.governor import RiskGovernor


class PaperExecutionAgent:
    agent_name = "paper_execution"

    def __init__(self, *, broker: PaperBroker | None = None, governor: RiskGovernor | None = None) -> None:
        self.broker = broker or PaperBroker()
        self.governor = governor or RiskGovernor()

    def promotion_criteria(self, *, paper_stats: dict[str, Any]) -> dict[str, Any]:
        failures: list[str] = []
        if paper_stats.get("trading_days", 0) < 30:
            failures.append("minimum_30_trading_days")
        if paper_stats.get("trade_count", 0) < 30:
            failures.append("minimum_trade_count")
        if paper_stats.get("max_drawdown", 1.0) > 0.08:
            failures.append("max_drawdown")
        if paper_stats.get("slippage_ok", True) is not True:
            failures.append("slippage_within_expected_range")
        if paper_stats.get("spread_live_like", True) is not True:
            failures.append("live_like_spread_assumptions")
        if paper_stats.get("execution_anomalies", 0) > 0:
            failures.append("execution_anomalies")
        if paper_stats.get("risk_governor_violations", 0) > 0:
            failures.append("risk_governor_violations")
        if paper_stats.get("within_confidence_interval", True) is not True:
            failures.append("performance_confidence_interval")
        return {"eligible": not failures, "failures": failures}

    def run(self, *, context: AgentRunContext, task_input: dict[str, Any]) -> AgentRunResult:
        if not task_input.get("approved_paper_strategy", False):
            return AgentRunResult(agent_name=self.agent_name, status="blocked", output={"reason": "paper_strategy_not_approved"})
        proposal = task_input.get("trade_proposal", {})
        decision = self.governor.evaluate_trade(proposal=proposal, portfolio_snapshot=self.broker.account_snapshot(), market_snapshot=task_input.get("market_snapshot", {}))
        if decision.decision != "approved":
            return AgentRunResult(agent_name=self.agent_name, status="blocked", output={"risk_governor": decision.__dict__})
        receipt = self.broker.place_order(
            symbol=proposal.get("symbol", "UNKNOWN"),
            side=proposal.get("side", "buy"),
            order_type=proposal.get("entry_type", "market"),
            size=float(proposal.get("requested_size", 0.01)),
            price=float(proposal.get("price", 1.0)),
            spread=float(task_input.get("market_snapshot", {}).get("spread", 0.0)),
            slippage=float(task_input.get("market_snapshot", {}).get("slippage", 0.0)),
            commission=float(task_input.get("commission", 0.0)),
            swap=float(task_input.get("swap", 0.0)),
        )
        return AgentRunResult(agent_name=self.agent_name, status="completed", output={"risk_governor": decision.__dict__, "paper_execution": receipt})


__all__ = ["PaperExecutionAgent"]

