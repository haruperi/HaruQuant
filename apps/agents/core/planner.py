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
        if task.task_type == "strategy_promotion_review" or task.intent == "strategy_promotion_review":
            return WorkflowPlan(
                workflow_name="strategy_promotion_review",
                specialist_names=["strategy_qa"],
                required_inputs=["backtest_id", "optimization_id", "strategy_version_id"],
                metadata={"reason": "stored_validation_review"},
            )
        if task.task_type == "snapshot_drift_watch" or task.intent == "snapshot_drift_watch":
            return WorkflowPlan(
                workflow_name="snapshot_drift_watch",
                specialist_names=["edge_intelligence"],
                required_inputs=[],
                metadata={"reason": "edge_snapshot_drift_watch"},
            )
        if task.task_type == "execution_quality_watch" or task.intent == "execution_quality_watch":
            return WorkflowPlan(
                workflow_name="execution_quality_watch",
                specialist_names=["execution_oversight"],
                required_inputs=["session_id"],
                metadata={"reason": "live_execution_quality_watch"},
            )
        if task.task_type == "portfolio_allocation_review" or task.intent == "portfolio_allocation_review":
            return WorkflowPlan(
                workflow_name="portfolio_allocation_review",
                specialist_names=["portfolio_allocator"],
                required_inputs=["snapshot_id"],
                metadata={"reason": "risk_recommendation_allocation_review"},
            )
        return WorkflowPlan(
            workflow_name="unmapped_task",
            specialist_names=[],
            required_inputs=[],
            metadata={"reason": "no_planner_rule"},
        )
