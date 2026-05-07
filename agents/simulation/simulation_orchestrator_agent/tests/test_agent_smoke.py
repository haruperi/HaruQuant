from agents.simulation.simulation_orchestrator_agent.agent import build_agent
from agents.simulation.simulation_orchestrator_agent.tools import TOOLS


def test_agent_smoke():
    agent = build_agent()
    assert agent.name == "simulation_orchestrator_agent"
    assert "execute_trade" not in TOOLS

