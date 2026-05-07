from agents.executive.ceo_agent.internal.planner_agent.service import InternalPlannerAgent


def test_approval_request_routes_to_governed_draft():
    output = InternalPlannerAgent().create_internal_plan(user_request="approve live deployment", request_id="r4")
    assert output.intent == "governed_action_draft"
