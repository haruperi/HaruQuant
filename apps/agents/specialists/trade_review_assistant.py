"""Deterministic trade review assistant over simulator preview and what-if context."""

from __future__ import annotations

from typing import Any, Dict, List

from apps.agents.core.agent_models import AgentResult, AgentTask
from apps.agents.tools.edge_tools import EdgeTools
from apps.agents.tools.simulator_tools import SimulatorTools


class TradeReviewAssistantAgent:
    """Support manual trade review with preview and optional what-if evidence."""

    def __init__(self, simulator_tools: SimulatorTools, edge_tools: EdgeTools | None = None) -> None:
        self.simulator_tools = simulator_tools
        self.edge_tools = edge_tools

    def run(self, task: AgentTask) -> AgentResult:
        """Build an advisory accept/caution/avoid memo for one candidate simulator trade."""
        session_id = int(task.input_payload.get("session_id") or 0)
        trade_request = dict(task.input_payload.get("trade_request") or {})
        preview = self.simulator_tools.sim_preview_trade(
            session_id=session_id,
            trade_request=trade_request,
        )
        what_if_payload = self._maybe_run_what_if(task, session_id=session_id)
        state = self._classify(preview, what_if_payload)
        edge_note = self._edge_note(task)
        governance = dict(preview.get("governance") or {})
        summary = (
            f"Trade review for session {session_id}: {state}. "
            f"Governance={governance.get('decision') or governance.get('status') or 'n/a'}, "
            f"checks={len(preview.get('rows') or [])}. {edge_note}"
        )
        recommendations: List[Dict[str, Any]] = []
        if what_if_payload:
            recommendations.append(
                {
                    "type": "what_if_projection",
                    "projected_compliance_state": (what_if_payload.get("summary") or {}).get("projected_compliance_state"),
                    "projected_governance_decision": (what_if_payload.get("summary") or {}).get("projected_governance_decision"),
                }
            )
        return AgentResult(
            status="ok",
            summary=summary,
            evidence=[
                {"type": "sim_trade_preview", "session_id": session_id},
                *(
                    [{"type": "sim_what_if", "session_id": session_id}]
                    if what_if_payload
                    else []
                ),
            ],
            recommendations=recommendations,
            required_actions=[],
            warnings=self._warnings(preview),
            confidence=0.77,
            metadata={"workflow": "trade_review_assistant", "state": state},
        )

    def _maybe_run_what_if(self, task: AgentTask, *, session_id: int) -> Dict[str, Any]:
        actions = list(task.input_payload.get("what_if_actions") or [])
        if not actions:
            return {}
        return self.simulator_tools.sim_run_what_if(
            session_id=session_id,
            actions=actions,
            leverage_override=task.input_payload.get("leverage_override"),
        )

    def _classify(self, preview: Dict[str, Any], what_if_payload: Dict[str, Any]) -> str:
        governance = dict(preview.get("governance") or {})
        decision = str(governance.get("decision") or governance.get("status") or "").lower()
        if decision in {"reject", "breach"}:
            return "avoid"
        if decision in {"warning", "caution"}:
            return "caution"
        if what_if_payload:
            projected = str((what_if_payload.get("summary") or {}).get("projected_governance_decision") or "").lower()
            if projected in {"reject", "breach", "warning", "caution"}:
                return "caution"
        rows = list(preview.get("rows") or [])
        if any(not bool(row.get("acceptable", True)) for row in rows):
            return "caution"
        return "accept"

    def _warnings(self, preview: Dict[str, Any]) -> List[str]:
        rows = list(preview.get("rows") or [])
        return [str(row.get("item") or row.get("key")) for row in rows if not bool(row.get("acceptable", True))]

    def _edge_note(self, task: AgentTask) -> str:
        if self.edge_tools is None:
            return ""
        snapshot_id = task.input_payload.get("edge_snapshot_id")
        if snapshot_id in (None, "", 0):
            return ""
        snapshot = self.edge_tools.edge_get_snapshot(snapshot_id=int(snapshot_id)) or {}
        fits = list(snapshot.get("strategy_fit") or [])
        best_fit = fits[0] if fits else {}
        if not best_fit:
            return ""
        return f"Edge context={best_fit.get('archetype') or 'n/a'}."
