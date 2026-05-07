from agents._shared.base_contracts import AgentContext, AgentRequest
from agents.simulation.simulation_orchestrator_agent.service import SimulationOrchestratorAgentService
from agents.simulation.shared.contracts import SimulationRequestPayload


def test_valid_request_schema():
    payload = SimulationRequestPayload(strategy_id="s1", strategy_code_hash="hash", symbol="EURUSD", timeframe="H1", data_start="2023-01-01", data_end="2024-01-01", initial_balance=1000, commission_model={"value": 1}, spread_model={"value": 1}, slippage_model={"value": 1}, execution_mode="next_bar_open")
    assert payload.strategy_id == "s1"


def test_response_serializes(event_loop):
    service = SimulationOrchestratorAgentService()
    request = AgentRequest(request_id="r1", agent_name=service.agent_name, task="simulate", payload={})
    response = event_loop.run_until_complete(service.run(request, AgentContext(session_id="test")))
    assert response.model_dump(mode="json")["agent_name"] == service.agent_name
