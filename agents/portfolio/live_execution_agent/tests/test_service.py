from agents._shared import AgentRunContext
from agents.portfolio.live_execution_agent import LiveExecutionAgent


def test_service_blocks_without_gates():
    result = LiveExecutionAgent().run(context=AgentRunContext(workflow_id="wf", task_id="task", user_request="live"), task_input={})
    assert result.status == "blocked"
