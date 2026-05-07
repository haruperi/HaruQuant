from agents.executive.ceo_agent.evaluator import evaluate_ceo_response
from agents.executive.ceo_agent.service import CEOAgent
from agents.executive.planner_agent.service import PlannerAgent


def test_ceo_evaluator_checks_governance_envelope():
    plan = PlannerAgent().create_plan(user_request="who are you?", request_id="r7")
    response = CEOAgent().create_executive_response(request_id="r7", request="who are you?", planner_result=plan)
    result = evaluate_ceo_response(response)

    assert result["passed"]
