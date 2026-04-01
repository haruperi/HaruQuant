"""Deterministic risk memo builder over stored risk snapshots."""

from __future__ import annotations

from typing import Any, Dict

from apps.agents.core.agent_models import AgentResult, AgentTask
from apps.agents.tools.risk_tools import RiskTools


class RiskSupervisorAgent:
    """Summarize one stored risk snapshot into a desk-style memo."""

    def __init__(self, risk_tools: RiskTools) -> None:
        self.risk_tools = risk_tools

    def run(self, task: AgentTask) -> AgentResult:
        """Build a compact current-state risk memo."""
        snapshot_id = int(task.input_payload.get("snapshot_id") or 0)
        report = self.risk_tools.risk_get_snapshot_report(snapshot_id=snapshot_id)
        governance = dict(report.get("governance_summary") or {})
        portfolio = dict(report.get("portfolio_summary") or {})
        scenarios = list(report.get("scenarios") or [])
        recommendations = list(report.get("recommendations") or [])
        state = self._classify_state(governance)
        worst = scenarios[0] if scenarios else {}
        summary = (
            f"Risk state for snapshot {snapshot_id}: {state}. "
            f"Governance={governance.get('status')}, VaR={portfolio.get('portfolio_var')}, "
            f"worst_scenario_loss={worst.get('loss')}."
        )
        return AgentResult(
            status="ok",
            summary=summary,
            evidence=[
                {
                    "type": "risk_snapshot",
                    "snapshot_id": snapshot_id,
                    "run_id": report.get("snapshot_header", {}).get("run_id"),
                }
            ],
            recommendations=recommendations[:3],
            required_actions=[],
            warnings=[],
            confidence=0.8,
            metadata={"workflow": "live_risk_watch", "state": state},
        )

    def _classify_state(self, governance: Dict[str, Any]) -> str:
        status = str(governance.get("status") or "").lower()
        if status == "breach":
            return "escalate"
        if status == "warning":
            return "caution"
        if status == "compliant":
            return "safe"
        return "unknown"
