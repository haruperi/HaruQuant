from agents.executive.ceo_agent.internal.planner_agent.service import InternalPlannerAgent


def test_short_request_needs_clarification():
    output = InternalPlannerAgent().create_internal_plan(user_request="?", request_id="r3")
    assert output.intent == "clarification"
    assert output.missing_inputs
