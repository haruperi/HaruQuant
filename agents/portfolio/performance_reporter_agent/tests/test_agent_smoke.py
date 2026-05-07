from agents.portfolio.performance_reporter_agent.agent import build_agent

def test_build_agent_smoke():
    assert build_agent()["name"] == "performance_reporter_agent"
