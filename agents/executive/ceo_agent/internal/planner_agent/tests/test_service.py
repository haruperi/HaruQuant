from agents.executive.ceo_agent.internal.planner_agent.service import InternalPlannerAgent


def test_internal_planner_wraps_existing_planner():
    output = InternalPlannerAgent().create_internal_plan(user_request="portfolio allocation review", request_id="r1")
    assert output.intent == "portfolio"
    assert "portfolio" in output.departments_to_call
