from agents.executive.ceo_agent.service import CEOAgent
from agents.executive.planner_agent.service import PlannerAgent


def test_specialist_failure_blocks_final_decision():
    plan = PlannerAgent().create_plan(user_request="research EURUSD", request_id="r6")
    response = CEOAgent().create_executive_response(
        request_id="r6",
        request="research EURUSD",
        planner_result=plan,
        agent_outputs={"research": {"status": "failed"}},
        evidence_refs=plan.evidence_requirements,
    )

    assert response.status == "blocked"
    assert "specialist_failure_or_block" in response.decision.reasons
