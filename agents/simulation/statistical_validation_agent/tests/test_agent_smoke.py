from agents.simulation.statistical_validation_agent.agent import build_agent
from agents.simulation.statistical_validation_agent.tools import TOOLS


def test_agent_smoke():
    agent = build_agent()
    assert agent.name == "statistical_validation_agent"
    assert "execute_trade" not in TOOLS

