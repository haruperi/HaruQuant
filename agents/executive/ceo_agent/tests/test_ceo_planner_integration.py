from agents.executive.ceo_agent.internal.planner_agent.service import InternalPlannerAgent
from agents.executive.ceo_agent.service import CEOAgent
from agents.executive.planner_agent.service import PlannerAgent


def test_ceo_uses_existing_planner_shape_for_executive_response():
    plan = PlannerAgent().create_plan(user_request="portfolio allocation review", request_id="r1")
    response = CEOAgent().create_executive_response(request_id="r1", request="portfolio allocation review", planner_result=plan, evidence_refs=plan.evidence_requirements)

    assert response.planner_output["intent"] == "portfolio"
    assert response.audit["planner_called"] is True


def test_internal_planner_is_ceo_owned_wrapper():
    output = InternalPlannerAgent().create_internal_plan(user_request="research EURUSD", request_id="r2")
    assert output.intent == "research"
    assert "internal_planner" in output.audit_tags
