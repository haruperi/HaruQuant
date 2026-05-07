from agents.risk.risk_approval_auditor_agent.agent import build_agent


def test_agent_smoke():
    agent = build_agent()
    assert agent.name == "risk_approval_auditor"
