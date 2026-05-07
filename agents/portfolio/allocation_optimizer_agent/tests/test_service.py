from agents._shared import AgentRunContext
from agents.portfolio.allocation_optimizer_agent.service import AllocationOptimizerAgent

def test_service_returns_audited_result():
    task_input = {key: "ok" for key in ['current_allocations', 'risk_constraints']}
    result = AllocationOptimizerAgent().run(context=AgentRunContext(workflow_id="wf", task_id="task", user_request="test"), task_input=task_input)
    assert result.agent_name
    assert result.output["audit_ref"]
