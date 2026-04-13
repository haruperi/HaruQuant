from __future__ import annotations

from backend.agents.runtime.workflow_definition import WorkflowRegistry


def test_ai_trading_project_workflows_parse() -> None:
    registry = WorkflowRegistry("backend/workflows")

    expected_steps = {
        "classification_optimization": 6,
        "data_transformation": 5,
        "dynamic_strategy": 5,
        "momentum_trading": 6,
        "rl_trading": 5,
    }

    for workflow_name, step_count in expected_steps.items():
        definition = registry.load(workflow_name)

        assert definition.name == workflow_name
        assert definition.pattern.value == "sequential"
        assert len(definition.steps) == step_count
        assert all(step.name for step in definition.steps)
        assert all(step.agent for step in definition.steps)
        assert all(step.expected_output for step in definition.steps)
