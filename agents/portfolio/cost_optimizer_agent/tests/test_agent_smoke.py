from agents.portfolio.cost_optimizer_agent.agent import build_agent

def test_build_agent_smoke():
    assert build_agent()["name"] == "cost_optimizer_agent"
