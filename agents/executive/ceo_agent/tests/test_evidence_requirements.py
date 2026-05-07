from agents.executive.ceo_agent.deterministic_policy import make_executive_decision
from agents.executive.planner_agent.service import PlannerAgent


def test_missing_evidence_returns_needs_more_context():
    plan = PlannerAgent().create_plan(user_request="risk review this strategy", request_id="r3")
    decision = make_executive_decision(request="risk review this strategy", planner_result=plan, evidence_refs=[])

    assert decision.status == "needs_more_context"
    assert decision.missing_evidence
