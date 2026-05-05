"""Incident summarization and escalation agent."""

from __future__ import annotations

from typing import Any

from agents.base import AgentRunContext, AgentRunResult


class IncidentAgent:
    agent_name = "incident_agent"

    def summarize(self, incident: dict[str, Any]) -> dict[str, Any]:
        severity = incident.get("severity", "major")
        return {
            "incident_id": incident.get("incident_id", "incident-unknown"),
            "summary": incident.get("summary", "Risk control incident detected."),
            "trigger": incident.get("trigger", "unknown"),
            "affected_strategies": incident.get("affected_strategies", []),
            "open_positions": incident.get("open_positions", []),
            "required_action": incident.get("required_action", "pause_new_orders"),
            "recommendation": "resume_only_after_human_approval" if severity == "critical" else "review_before_resume",
            "requires_human_approval_to_resume": severity == "critical",
        }

    def run(self, *, context: AgentRunContext, task_input: dict[str, Any]) -> AgentRunResult:
        return AgentRunResult(agent_name=self.agent_name, status="completed", output=self.summarize(task_input))


__all__ = ["IncidentAgent"]
