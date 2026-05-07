from agents.risk.risk_limit_auditor_agent.agent import build_agent


def test_agent_smoke():
    agent = build_agent()
    assert agent.name == "risk_limit_auditor"
