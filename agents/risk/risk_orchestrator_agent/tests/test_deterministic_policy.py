from agents._shared import AgentRunContext
from agents.risk.risk_orchestrator_agent.service import RiskOrchestratorAgent


def test_policy_blocks_llm_override():
    result = RiskOrchestratorAgent().run(context=AgentRunContext(workflow_id="wf", task_id="t1", user_request="risk"), task_input={"proposal": {"proposal_id": "p1", "strategy_id": "s1", "strategy_code_hash": "hash", "symbol": "EURUSD", "side": "buy", "requested_volume": 0.01, "expected_risk": {"amount": 50}}})
    artifact = result.output["risk_department_response"]
    assert artifact["risk_memo"]["llm_override_blocked"] is True
    assert "execute_trade" in result.output["blocked_actions"]
