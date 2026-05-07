from agents.executive.ceo_agent.shared.planner_contracts import PlannerOutput


def test_planner_output_contract_serializes():
    output = PlannerOutput(request_id="r1", intent="research", workflow_type="research", task_summary="Research EURUSD")
    assert output.plan_id
    assert output.model_dump() if hasattr(output, "model_dump") else output.dict()
