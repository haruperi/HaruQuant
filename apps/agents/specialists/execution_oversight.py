"""Deterministic execution oversight over live session counters and status."""

from __future__ import annotations

from typing import Any, Dict

from apps.agents.core.agent_models import AgentResult, AgentTask
from apps.agents.tools.live_tools import LiveTools


class ExecutionOversightAgent:
    """Summarize live session execution health and caution signals."""

    def __init__(self, live_tools: LiveTools) -> None:
        self.live_tools = live_tools

    def run(self, task: AgentTask) -> AgentResult:
        """Build a compact execution-quality memo."""
        session_id = int(task.input_payload.get("session_id") or 0)
        quality = self.live_tools.live_get_execution_quality(session_id=session_id)
        caution = self._classify(quality)
        summary = (
            f"Execution quality for session {session_id}: {caution}. "
            f"approval_rate={quality.get('approval_rate'):.2f}, "
            f"rejection_rate={quality.get('rejection_rate'):.2f}, "
            f"active_positions={quality.get('active_positions')}."
        )
        warnings = []
        if quality.get("error_message"):
            warnings.append(str(quality.get("error_message")))
        return AgentResult(
            status="ok",
            summary=summary,
            evidence=[{"type": "live_session_quality", "session_id": session_id}],
            recommendations=[
                {"type": "execution_state", "state": caution},
            ],
            required_actions=[],
            warnings=warnings,
            confidence=0.72,
            metadata={"workflow": "execution_quality_watch", "state": caution},
        )

    def _classify(self, quality: Dict[str, Any]) -> str:
        if quality.get("error_message"):
            return "unsuitable_execution_environment"
        if float(quality.get("rejection_rate", 0.0) or 0.0) >= 0.5:
            return "caution"
        return "normal"
