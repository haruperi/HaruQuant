from agents._shared import AgentRunContext
from agents.portfolio.execution_readiness_agent.service import ExecutionReadinessAgent

def test_service_returns_audited_result():
    task_input = {key: "ok" for key in ['broker_health', 'audit_health_status', 'risk_governor_status']}
    result = ExecutionReadinessAgent().run(context=AgentRunContext(workflow_id="wf", task_id="task", user_request="test"), task_input=task_input)
    assert result.agent_name
    assert result.output["audit_ref"]
