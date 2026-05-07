"""Strategy Creation Department capability registry."""

from __future__ import annotations

from dataclasses import dataclass


COMMON_FORBIDDEN = (
    "execute_trades",
    "send_orders_to_mt5_or_ctrader",
    "approve_risk",
    "override_risk_governor",
    "modify_live_portfolio",
    "deploy_strategy_to_production",
    "bypass_validation_or_risk_departments",
)


@dataclass(frozen=True)
class StrategyAgentCapabilities:
    inputs: tuple[str, ...]
    responsibilities: tuple[str, ...]
    deterministic_rules: tuple[str, ...]
    output_artifacts: tuple[str, ...]
    tests_required: tuple[str, ...] = ("test_contracts.py", "test_deterministic_policy.py", "test_service.py", "test_agent_smoke.py")
    forbidden_actions: tuple[str, ...] = COMMON_FORBIDDEN


AGENT_CAPABILITIES: dict[str, StrategyAgentCapabilities] = {
    "strategy_creation_orchestrator_agent": StrategyAgentCapabilities(("user_prompt", "research_handoff", "existing_memory"), ("determine_request_source", "route_department_agents", "resolve_conflicts", "produce_final_package"), ("missing_symbol_needs_context", "untestable_rules_block_codegen", "failed_review_blocks_handoff"), ("strategy_creation_package", "audit_metadata")),
    "strategy_creator_agent": StrategyAgentCapabilities(("user_prompt", "approved_research_hypothesis", "evidence_refs", "symbol", "timeframe", "strategy_family"), ("convert_prompt_to_spec", "convert_hypothesis_to_spec", "define_on_bar_get_signal_on_event_contracts"), ("schema_valid_spec_required", "symbol_timeframe_entry_exit_required", "no_future_or_broker_logic"), ("StrategySpec", "StrategyImplementationBrief", "parameter_catalog", "test_plan")),
    "strategy_spec_validator_agent": StrategyAgentCapabilities(("StrategySpec",), ("validate_spec_completeness", "reject_vague_or_future_rules"), ("missing_symbol_or_timeframe_rejects", "lookahead_rules_required"), ("strategy_spec_validation_report",)),
    "strategy_rule_normalizer_agent": StrategyAgentCapabilities(("StrategySpec",), ("normalize_rules", "make_rules_testable"), ("vague_rules_are_blocked",), ("strategy_rule_normalization_report",)),
    "strategy_template_selector_agent": StrategyAgentCapabilities(("StrategySpec",), ("select_template", "select_base_classes", "select_lifecycle_methods"), ("stateful_requires_on_event",), ("strategy_template_selection_report",)),
    "strategy_risk_assumption_agent": StrategyAgentCapabilities(("StrategySpec",), ("define_risk_assumptions", "define_position_sizing_assumptions"), ("missing_risk_assumptions_block_handoff",), ("strategy_risk_assumption_report",)),
    "strategy_cost_execution_agent": StrategyAgentCapabilities(("StrategySpec",), ("define_cost_assumptions", "define_execution_assumptions"), ("missing_cost_assumptions_block_handoff",), ("strategy_cost_execution_report",)),
    "strategy_test_plan_agent": StrategyAgentCapabilities(("StrategySpec",), ("create_tests", "create_robustness_plan", "define_no_lookahead_tests"), ("missing_required_tests_block_handoff",), ("strategy_test_plan",)),
    "strategy_codegen_agent": StrategyAgentCapabilities(("approved_StrategySpec", "template_selection_report"), ("generate_code", "generate_config_readme_tests"), ("approved_spec_required", "generated_pending_review_only", "broker_and_risk_calls_blocked"), ("StrategyCodePackage", "generated_file_manifest", "generated_tests", "README")),
    "strategy_reviewer_agent": StrategyAgentCapabilities(("StrategySpec", "StrategyCodePackage", "generated_tests", "README"), ("review_structure_safety_tests", "approve_or_reject_for_backtesting"), ("missing_files_or_tests_reject", "lookahead_or_broker_calls_reject", "approve_only_for_backtesting"), ("StrategyReviewReport", "fix_list", "backtesting_handoff_readiness")),
    "strategy_spec_storage_agent": StrategyAgentCapabilities(("StrategySpec",), ("save_spec", "version_spec", "link_lineage"), ("no_overwrite_without_version", "approved_states_require_validation"), ("strategy_spec_storage_receipt",)),
    "strategy_code_storage_agent": StrategyAgentCapabilities(("StrategyCodePackage",), ("save_code_package", "version_code", "track_checksums"), ("valid_spec_id_required", "blocked_imports_prevent_storage"), ("strategy_code_storage_receipt",)),
    "strategy_handoff_agent": StrategyAgentCapabilities(("approved_StrategySpec", "StrategyCodePackage", "StrategyReviewReport"), ("create_backtesting_handoff", "package_validation_payload"), ("approved_for_backtest_required", "reviewer_approval_required", "evidence_lineage_required"), ("StrategyHandoffPackage",)),
}
