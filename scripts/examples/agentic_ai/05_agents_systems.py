"""Real agent example: Strategy Creator system.

Usage:
    python scripts/examples/agentic_ai/05_agents_systems.py
"""

from __future__ import annotations

import json
import os
import sys
from pathlib import Path
from typing import Any

import yaml

PROJECT_ROOT = os.path.abspath(
    os.path.join(os.path.dirname(__file__), "..", "..", "..", "..")
)
sys.path.insert(0, PROJECT_ROOT)

if sys.platform == "win32":
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")

from agents.strategy_development.strategy_creator_agent.service import StrategyCreatorAgent
from agents.runtime import (
    ADKRunRequest,
    ADKRunResult,
    ADKRunnerConfig,
    ADKRunnerService,
    AgentExecutionContext,
    AgentExecutionResult,
)
from data.database import GovernanceRepository, apply_pending_migrations, default_migrations_dir
from data.database.sqlite.database_operations import DatabaseManager
from haruquant.strategy import StrategyCatalogService, StrategyStorage
from haruquant.strategy import StrategyBlueprintMaterializationRequest, StrategyBlueprintMaterializationService, StrategyBlueprintRenderer, StrategyBlueprintValidator


DEFAULT_USER_IDEA = "Buy when RSI is low and exit when it recovers."


def print_example_header(title: str) -> None:
    print()
    print("=" * 78)
    print(title)
    print("=" * 78)


def print_kv(label: str, value: Any) -> None:
    if isinstance(value, (dict, list, tuple)):
        value = json.dumps(value, indent=2, default=str)
    print(f"  {label:<35s} {value}")


class MockStrategyCreatorRuntime:
    """Deterministic runtime used by the examples."""

    def run(
        self,
        *,
        request: ADKRunRequest,
        context: AgentExecutionContext,
    ) -> AgentExecutionResult:
        idea = str(request.input_payload.get("idea", "")).lower()
        if "hrp" in idea or "risk parity" in idea or "portfolio" in idea:
            payload = {
                "strategy_name": "Large Cap HRP Allocation",
                "strategy_type": "portfolio",
                "entry_logic": [
                    "Rebalance into the current HRP weight vector at the scheduled rebalance date."
                ],
                "exit_logic": [
                    "Exit and recompute weights on the next rebalance date.",
                    "Exit positions if the portfolio-level drawdown rule triggers."
                ],
                "portfolio_construction": {
                    "method": "HRP",
                    "rebalance_frequency": "Weekly",
                    "objective": "Risk-balanced diversified allocation"
                },
                "risk_management": {
                    "ignore_stop_loss_take_profit": False,
                    "additional_rules": ["Cap portfolio drawdown at 12 percent."]
                }
            }
        elif "decision tree" in idea or "predict" in idea or "classifier" in idea:
            payload = {
                "strategy_name": "Decision Tree Direction Forecast",
                "strategy_type": "ml",
                "entry_logic": [
                    "Enter LONG when the model predicts the next-day return class is positive."
                ],
                "exit_logic": [
                    "Exit LONG when the model prediction flips negative."
                ],
                "risk_management": {
                    "ignore_stop_loss_take_profit": False,
                    "additional_rules": ["Retrain model monthly on a rolling window."]
                }
            }
        else:
            payload = {
                "strategy_name": "RSI Mean Reversion",
                "strategy_type": "technical",
                "entry_logic": [
                    "Enter LONG when RSI is low enough to indicate an oversold condition."
                ],
                "exit_logic": [
                    "Exit LONG when RSI normalizes back into the mid-range."
                ],
                "risk_management": {
                    "ignore_stop_loss_take_profit": False,
                    "additional_rules": ["Do not open a second position while one is active."]
                }
            }

        output = {
            "schema_version": "1.0.0",
            "contract_type": "StrategyBlueprint",
            "workflow_id": request.workflow_id,
            "correlation_id": request.correlation_id,
            "causation_id": f"evt-{request.correlation_id}",
            "timestamp_utc": "2026-04-19T12:00:00Z",
            "originator": {"type": "agent", "id": "strategy_creator_agent"},
            "environment": "paper",
            "operating_mode": "MODE-001",
            "payload": {
                "source_idea": str(request.input_payload.get("idea", "")),
                **payload,
            },
        }
        return AgentExecutionResult(
            output_payload=output,
            final_state="COMPLETED",
            token_usage={"prompt_tokens": 120, "completion_tokens": 180, "total_tokens": 300},
        )


def _runner() -> ADKRunnerService:
    return ADKRunnerService(
        config=ADKRunnerConfig(
            runner_name="strategy_creator_examples",
            default_model="mock-strategy-creator",
        )
    )


def _agent() -> StrategyCreatorAgent:
    return StrategyCreatorAgent(
        validator=StrategyBlueprintValidator(),
        materializer=_materializer(),
    )


def _workflow_definition() -> dict[str, Any]:
    path = Path(PROJECT_ROOT) / "config" / "workflows" / "hypothesis_design.yaml"
    return yaml.safe_load(path.read_text(encoding="utf-8"))


def prompt_user_idea() -> str:
    print_example_header("00: User Prompt")
    print("  Enter a rough trading idea for the Strategy Creator agent.")
    print(f"  Press Enter to use default: {DEFAULT_USER_IDEA}")
    try:
        idea = input("\nUser idea> ").strip()
    except EOFError:
        idea = ""
    final_idea = idea or DEFAULT_USER_IDEA
    print_kv("User idea", final_idea)
    return final_idea


def _materializer() -> StrategyBlueprintMaterializationService:
    temp_root = Path(PROJECT_ROOT) / ".tmp_agentic_examples" / "strategy_creator"
    temp_root.mkdir(parents=True, exist_ok=True)
    db_path = temp_root / "materialization.db"
    storage_root = temp_root / "strategies"

    db = DatabaseManager(db_path=str(db_path))
    db.initialize_database()
    apply_pending_migrations(db_path, default_migrations_dir())
    if not db.get_user(user_id=1):
        db.create_user(
            email="agentic.examples@haruquant.local",
            username="agentic_examples",
            password="password",
            full_name="Agentic Examples",
        )

    catalog = StrategyCatalogService(
        db_manager=db,
        strategy_storage=StrategyStorage(base_dir=str(storage_root)),
        governance_repository=GovernanceRepository(db.db_path),
    )
    return StrategyBlueprintMaterializationService(catalog_service=catalog)


def example_01_rulebook_defaults(user_idea: str) -> None:
    print_example_header("01: Rulebook Defaults")
    validator = StrategyBlueprintValidator()
    candidate = {
        "payload": {
            "source_idea": user_idea
        }
    }
    result = validator.validate(candidate)
    print_kv("Strategy type", result.blueprint.payload.strategy_type)
    print_kv("Assets", result.blueprint.payload.asset_scope.assets)
    print_kv("Timeframe", result.blueprint.payload.asset_scope.timeframe)
    print_kv("Defaults used", result.blueprint.payload.assumption_defaults_used)


def example_02_strategy_creator_agent(user_idea: str) -> None:
    print_example_header("02: Strategy Creator Agent")
    result = _agent().create_from_idea(user_id=1, idea=user_idea, full_permissions=False)
    print_kv("Contract type", result.blueprint.contract_type)
    print_kv("Strategy name", result.blueprint.payload.strategy_name)
    print_kv("Readiness", result.blueprint.payload.backtest_readiness)


def example_03_portfolio_blueprint() -> None:
    print_example_header("03: Portfolio Strategy Blueprint")
    result = _agent().create_from_idea(
        user_id=1,
        idea="Build an HRP portfolio over large-cap tech and rebalance weekly.",
        full_permissions=False,
    )
    payload = result.blueprint.payload
    print_kv("Strategy type", payload.strategy_type)
    print_kv("Portfolio method", payload.portfolio_construction.method if payload.portfolio_construction else None)
    print_kv("Assets count", len(payload.asset_scope.assets))


def example_04_ml_blueprint() -> None:
    print_example_header("04: ML Strategy Blueprint")
    result = _agent().create_from_idea(
        user_id=1,
        idea="Use a decision tree classifier to predict next-day direction.",
        full_permissions=False,
    )
    payload = result.blueprint.payload
    print_kv("Strategy type", payload.strategy_type)
    print_kv("Model spec", payload.model_spec)


def example_05_render_strategy_code(user_idea: str) -> None:
    print_example_header("05: Render Strategy Code")
    renderer = StrategyBlueprintRenderer()
    blueprint = _agent().create_from_idea(user_id=1, idea=user_idea, full_permissions=False).blueprint
    rendered = renderer.render_python_strategy(blueprint)
    print_kv("Render summary", renderer.render_summary(blueprint))
    print("  Code preview:")
    for line in rendered.splitlines()[:28]:
        print(f"    {line}")


def example_06_catalog_governance_integration(user_idea: str) -> None:
    print_example_header("06: Catalog and Governance Integration")
    result = _agent().create_from_idea(user_id=1, idea=user_idea, full_permissions=True)
    print_kv("Strategy id", result.strategy["id"] if result.strategy else None)
    print_kv("Governance strategy id", result.strategy["governance_strategy_id"] if result.strategy else None)
    print_kv("Lifecycle state", result.strategy["lifecycle_state"] if result.strategy else None)
    print_kv("Blueprint artifact", result.blueprint_artifact_path)


def example_07_workflow_design() -> None:
    print_example_header("07: Workflow and Orchestration")
    definition = _workflow_definition()
    print_kv("Workflow name", definition["name"])
    print_kv(
        "Steps",
        [
            {
                "name": step["name"],
                "agent": step["agent"],
                "expected_output": step["expected_output"],
            }
            for step in definition["steps"]
        ],
    )


def main() -> None:
    print()
    print("#" * 78)
    print("#  Strategy Creator Agent System")
    print("#" * 78)

    user_idea = prompt_user_idea()

    examples = [
        lambda: example_01_rulebook_defaults(user_idea),
        lambda: example_02_strategy_creator_agent(user_idea),
        example_03_portfolio_blueprint,
        example_04_ml_blueprint,
        lambda: example_05_render_strategy_code(user_idea),
        lambda: example_06_catalog_governance_integration(user_idea),
        example_07_workflow_design,
    ]

    for example in examples:
        try:
            example()
        except Exception as exc:
            print(f"\n  ERROR in {example.__name__}: {exc}")

    print()
    print("#" * 78)
    print("#  Strategy Creator examples complete")
    print("#" * 78)
    print()


if __name__ == "__main__":
    main()

