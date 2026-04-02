"""Deterministic allocation review over stored risk recommendations and Edge fit."""

from __future__ import annotations

from typing import Any, Dict, List, Optional

from apps.agents.core.agent_models import AgentResult, AgentTask
from apps.agents.tools.edge_tools import EdgeTools
from apps.agents.tools.risk_tools import RiskTools


class PortfolioAllocationAgent:
    """Summarize where capital should be increased, held, or reduced."""

    def __init__(self, risk_tools: RiskTools, edge_tools: EdgeTools) -> None:
        self.risk_tools = risk_tools
        self.edge_tools = edge_tools

    def run(self, task: AgentTask) -> AgentResult:
        """Build a compact allocation review memo."""
        snapshot_id = int(task.input_payload.get("snapshot_id") or 0)
        edge_snapshot_id = task.input_payload.get("edge_snapshot_id")
        risk_bundle = self.risk_tools.risk_get_snapshot_bundle(snapshot_id=snapshot_id)
        recommendations = list(risk_bundle.get("recommendations") or [])
        top_recommendations = recommendations[:3]
        edge_fit = self._load_edge_fit(edge_snapshot_id)
        top_action = top_recommendations[0] if top_recommendations else {}
        summary = (
            f"Allocation review for risk snapshot {snapshot_id}: "
            f"{len(top_recommendations)} ranked recommendation(s). "
            f"Top action={top_action.get('action_type') or 'n/a'} {top_action.get('symbol') or ''}. "
            f"Edge context={edge_fit.get('archetype') or 'unavailable'}."
        )
        return AgentResult(
            status="ok",
            summary=summary,
            evidence=[{"type": "risk_snapshot", "snapshot_id": snapshot_id}],
            recommendations=top_recommendations,
            required_actions=[],
            warnings=[],
            confidence=0.76,
            metadata={"workflow": "portfolio_allocation_review"},
        )

    def _load_edge_fit(self, edge_snapshot_id: Any) -> Dict[str, Any]:
        if edge_snapshot_id in (None, "", 0):
            return {}
        snapshot = self.edge_tools.edge_get_snapshot(snapshot_id=int(edge_snapshot_id)) or {}
        return dict((snapshot.get("strategy_fit") or [{}])[0] or {})
