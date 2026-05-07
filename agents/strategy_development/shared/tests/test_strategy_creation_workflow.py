from __future__ import annotations

from agents._shared.base_contracts import AgentContext, AgentRequest
from agents.executive.planner_agent.service import PlannerAgent
from agents.strategy_development.shared.capabilities import AGENT_CAPABILITIES
from agents.strategy_development.shared.constants import (
    STANDARD_ACTIVATOR_COLUMNS,
    STANDARD_SIGNAL_COLUMNS,
)
from agents.strategy_development.shared.contracts import StrategySpec
from agents.strategy_development.shared.workflow import run_strategy_creation_workflow_sync


def test_capability_registry_covers_all_department_agents():
    assert len(AGENT_CAPABILITIES) == 13
    for capabilities in AGENT_CAPABILITIES.values():
        assert capabilities.inputs
        assert capabilities.responsibilities
        assert capabilities.deterministic_rules
        assert capabilities.output_artifacts
        assert "execute_trades" in capabilities.forbidden_actions


def test_strategy_spec_contract_has_template_requirements():
    spec = StrategySpec(
        spec_id="spec-test",
        strategy_name="EURUSD_H1_mean_reversion",
        strategy_family="mean_reversion",
        strategy_type="simple",
        created_at="2026-05-07T00:00:00+00:00",
        created_by_agent="test",
    )

    assert set(STANDARD_SIGNAL_COLUMNS).issubset(set(spec.signal_columns))
    assert set(STANDARD_ACTIVATOR_COLUMNS).issubset(set(spec.activator_columns))
    assert spec.cost_assumptions
    assert spec.execution_assumptions
    assert spec.risk_controls
    assert spec.test_plan


def test_strategy_creation_workflow_runs_to_handoff():
    package = run_strategy_creation_workflow_sync(
        AgentRequest(
            request_id="strategy-workflow-test",
            agent_name="strategy_creation_orchestrator_agent",
            task="create a EURUSD H1 mean-reversion strategy",
            payload={
                "user_prompt": "create a EURUSD H1 mean-reversion strategy",
                "symbol": "EURUSD",
                "timeframe": "H1",
                "evidence_refs": ["ev-1"],
            },
        ),
        AgentContext(session_id="ctx-strategy-workflow-test"),
    )

    assert len(package.agent_responses) == 12
    assert package.final_strategy_creation_package["strategy_spec"]
    assert package.validation_backtesting_handoff["spec_id"]
    assert package.audit["ceo_gateway_surface_ready"]


def test_planner_registers_strategy_creation_department():
    plan = PlannerAgent().create_plan(
        user_request="create a EURUSD H1 mean-reversion strategy"
    )

    assert plan.intent == "strategy_creation"
    assert "strategy_creation_orchestrator_agent" in plan.allowed_agents
    assert "strategy_codegen_agent" in plan.allowed_agents
    assert "StrategyValidationHandoffPackage" in plan.expected_outputs
