from agents.portfolio.execution_readiness_agent.agent import build_agent

def test_build_agent_smoke():
    assert build_agent()["name"] == "execution_readiness_agent"
