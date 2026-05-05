"""Multi-agent coordination examples using HaruQuant's actual agent model.

Usage:
    python scripts/examples/agentic_ai/04_multi_agent_systems.py
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

CONTRACTS_ROOT = Path(PROJECT_ROOT) / "backend_retiring" / "contracts"
WORKFLOWS_ROOT = Path(PROJECT_ROOT) / "backend_retiring" / "orchestration" / "workflow" / "definitions"

from backend_retiring.agents.runtime.session_manager import SessionManager


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


def example_01_multi_agent_architecture() -> None:
    """Define the actual HaruQuant agent roster and responsibilities."""
    print_example_header("01: Multi-Agent Architecture")

    architecture = [
        {"agent": "research_agent", "responsibility": "collect evidence and observation events"},
        {"agent": "strategy_agent", "responsibility": "draft trade hypotheses and proposals"},
        {"agent": "portfolio_agent", "responsibility": "run scenarios, backtests, and overlays"},
        {"agent": "risk_governor_agent", "responsibility": "produce deterministic risk decisions"},
        {"agent": "compliance_agent", "responsibility": "approve, limit, or reject actions"},
        {"agent": "execution_agent", "responsibility": "translate approved intents into broker-safe actions"},
    ]
    print_section("Agent roster", architecture)


def example_02_orchestration() -> None:
    """Show the sequential orchestration already encoded in proposal.yaml."""
    print_example_header("02: Sequential Orchestration from proposal.yaml")

    definition = load_workflow("proposal")
    sequence = [
        {
            "step": step["name"],
            "agent": step["agent"],
            "output": step["expected_output"],
            "depends_on": step.get("depends_on", []),
        }
        for step in definition["steps"]
    ]
    print_section("Orchestrated steps", sequence)


def example_03_routing_data_flow() -> None:
    """Route between agents using real workflow and contract states."""
    print_example_header("03: Routing and Data Flow")

    proposal = load_contract_example("trade_proposal", "eurusd_ready_for_risk")
    risk_decision = load_contract_example("risk_assessment_decision", "approve_with_limits")

    routes = [
        {
            "state": proposal["payload"]["readiness_state"],
            "from": "strategy_agent",
            "to": "risk_governor_agent",
        },
        {
            "state": risk_decision["payload"]["decision"],
            "from": "risk_governor_agent",
            "to": "compliance_agent",
        },
        {
            "state": "approved_with_limits",
            "from": "compliance_agent",
            "to": "execution_agent",
        },
    ]
    print_section("Routing states", routes)


def example_04_state_management() -> None:
    """Store workflow-wide shared state for multiple agents."""
    print_example_header("04: Shared Session State")

    manager = SessionManager()
    session = manager.create_session(
        metadata={
            "workflow_name": "proposal",
            "workflow_id": "wf_01",
            "proposal_id": "prop_01",
            "current_stage": "risk_review",
            "shared_contract_refs": ["hyp_01", "prop_01", "risk_01"],
        }
    )
    session.metadata["assigned_agents"] = [
        "strategy_agent",
        "research_agent",
        "risk_governor_agent",
        "compliance_agent",
    ]
    print_section("Shared metadata", session.metadata)


def example_05_orchestration_state_coordination() -> None:
    """Coordinate parallel reviews before synthesis."""
    print_example_header("05: Parallel Reviews and Synthesis")

    committee_outputs = {
        "research_agent": "market snapshot confirms breakout-and-retest structure",
        "portfolio_agent": "existing EURUSD exposure remains below concentration threshold",
        "risk_governor_agent": "approve_with_limits because realized volatility percentile is elevated",
    }
    synthesis = {
        "proposal_id": "prop_01",
        "summary": "proposal may continue, but only under reduced size and deviation constraints",
        "contributors": list(committee_outputs.keys()),
    }
    print_section("Parallel outputs", committee_outputs)
    print_section("Synthesis", synthesis)


def example_06_multi_agent_rag() -> None:
    """Use local HaruQuant artifacts as collaborative retrieval context."""
    print_example_header("06: Multi-Agent RAG")

    proposal_workflow = load_workflow("proposal")
    momentum_workflow = load_workflow("momentum_trading")
    retrieved_context = {
        "research_agent": proposal_workflow["description"].strip(),
        "strategy_agent": momentum_workflow["description"].strip(),
        "compliance_agent": load_contract_example("risk_assessment_decision", "approve_with_limits")["payload"]["reasons"],
    }
    print_section("Retrieved context", retrieved_context)


def example_07_complete_trade_approval_system() -> None:
    """Mirror the real HaruQuant trade lifecycle using contract samples."""
    print_example_header("07: Complete HaruQuant Trade Approval System")

    lifecycle = [
        load_contract_example("trade_hypothesis", "eurusd_buy"),
        load_contract_example("observation_event", "market_snapshot_notice"),
        load_contract_example("trade_proposal", "eurusd_ready_for_risk"),
        load_contract_example("risk_assessment_decision", "approve_with_limits"),
        load_contract_example("execution_receipt", "filled_limit_order"),
    ]

    stages = []
    for item in lifecycle:
        stages.append(
            {
                "contract_type": item["contract_type"],
                "originator": item["originator"]["id"],
                "workflow_id": item["workflow_id"],
            }
        )
    print_section("Lifecycle stages", stages)
    print_section(
        "Decision boundary",
        "risk_governor_agent is deterministic; compliance_agent decides approval envelope; execution_agent acts only after approval.",
    )


def main() -> None:
    print()
    print("#" * 78)
    print("#  HaruQuant Multi-Agent Systems")
    print("#" * 78)

    examples = [
        example_01_multi_agent_architecture,
        example_02_orchestration,
        example_03_routing_data_flow,
        example_04_state_management,
        example_05_orchestration_state_coordination,
        example_06_multi_agent_rag,
        example_07_complete_trade_approval_system,
    ]

    for example in examples:
        try:
            example()
        except Exception as exc:
            print(f"\n  ERROR in {example.__name__}: {exc}")

    print()
    print("#" * 78)
    print("#  All multi-agent examples complete")
    print("#" * 78)
    print()


if __name__ == "__main__":
    main()
