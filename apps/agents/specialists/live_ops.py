"""Deterministic live-operations summary over existing live session status."""

from __future__ import annotations

from typing import Any, Dict

from apps.agents.core.agent_models import AgentResult, AgentTask
from apps.agents.tools.live_tools import LiveTools


class LiveOpsAgent:
    """Summarize current live session operating state for desk reporting."""

    def __init__(self, live_tools: LiveTools) -> None:
        self.live_tools = live_tools

    def run(self, task: AgentTask) -> AgentResult:
        """Build a compact live-operations memo from one session status snapshot."""
        session_id = int(task.input_payload.get("session_id") or 0)
        status = self.live_tools.live_get_session_status(session_id=session_id)
        quality = self.live_tools.live_get_execution_quality(session_id=session_id)
        state = self._classify(status, quality)
        summary = (
            f"Live ops summary for session {session_id}: {state}. "
            f"status={status.get('status')}, running={status.get('running')}, "
            f"signals_detected={status.get('signals_detected')}, active_positions={status.get('active_positions')}."
        )
        warnings = []
        if status.get("error_message"):
            warnings.append(str(status.get("error_message")))
        return AgentResult(
            status="ok",
            summary=summary,
            evidence=[{"type": "live_session_status", "session_id": session_id}],
            recommendations=[
                {
                    "type": "live_ops_state",
                    "state": state,
                    "approval_rate": quality.get("approval_rate"),
                    "rejection_rate": quality.get("rejection_rate"),
                }
            ],
            required_actions=[],
            warnings=warnings,
            confidence=0.74,
            metadata={"workflow": "live_ops_summary", "state": state},
        )

    def _classify(self, status: Dict[str, Any], quality: Dict[str, Any]) -> str:
        if status.get("error_message"):
            return "error"
        status_name = str(status.get("status") or "").lower()
        if status_name == "paused":
            return "paused"
        if float(quality.get("rejection_rate", 0.0) or 0.0) >= 0.5:
            return "caution"
        if bool(status.get("running")) or status_name == "running":
            return "running"
        return "idle"
