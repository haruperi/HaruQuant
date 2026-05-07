from agents.audit.audit_agent.deterministic_policy import audit_policy

def test_missing_token_is_critical():
    assert audit_policy([{"live_order": True, "order_id": "o1"}])[0].severity == "critical"
