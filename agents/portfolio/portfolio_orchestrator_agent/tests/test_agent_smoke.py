from agents.portfolio.portfolio_orchestrator_agent.agent import build_agent

def test_build_agent_smoke():
    assert build_agent()["name"] == "portfolio_orchestrator_agent"
