from agents.executive.planner_agent.service import PlannerAgent


def test_clarification_route_has_missing_input():
    plan = PlannerAgent().create_plan(user_request="?")
    assert plan.needs_clarification
    assert "clarify_goal" in plan.missing_inputs
