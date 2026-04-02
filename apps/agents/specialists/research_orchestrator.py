"""Deterministic research summary over saved Edge snapshots."""

from __future__ import annotations

from typing import Any, Dict

from apps.agents.core.agent_models import AgentResult, AgentTask
from apps.agents.tools.edge_tools import EdgeTools


class ResearchOrchestratorAgent:
    """Summarize saved Edge state into a market brief."""

    def __init__(self, edge_tools: EdgeTools) -> None:
        self.edge_tools = edge_tools

    def run(self, task: AgentTask) -> AgentResult:
        """Build a small desk-style brief from the latest saved snapshot."""
        symbol = str(task.input_payload.get("symbol") or "")
        timeframe = str(task.input_payload.get("timeframe") or "")
        snapshots = self.edge_tools.edge_list_snapshots(symbol=symbol, timeframe=timeframe, limit=2)
        if not snapshots:
            return AgentResult(
                status="incomplete_evidence",
                summary=f"No Edge snapshots found for {symbol} {timeframe}.",
                warnings=["no_edge_snapshots_found"],
                confidence=0.0,
            )

        current = self.edge_tools.edge_get_snapshot(snapshot_id=int(snapshots[0]["snapshot_id"])) or {}
        previous = None
        if len(snapshots) > 1:
            previous = self.edge_tools.edge_get_snapshot(snapshot_id=int(snapshots[1]["snapshot_id"]))

        scorecard = dict(current.get("scorecard_summary") or {})
        strategy_fit = list(current.get("strategy_fit") or [])
        best_fit = strategy_fit[0] if strategy_fit else {}
        score = scorecard.get("final_score")
        readiness = scorecard.get("readiness_label") or scorecard.get("final_label") or "unknown"
        drift_text = self._describe_drift(current, previous)
        summary = (
            f"Latest Edge snapshot for {symbol} {timeframe}: score={score}, "
            f"readiness={readiness}, top_fit={best_fit.get('archetype') or 'n/a'}. {drift_text}"
        )
        recommendations = []
        if best_fit:
            recommendations.append(
                {
                    "type": "strategy_fit",
                    "archetype": best_fit.get("archetype"),
                    "fit_score": best_fit.get("fit_score"),
                    "rationale": best_fit.get("rationale"),
                }
            )
        return AgentResult(
            status="ok",
            summary=summary,
            evidence=[
                {
                    "type": "edge_snapshot",
                    "snapshot_id": current.get("snapshot_id"),
                    "symbol": current.get("symbol"),
                    "timeframe": current.get("timeframe"),
                }
            ],
            recommendations=recommendations,
            required_actions=[],
            warnings=[],
            confidence=0.75,
            metadata={"workflow": "daily_market_brief"},
        )

    def _describe_drift(
        self,
        current: Dict[str, Any],
        previous: Dict[str, Any] | None,
    ) -> str:
        if not previous:
            return "No prior snapshot available for drift comparison."
        current_score = (current.get("scorecard_summary") or {}).get("final_score")
        previous_score = (previous.get("scorecard_summary") or {}).get("final_score")
        if current_score is None or previous_score is None:
            return "Prior snapshot exists but score drift could not be computed."
        delta = float(current_score) - float(previous_score)
        if delta > 0:
            return f"Score improved by {delta:.2f} versus snapshot {previous.get('snapshot_id')}."
        if delta < 0:
            return f"Score deteriorated by {abs(delta):.2f} versus snapshot {previous.get('snapshot_id')}."
        return f"Score is unchanged versus snapshot {previous.get('snapshot_id')}."
