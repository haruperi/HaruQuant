from agents.executive.ceo_agent.internal.planner_agent.deterministic_policy import validate_planner_output
from agents.executive.ceo_agent.shared.planner_contracts import PlannerOutput


def test_forbidden_tool_is_rejected():
    output = PlannerOutput(request_id="r1", intent="research", workflow_type="research", task_summary="x", backend_tools_to_run=["place_order"])
    assert validate_planner_output(output)["valid"] is False
