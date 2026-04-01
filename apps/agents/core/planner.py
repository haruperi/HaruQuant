"""Intent-based workflow planner for the initial agent workflows."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Dict, List

from apps.agents.core.agent_models import AgentTask
from apps.agents.core.policies import PermissionTier


@dataclass(frozen=True)
class WorkflowPlan:
    """Planner output consumed by the workflow runner."""

    workflow_name: str
    specialist_names: List[str] = field(default_factory=list)
    required_inputs: List[str] = field(default_factory=list)
    permission_tier: str = PermissionTier.READ_ONLY
    metadata: Dict[str, str] = field(default_factory=dict)


class AgentPlanner:
    """Route tasks to supported workflow templates."""

    def plan(self, task: AgentTask) -> WorkflowPlan:
        """Return a deterministic plan for the current task."""
        if task.task_type == "noop" or task.intent == "foundation_check":
            return WorkflowPlan(
                workflow_name="noop_workflow",
                specialist_names=[],
                required_inputs=[],
                metadata={"reason": "phase_0_foundation_alignment"},
            )
        if task.task_type == "daily_market_brief" or task.intent == "daily_market_brief":
            return WorkflowPlan(
                workflow_name="daily_market_brief",
                specialist_names=["research_orchestrator"],
                required_inputs=["symbol", "timeframe"],
                metadata={"reason": "edge_snapshot_brief"},
            )
        if task.task_type == "live_risk_watch" or task.intent == "live_risk_watch":
            return WorkflowPlan(
                workflow_name="live_risk_watch",
                specialist_names=["risk_supervisor"],
                required_inputs=["snapshot_id"],
                metadata={"reason": "risk_snapshot_watch"},
            )
        if task.task_type == "incident_review" or task.intent == "incident_review":
            return WorkflowPlan(
                workflow_name="incident_review",
                specialist_names=["incident_investigator"],
                required_inputs=["run_id"],
                metadata={"reason": "replay_backed_incident_review"},
            )
        return WorkflowPlan(
            workflow_name="unmapped_task",
            specialist_names=[],
            required_inputs=[],
            metadata={"reason": "no_planner_rule"},
        )
