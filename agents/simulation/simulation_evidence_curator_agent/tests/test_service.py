from agents._shared.base_contracts import AgentContext, AgentRequest
from agents.simulation.simulation_evidence_curator_agent.service import SimulationEvidenceCuratorAgentService


def test_service_returns_agent_response(event_loop):
    service = SimulationEvidenceCuratorAgentService()
    request = AgentRequest(request_id="r1", agent_name=service.agent_name, task="simulate", payload={})
    response = event_loop.run_until_complete(service.run(request, AgentContext(session_id="test")))
    assert response.audit
    assert response.evidence
    assert response.decision
    assert response.artifacts
    assert response.audit["strategy_code_hash"]
    assert response.decision.allowed_actions
    assert response.decision.blocked_actions
