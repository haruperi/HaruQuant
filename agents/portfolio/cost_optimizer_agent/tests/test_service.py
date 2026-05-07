from agents._shared import AgentRunContext
from agents.portfolio.cost_optimizer_agent.service import CostOptimizerAgent

def test_service_returns_audited_result():
    task_input = {key: "ok" for key in ['cost_usage']}
    result = CostOptimizerAgent().run(context=AgentRunContext(workflow_id="wf", task_id="task", user_request="test"), task_input=task_input)
    assert result.agent_name
    assert result.output["audit_ref"]
