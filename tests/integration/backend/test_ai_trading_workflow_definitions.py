from __future__ import annotations

from backend.agents.runtime.workflow_definition import WorkflowRegistry


def test_ai_trading_project_workflows_parse() -> None:
    registry = WorkflowRegistry()

    expected_steps = {
        "classification_optimization": 6,
        "data_transformation": 11,
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


def test_data_transformation_workflow_matches_ai_trading_sequence() -> None:
    registry = WorkflowRegistry()
    definition = registry.load("data_transformation")

    assert [step.name for step in definition.steps] == [
        "collect_market_data",
        "clean_and_prepare_data",
        "create_features",
        "define_strategy_or_model",
        "generate_signals",
        "run_unsupervised_research",
        "backtest_strategy",
        "evaluate_performance",
        "refine_and_repeat",
        "run_refinement_experiments",
        "agent_evaluate_and_conclude",
    ]
    assert [step.input["workflow_step"] for step in definition.steps] == list(range(1, 12))
