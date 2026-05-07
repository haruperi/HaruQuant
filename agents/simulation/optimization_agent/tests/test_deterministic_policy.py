from agents._shared.base_contracts import AgentContext, AgentRequest, AgentStatus
from agents.simulation.optimization_agent.service import OptimizationAgentService


def test_normal_policy_success(event_loop):
    service = OptimizationAgentService()
    request = AgentRequest(request_id="r1", agent_name=service.agent_name, task="simulate", payload={})
    response = event_loop.run_until_complete(service.run(request, AgentContext(session_id="test")))
    assert response.decision.status in {AgentStatus.SUCCESS, AgentStatus.NEEDS_MORE_CONTEXT}
    assert "execute_trade" in response.decision.blocked_actions


def test_rejects_missing_data_or_unreviewed_strategy(event_loop):
    service = OptimizationAgentService()
    request = AgentRequest(request_id="r2", agent_name=service.agent_name, task="simulate", payload={"strategy_review_status": "failed", "historical_data": []})
    response = event_loop.run_until_complete(service.run(request, AgentContext(session_id="test")))
    assert response.decision.status == AgentStatus.REJECTED
    assert "strategy_not_approved_by_reviewer" in response.decision.reasons
