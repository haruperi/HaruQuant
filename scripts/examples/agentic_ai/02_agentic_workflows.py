"""Agentic workflows grounded in HaruQuant's actual operating model.

Usage:
    python scripts/examples/agentic_ai/02_agentic_workflows.py
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

CONTRACTS_ROOT = Path(PROJECT_ROOT) / "contracts"
WORKFLOWS_ROOT = Path(PROJECT_ROOT) / "config" / "workflows"


def print_example_header(title: str) -> None:
    print()
    print("=" * 78)
    print(title)
    print("=" * 78)


def print_section(label: str, value: Any) -> None:
    if isinstance(value, (dict, list)):
        value = json.dumps(value, indent=2, default=str)
    print(f"  {label:<35s} {value}")


def load_workflow(name: str) -> dict[str, Any]:
    path = WORKFLOWS_ROOT / f"{name}.yaml"
    with path.open("r", encoding="utf-8") as handle:
        return yaml.safe_load(handle)


def load_contract_example(contract_name: str, sample_name: str) -> dict[str, Any]:
    path = CONTRACTS_ROOT / contract_name / "examples" / "valid" / f"{sample_name}.json"
    with path.open("r", encoding="utf-8") as handle:
        return json.load(handle)


def workflow_step_names(definition: dict[str, Any]) -> list[str]:
    return [step["name"] for step in definition.get("steps", [])]


def workflow_agents(definition: dict[str, Any]) -> list[str]:
    return [step["agent"] for step in definition.get("steps", [])]


def example_01_workflow_modeling() -> None:
    """Show the real proposal workflow and the contracts it expects."""
    print_example_header("01: Workflow Modeling from proposal.yaml")

    definition = load_workflow("proposal")
    print_section("Workflow name", definition["name"])
    print_section("Pattern", definition["pattern"])
    print_section("Description", definition["description"].strip())

    for index, step in enumerate(definition["steps"], start=1):
        depends_on = step.get("depends_on", [])
        print_section(
            f"Step {index}",
            {
                "name": step["name"],
                "agent": step["agent"],
                "expected_output": step["expected_output"],
                "depends_on": depends_on or ["none"],
            },
        )


def example_02_prompt_chaining() -> None:
    """Map a real HaruQuant research chain from momentum_trading.yaml."""
    print_example_header("02: Prompt Chaining with momentum_trading.yaml")

    definition = load_workflow("momentum_trading")
    print_section("Workflow", definition["name"])
    print_section("Ordered steps", workflow_step_names(definition))

    chain_preview = []
    for step in definition["steps"]:
        chain_preview.append(
            {
                "step": step["name"],
                "agent": step["agent"],
                "input_stage": step["input"]["stage"],
                "depends_on": step.get("depends_on", []),
            }
        )
    print_section("Chained context flow", chain_preview)


def example_03_routing_workflow() -> None:
    """Show realistic routing keys from the proposal lifecycle."""
    print_example_header("03: Routing Decisions from Proposal States")

    trade_proposal = load_contract_example("trade_proposal", "eurusd_ready_for_risk")
    risk_decision = load_contract_example("risk_assessment_decision", "approve_with_limits")
    execution_receipt = load_contract_example("execution_receipt", "filled_limit_order")

    routing_cases = [
        {
            "route_key": trade_proposal["payload"]["readiness_state"],
            "current_agent": "strategy_agent",
            "next_agent": "risk_governor_agent",
            "reason": "proposal is ready_for_risk",
        },
        {
            "route_key": risk_decision["payload"]["decision"],
            "current_agent": "risk_governor_agent",
            "next_agent": "compliance_agent",
            "reason": "risk governor returned APPROVE_WITH_LIMITS",
        },
        {
            "route_key": execution_receipt["payload"]["status"],
            "current_agent": "execution_agent",
            "next_agent": "monitoring_agent",
            "reason": "broker acknowledged a filled order",
        },
    ]
    print_section("Routing cases", routing_cases)


def example_04_parallelization() -> None:
    """Show HaruQuant's real fan-out around evidence and scenario gathering."""
    print_example_header("04: Parallelization for Evidence Assembly")

    definition = load_workflow("proposal")
    attach_evidence = next(step for step in definition["steps"] if step["name"] == "attach_evidence")
    evidence_types = attach_evidence["input"]["evidence_types"]

    fan_out = [
        {"task_name": f"collect_{name}", "owner": "research_agent", "result_contract": "ObservationEvent"}
        for name in evidence_types
    ]
    print_section("Fan-out tasks", fan_out)
    print_section(
        "Fan-in target",
        "All evidence items feed the later risk_review and approval_decision stages.",
    )


def example_05_evaluator_optimizer() -> None:
    """Demonstrate revision pressure using real contract artifacts."""
    print_example_header("05: Evaluator-Optimizer with Real Contracts")

    trade_hypothesis = load_contract_example("trade_hypothesis", "eurusd_buy")
    evaluation_report = load_contract_example("evaluation_report", "workflow_pass")

    iteration_log = [
        {
            "iteration": 1,
            "candidate_contract": trade_hypothesis["contract_type"],
            "candidate_confidence": trade_hypothesis["payload"]["confidence"],
            "evaluator_verdict": evaluation_report["payload"]["verdict"],
            "improvement_actions": evaluation_report["payload"]["improvement_actions"],
        },
        {
            "iteration": 2,
            "candidate_contract": trade_hypothesis["contract_type"],
            "candidate_confidence": 0.70,
            "evaluator_verdict": "pass",
            "improvement_actions": ["macro-risk note added to calibration note"],
        },
    ]
    print_section("Refinement loop", iteration_log)


def example_06_orchestrator_workers() -> None:
    """Show the real worker delegation from the proposal workflow."""
    print_example_header("06: Orchestrator-Workers from proposal.yaml")

    definition = load_workflow("proposal")
    delegated_plan = []
    for step in definition["steps"]:
        delegated_plan.append(
            {
                "step": step["name"],
                "worker_agent": step["agent"],
                "contract": step["expected_output"],
                "validate": step.get("validate", False),
            }
        )
    print_section("Delegation plan", delegated_plan)


def example_07_platform_foundation() -> None:
    """Tie the workflow patterns back to the concrete HaruQuant platform pieces."""
    print_example_header("07: Platform Foundation Anchors")

    proposal = load_workflow("proposal")
    momentum = load_workflow("momentum_trading")
    print_section("Workflow definitions", ["proposal.yaml", "momentum_trading.yaml"])
    print_section("Proposal agents", workflow_agents(proposal))
    print_section("Momentum agents", workflow_agents(momentum))
    print_section(
        "Deterministic boundary",
        "risk_governor_agent is a deterministic adapter and should not be modeled as free-form LLM reasoning.",
    )


def example_08_complete_trade_lifecycle() -> None:
    """Walk the real trade lifecycle using sample contract outputs."""
    print_example_header("08: Complete HaruQuant Trade Lifecycle")

    lifecycle = [
        load_contract_example("trade_hypothesis", "eurusd_buy"),
        load_contract_example("observation_event", "market_snapshot_notice"),
        load_contract_example("trade_proposal", "eurusd_ready_for_risk"),
        load_contract_example("risk_assessment_decision", "approve_with_limits"),
        load_contract_example("execution_receipt", "filled_limit_order"),
        load_contract_example("replay_bundle", "complete_bundle"),
    ]

    summary = [
        {
            "contract_type": item["contract_type"],
            "originator": item["originator"]["id"],
            "workflow_id": item["workflow_id"],
        }
        for item in lifecycle
    ]
    print_section("Lifecycle summary", summary)


def main() -> None:
    print()
    print("#" * 78)
    print("#  HaruQuant Workflow Examples")
    print("#  Real workflows, contracts, and routing states")
    print("#" * 78)

    examples = [
        example_01_workflow_modeling,
        example_02_prompt_chaining,
        example_03_routing_workflow,
        example_04_parallelization,
        example_05_evaluator_optimizer,
        example_06_orchestrator_workers,
        example_07_platform_foundation,
        example_08_complete_trade_lifecycle,
    ]

    for example in examples:
        try:
            example()
        except Exception as exc:
            print(f"\n  ERROR in {example.__name__}: {exc}")

    print()
    print("#" * 78)
    print("#  All workflow examples complete")
    print("#" * 78)
    print()


if __name__ == "__main__":
    main()

