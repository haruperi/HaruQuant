from agents.portfolio.strategy_lifecycle_agent.agent import build_agent

def test_build_agent_smoke():
    assert build_agent()["name"] == "strategy_lifecycle_agent"
