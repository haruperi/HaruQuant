"""Minimal workflow planner for the Phase 0 foundation scaffold."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Dict, List

from apps.agents.core.agent_models import AgentTask


@dataclass(frozen=True)
class WorkflowPlan:
    """Planner output consumed by the workflow runner."""

    workflow_name: str
    specialist_names: List[str] = field(default_factory=list)
    metadata: Dict[str, str] = field(default_factory=dict)


class AgentPlanner:
    """Route tasks to a minimal workflow selection for Phase 0."""

    def plan(self, task: AgentTask) -> WorkflowPlan:
        """Return a deterministic plan for the current task."""
        if task.task_type == "noop" or task.intent == "foundation_check":
            return WorkflowPlan(
                workflow_name="noop_workflow",
                specialist_names=[],
                metadata={"reason": "phase_0_foundation_alignment"},
            )
        return WorkflowPlan(
            workflow_name="unmapped_task",
            specialist_names=[],
            metadata={"reason": "no_planner_rule"},
        )
