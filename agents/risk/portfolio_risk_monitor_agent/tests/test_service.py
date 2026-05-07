from agents._shared import AgentRunContext
from agents.risk.portfolio_risk_monitor_agent.service import PortfolioRiskMonitorAgent


def test_service_returns_audit_and_artifact():
    result = PortfolioRiskMonitorAgent().run(context=AgentRunContext(workflow_id="wf", task_id="t1", user_request="risk"), task_input={"proposal": {"proposal_id": "p1", "strategy_id": "s1", "strategy_code_hash": "hash", "symbol": "EURUSD", "side": "buy", "requested_volume": 0.01, "expected_risk": {"amount": 50}}})
    assert result.status in {"completed", "blocked"}
    assert result.output["audit"]
    assert result.output["portfolio_risk_report"]
