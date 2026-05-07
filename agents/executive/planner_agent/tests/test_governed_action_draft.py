from agents.executive.planner_agent.service import PlannerAgent


def test_approval_routes_to_governed_action_draft():
    plan = PlannerAgent().create_plan(user_request="approve risk threshold change")
    assert plan.intent == "governed_action_draft"
    assert plan.requires_board_approval
