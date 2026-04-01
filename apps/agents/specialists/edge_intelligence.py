"""Deterministic snapshot-drift and fit-change analysis for Edge artifacts."""

from __future__ import annotations

from typing import Any, Dict, List

from apps.agents.core.agent_models import AgentResult, AgentTask
from apps.agents.tools.edge_tools import EdgeTools


class EdgeIntelligenceAgent:
    """Interpret changes between saved Edge snapshots."""

    def __init__(self, edge_tools: EdgeTools) -> None:
        self.edge_tools = edge_tools

    def run(self, task: AgentTask) -> AgentResult:
        """Build a compact drift and strategy-fit change summary."""
        left_id, right_id = self._resolve_snapshot_ids(task)
        comparison = self.edge_tools.edge_compare_snapshots(
            left_snapshot_id=left_id,
            right_snapshot_id=right_id,
        )
        if not comparison:
            return AgentResult(
                status="incomplete_evidence",
                summary="Snapshot comparison could not be built.",
                warnings=["snapshot_comparison_unavailable"],
                confidence=0.0,
            )

        left = dict(comparison.get("left_snapshot") or {})
        right = dict(comparison.get("right_snapshot") or {})
        left_fit = dict(left.get("primary_strategy_fit") or {})
        right_fit = dict(right.get("primary_strategy_fit") or {})
        fit_change = self._describe_fit_change(left_fit, right_fit)
        summary = (
            f"Snapshot drift from {left.get('snapshot_id')} to {right.get('snapshot_id')}: "
            f"{len(comparison.get('score_diffs') or [])} score changes, "
            f"{len(comparison.get('metric_diffs') or [])} metric changes. {fit_change}"
        )
        recommendations: List[Dict[str, Any]] = []
        if right_fit:
            recommendations.append(
                {
                    "type": "current_primary_fit",
                    "archetype": right_fit.get("archetype"),
                    "fit_score": right_fit.get("fit_score"),
                }
            )
        return AgentResult(
            status="ok",
            summary=summary,
            evidence=[
                {
                    "type": "edge_snapshot_comparison",
                    "left_snapshot_id": left.get("snapshot_id"),
                    "right_snapshot_id": right.get("snapshot_id"),
                }
            ],
            recommendations=recommendations,
            required_actions=[],
            warnings=[],
            confidence=0.78,
            metadata={"workflow": "snapshot_drift_watch"},
        )

    def _resolve_snapshot_ids(self, task: AgentTask) -> tuple[int, int]:
        left = task.input_payload.get("left_snapshot_id")
        right = task.input_payload.get("right_snapshot_id")
        if left and right:
            return int(left), int(right)
        symbol = str(task.input_payload.get("symbol") or "")
        timeframe = str(task.input_payload.get("timeframe") or "")
        snapshots = self.edge_tools.edge_list_snapshots(symbol=symbol, timeframe=timeframe, limit=2)
        if len(snapshots) < 2:
            raise ValueError("At least two snapshots are required for drift watch.")
        return int(snapshots[1]["snapshot_id"]), int(snapshots[0]["snapshot_id"])

    def _describe_fit_change(self, left_fit: Dict[str, Any], right_fit: Dict[str, Any]) -> str:
        if not left_fit and not right_fit:
            return "No primary strategy-fit rows are available."
        if left_fit.get("archetype") != right_fit.get("archetype"):
            return (
                f"Primary fit changed from {left_fit.get('archetype') or 'n/a'} "
                f"to {right_fit.get('archetype') or 'n/a'}."
            )
        left_score = left_fit.get("fit_score")
        right_score = right_fit.get("fit_score")
        if left_score is None or right_score is None:
            return "Primary fit is unchanged but score delta is unavailable."
        delta = float(right_score) - float(left_score)
        if delta > 0:
            return f"Primary fit strengthened by {delta:.2f}."
        if delta < 0:
            return f"Primary fit weakened by {abs(delta):.2f}."
        return "Primary fit is unchanged."
