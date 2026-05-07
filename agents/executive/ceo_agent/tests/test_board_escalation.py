from agents.executive.ceo_agent.service import CEOAgent
from agents.executive.planner_agent.service import PlannerAgent


def test_board_escalation_packet_is_created_for_live_approval():
    plan = PlannerAgent().create_plan(user_request="approve live deployment", request_id="r4")
    response = CEOAgent().create_executive_response(request_id="r4", request="approve live deployment", planner_result=plan, evidence_refs=plan.evidence_requirements)

    assert response.decision.requires_board_approval
    assert response.board_escalation is not None
    assert response.board_escalation["decision_required"] == "Human Board approval"
