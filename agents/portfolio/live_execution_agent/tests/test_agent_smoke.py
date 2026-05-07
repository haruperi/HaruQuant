from agents.portfolio.live_execution_agent.agent import build_agent


def test_build_agent():
    assert build_agent()["name"] == "live_execution_agent"
