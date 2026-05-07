from agents.portfolio.allocation_optimizer_agent.agent import build_agent

def test_build_agent_smoke():
    assert build_agent()["name"] == "allocation_optimizer_agent"
