from agents.simulation.optimization_comparator_agent.agent import build_agent
from agents.simulation.optimization_comparator_agent.tools import TOOLS


def test_agent_smoke():
    agent = build_agent()
    assert agent.name == "optimization_comparator_agent"
    assert "execute_trade" not in TOOLS

