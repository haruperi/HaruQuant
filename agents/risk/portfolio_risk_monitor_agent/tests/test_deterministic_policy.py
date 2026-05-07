from agents._shared import AgentRunContext
from agents.risk.portfolio_risk_monitor_agent.service import PortfolioRiskMonitorAgent


def test_policy_blocks_llm_override():
    result = PortfolioRiskMonitorAgent().run(context=AgentRunContext(workflow_id="wf", task_id="t1", user_request="risk"), task_input={"proposal": {"proposal_id": "p1", "strategy_id": "s1", "strategy_code_hash": "hash", "symbol": "EURUSD", "side": "buy", "requested_volume": 0.01, "expected_risk": {"amount": 50}}})
    artifact = result.output["portfolio_risk_report"]
    assert artifact["risk_memo"]["llm_override_blocked"] is True
    assert "execute_trade" in result.output["blocked_actions"]
