from agents.simulation.backtest_analyst_agent.agent import build_agent
from agents.simulation.backtest_analyst_agent.tools import TOOLS


def test_agent_smoke():
    agent = build_agent()
    assert agent.name == "backtest_analyst_agent"
    assert "execute_trade" not in TOOLS

