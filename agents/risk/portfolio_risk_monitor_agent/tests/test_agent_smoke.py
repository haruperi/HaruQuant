from agents.risk.portfolio_risk_monitor_agent.agent import build_agent


def test_agent_smoke():
    agent = build_agent()
    assert agent.name == "portfolio_risk_monitor"
