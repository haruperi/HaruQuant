from agents.risk.risk_orchestrator_agent.agent import build_agent


def test_agent_smoke():
    agent = build_agent()
    assert agent.name == "risk_orchestrator"
