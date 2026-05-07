from agents.portfolio.portfolio_orchestrator_agent.deterministic_policy import make_policy_decision

def test_missing_evidence_blocks():
    decision = make_policy_decision({}, {"missing_evidence": ["risk"]})
    assert decision["status"] == "blocked"

def test_llm_cannot_override_kill_switch():
    decision = make_policy_decision({"kill_switch_state": "triggered", "llm_says": "approve"}, {"missing_evidence": []})
    assert decision["status"] == "blocked"
