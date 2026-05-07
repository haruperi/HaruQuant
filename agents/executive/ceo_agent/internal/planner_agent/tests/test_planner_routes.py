from agents.executive.ceo_agent.internal.planner_agent.service import InternalPlannerAgent


def test_execution_route_is_governed():
    output = InternalPlannerAgent().create_internal_plan(user_request="place a live order", request_id="r2")
    assert output.intent == "execution_proposal"
    assert output.requires_risk_governor
    assert output.requires_board_approval
