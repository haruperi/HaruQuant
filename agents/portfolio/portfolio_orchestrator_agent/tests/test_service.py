from agents._shared import AgentRunContext
from agents.portfolio.portfolio_orchestrator_agent.service import PortfolioOrchestratorAgent

def test_service_returns_audited_result():
    task_input = {key: "ok" for key in ['risk_governor_constraints', 'audit_health_status']}
    result = PortfolioOrchestratorAgent().run(context=AgentRunContext(workflow_id="wf", task_id="task", user_request="test"), task_input=task_input)
    assert result.agent_name
    assert result.output["audit_ref"]
