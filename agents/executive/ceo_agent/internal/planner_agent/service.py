"""CEO-owned internal planner wrapper around the existing PlannerAgent."""

from __future__ import annotations

from agents.executive.ceo_agent.shared.planner_contracts import PlannerOutput
from agents.executive.planner_agent.service import PlannerAgent


class InternalPlannerAgent:
    agent_name = "internal_planner"

    def __init__(self, *, planner: PlannerAgent | None = None) -> None:
        self.planner = planner or PlannerAgent()

    def create_internal_plan(self, *, user_request: str, request_id: str | None = None) -> PlannerOutput:
        plan = self.planner.create_plan(user_request=user_request, request_id=request_id)
        return PlannerOutput.from_agent_plan(plan)
