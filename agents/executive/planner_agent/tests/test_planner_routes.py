from agents.executive.planner_agent.service import PlannerAgent


def test_portfolio_review_route():
    plan = PlannerAgent().create_plan(user_request="portfolio allocation review")
    assert plan.intent == "portfolio"


def test_execution_proposal_route_is_guarded():
    plan = PlannerAgent().create_plan(user_request="place a live order")
    assert plan.intent == "execution_proposal"
    assert "live_execution" in plan.blocked_agents
