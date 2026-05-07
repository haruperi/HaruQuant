from agents.simulation.optimization_agent.agent import build_agent
from agents.simulation.optimization_agent.tools import TOOLS


def test_agent_smoke():
    agent = build_agent()
    assert agent.name == "optimization_agent"
    assert "execute_trade" not in TOOLS

