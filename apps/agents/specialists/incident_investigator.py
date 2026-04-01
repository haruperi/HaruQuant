"""Deterministic incident reconstruction over stored replay frames."""

from __future__ import annotations

from apps.agents.core.agent_models import AgentResult, AgentTask
from apps.agents.tools.risk_tools import RiskTools


class IncidentInvestigatorAgent:
    """Build a simple replay-backed incident summary."""

    def __init__(self, risk_tools: RiskTools) -> None:
        self.risk_tools = risk_tools

    def run(self, task: AgentTask) -> AgentResult:
        """Reconstruct a compact incident timeline summary."""
        run_id = int(task.input_payload.get("run_id") or 0)
        report = self.risk_tools.replay_get_report(run_id=run_id)
        summary_data = dict(report.get("summary") or {})
        summary = (
            f"Incident review for run {run_id}: frames={report.get('frame_count')}, "
            f"last_governance_status={summary_data.get('last_governance_status')}, "
            f"last_regime={summary_data.get('last_regime_name')}."
        )
        return AgentResult(
            status="ok",
            summary=summary,
            evidence=[
                {
                    "type": "replay_run",
                    "run_id": run_id,
                    "frame_count": report.get("frame_count"),
                    "first_timestamp": report.get("first_timestamp"),
                    "last_timestamp": report.get("last_timestamp"),
                }
            ],
            recommendations=[
                {
                    "type": "incident_follow_up",
                    "what_if_available": summary_data.get("what_if_available"),
                }
            ],
            required_actions=[],
            warnings=[],
            confidence=0.7,
            metadata={"workflow": "incident_review"},
        )
