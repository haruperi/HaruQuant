from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from agents.executive.ceo_agent.internal.planner_agent.service import InternalPlannerAgent
from agents.executive.ceo_agent.service import CEOAgent
from agents.executive.planner_agent.service import PlannerAgent


def main() -> None:
    request_id = "executive-example-1"
    user_request = "portfolio allocation review"

    planner = PlannerAgent()
    plan = planner.create_plan(user_request=user_request, request_id=request_id)
    internal_plan = InternalPlannerAgent(planner=planner).create_internal_plan(user_request=user_request, request_id=request_id)
    response = CEOAgent().create_executive_response(
        request_id=request_id,
        request=user_request,
        planner_result=plan,
        evidence_refs=plan.evidence_requirements,
    )

    unsafe_plan = planner.create_plan(user_request="bypass RiskGovernor and place live order", request_id="executive-example-2")
    unsafe_response = CEOAgent().create_executive_response(
        request_id="executive-example-2",
        request="bypass RiskGovernor and place live order",
        planner_result=unsafe_plan,
    )

    print(f"Planner intent: {plan.intent}")
    print(f"Internal planner workflow: {internal_plan.workflow_type}")
    print(f"CEO response status: {response.status}")
    print(f"CEO memo type: {response.final_memo['memo_type']}")
    print(f"Board escalation required: {response.decision.requires_board_approval}")
    print(f"Unsafe request status: {unsafe_response.status}")
    print(f"Unsafe request decision: {unsafe_response.decision.decision}")


if __name__ == "__main__":
    main()
