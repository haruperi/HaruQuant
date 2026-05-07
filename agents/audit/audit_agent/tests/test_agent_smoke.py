from agents.audit.audit_agent.agent import build_agent

def test_build_agent():
    assert build_agent()["name"] == "audit_agent"
