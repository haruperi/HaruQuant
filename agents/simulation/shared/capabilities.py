"""Capability manifest for Simulation Department agents."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class SimulationAgentCapability:
    agent_name: str
    purpose: str
    allowed_actions: tuple[str, ...]
    tool_names: tuple[str, ...]


AGENT_CAPABILITIES = {
    "simulation_orchestrator_agent": SimulationAgentCapability("simulation_orchestrator_agent", "Coordinate simulation workflow.", ("create_simulation_plan", "route_to_risk_review", "route_to_strategy_revision"), ("validate_strategy_simulation_readiness", "create_simulation_plan")),
    "backtest_agent": SimulationAgentCapability("backtest_agent", "Run reproducible historical simulations.", ("validate_backtest_config", "run_backtest", "save_backtest_artifacts"), ("validate_data_availability", "run_haruquant_engine", "call_analytics_stack")),
    "backtest_analyst_agent": SimulationAgentCapability("backtest_analyst_agent", "Diagnose strategy behavior.", ("generate_diagnosis_report", "classify_edge_quality"), ("analyze_equity_curve", "analyze_failure_modes")),
    "optimization_agent": SimulationAgentCapability("optimization_agent", "Run bounded parameter sweeps.", ("run_parameter_sweep", "run_walk_forward_optimization"), ("validate_search_space", "run_candidate_backtests")),
    "optimization_comparator_agent": SimulationAgentCapability("optimization_comparator_agent", "Compare candidates by robust regions.", ("compare_candidate_runs", "reject_isolated_best_result"), ("cluster_parameter_sets", "compare_is_oos")),
    "robustness_agent": SimulationAgentCapability("robustness_agent", "Stress-test strategies.", ("run_spread_stress", "run_monte_carlo", "score_robustness"), ("run_cost_stress", "run_randomized_history")),
    "statistical_validation_agent": SimulationAgentCapability("statistical_validation_agent", "Validate statistical credibility.", ("validate_statistical_edge", "rate_evidence_quality"), ("run_bootstrap_tests", "run_randomization_tests")),
    "simulation_evidence_curator_agent": SimulationAgentCapability("simulation_evidence_curator_agent", "Preserve simulation evidence.", ("save_simulation_evidence", "index_result_package", "link_strategy_run"), ("index_simulation_artifacts", "mark_run_finalized")),
}

AGENT_CAPABILITIES["simulation_orchestrator"] = AGENT_CAPABILITIES["simulation_orchestrator_agent"]
AGENT_CAPABILITIES["statistical_validation"] = AGENT_CAPABILITIES["statistical_validation_agent"]
