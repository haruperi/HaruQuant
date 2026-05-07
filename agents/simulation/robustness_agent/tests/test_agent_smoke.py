from agents.simulation.robustness_agent.agent import build_agent
from agents.simulation.robustness_agent.tools import TOOLS


def test_agent_smoke():
    agent = build_agent()
    assert agent.name == "robustness_agent"
    assert "execute_trade" not in TOOLS

