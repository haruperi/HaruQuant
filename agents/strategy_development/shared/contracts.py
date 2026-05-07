"""Shared Strategy Creation Department contracts."""

from __future__ import annotations

from enum import Enum
from typing import Any

from pydantic import BaseModel, Field

from .constants import DEFAULT_SYMBOL, DEFAULT_TIMEFRAME, REQUIRED_STRATEGY_FILES, STANDARD_ACTIVATOR_COLUMNS, STANDARD_SIGNAL_COLUMNS


class StrategyType(str, Enum):
    SIMPLE = "simple"
    STATEFUL = "stateful"
    HYBRID = "hybrid"


class StrategyLifecycleState(str, Enum):
    SPEC = "spec"
    APPROVED_FOR_CODEGEN = "approved_for_codegen"
    GENERATED_PENDING_REVIEW = "generated_pending_review"
    REVIEW_FAILED = "review_failed"
    APPROVED_FOR_BACKTEST = "approved_for_backtest"


class StrategyCreationPayload(BaseModel):
    user_prompt: str | None = None
    approved_research_hypothesis: dict[str, Any] = Field(default_factory=dict)
    research_report_id: str | None = None
    evidence_refs: list[str] = Field(default_factory=list)
    symbol: str | None = None
    timeframe: str | None = None
    strategy_family: str = "mean_reversion"
    market_regime: str = "unknown"
    technical_context: dict[str, Any] = Field(default_factory=dict)
    macro_news_context: dict[str, Any] = Field(default_factory=dict)
    user_constraints: dict[str, Any] = Field(default_factory=dict)
    existing_strategy_memory: list[dict[str, Any]] = Field(default_factory=list)
    rejected_strategy_memory: list[dict[str, Any]] = Field(default_factory=list)
    research_validation_status: str = "approved_with_caution"
    strategy_type: StrategyType = StrategyType.SIMPLE


class StrategySpec(BaseModel):
    spec_id: str
    strategy_name: str
    strategy_family: str
    strategy_type: StrategyType
    lifecycle_state: StrategyLifecycleState = StrategyLifecycleState.SPEC
    symbol: str = DEFAULT_SYMBOL
    asset_class: str = "forex"
    timeframe: str = DEFAULT_TIMEFRAME
    execution_timeframe: str = DEFAULT_TIMEFRAME
    signal_timeframe: str = DEFAULT_TIMEFRAME
    filter_timeframe: str | None = None
    higher_timeframe: str | None = None
    lower_timeframe: str | None = None
    market_regime: str = "unknown"
    research_question: str | None = None
    hypothesis_id: str | None = None
    research_report_ids: list[str] = Field(default_factory=list)
    evidence_refs: list[str] = Field(default_factory=list)
    entry_rules: list[str] = Field(default_factory=lambda: ["Use closed-bar indicators only."])
    exit_rules: list[str] = Field(default_factory=lambda: ["Exit by target, stop, or invalidation."])
    pending_order_rules: list[str] = Field(default_factory=list)
    cancel_order_rules: list[str] = Field(default_factory=list)
    position_sizing_rules: list[str] = Field(default_factory=lambda: ["Risk fraction is capped and later approved by Risk Governor."])
    position_management_rules: list[str] = Field(default_factory=list)
    risk_controls: list[str] = Field(default_factory=lambda: ["No internal risk approval; Risk Governor decides later."])
    cost_assumptions: list[str] = Field(default_factory=lambda: ["Include spread, slippage, commission, and swap."])
    execution_assumptions: list[str] = Field(default_factory=lambda: ["No broker calls inside strategy files."])
    data_requirements: list[str] = Field(default_factory=lambda: ["ohlcv", "spread"])
    indicator_requirements: list[str] = Field(default_factory=list)
    state_requirements: list[str] = Field(default_factory=list)
    signal_columns: list[str] = Field(default_factory=lambda: list(STANDARD_SIGNAL_COLUMNS))
    activator_columns: list[str] = Field(default_factory=lambda: list(STANDARD_ACTIVATOR_COLUMNS))
    trade_action_types: list[str] = Field(default_factory=lambda: ["open", "close", "modify", "cancel"])
    parameter_schema: dict[str, str] = Field(default_factory=dict)
    parameter_defaults: dict[str, Any] = Field(default_factory=dict)
    parameter_validation_rules: list[str] = Field(default_factory=list)
    lookahead_handling: list[str] = Field(default_factory=lambda: ["Signals for bar N open use bar N-1 or earlier."])
    invalidation_rules: list[str] = Field(default_factory=list)
    test_plan: list[str] = Field(default_factory=lambda: ["test_params.py", "test_on_bar.py", "test_no_lookahead.py"])
    robustness_plan: list[str] = Field(default_factory=lambda: ["cost_sensitivity", "walk_forward", "monte_carlo"])
    expected_failure_modes: list[str] = Field(default_factory=list)
    generated_files_expected: list[str] = Field(default_factory=lambda: list(REQUIRED_STRATEGY_FILES))
    created_at: str
    created_by_agent: str
    version: str = "0.1.0"


class StrategyImplementationBrief(BaseModel):
    brief_id: str
    spec_id: str
    template_type: str
    base_classes: list[str]
    required_imports: list[str]
    strategy_file_path: str
    config_file_path: str
    readme_file_path: str
    test_file_paths: list[str]
    methods_to_implement: list[str]
    signal_columns_to_generate: list[str]
    activator_columns_to_generate: list[str]
    state_fields: list[str] = Field(default_factory=list)
    trade_action_metadata_fields: list[str]
    risk_control_fields: list[str]
    lookahead_rules: list[str]


class StrategyCodePackage(BaseModel):
    code_package_id: str
    spec_id: str
    strategy_version: str
    files: dict[str, str] = Field(default_factory=dict)
    file_manifest: list[str] = Field(default_factory=list)
    generated_tests: list[str] = Field(default_factory=list)
    readme: str = ""
    codegen_warnings: list[str] = Field(default_factory=list)
    blocked_imports_detected: list[str] = Field(default_factory=list)
    direct_execution_calls_detected: list[str] = Field(default_factory=list)
    risk_approval_calls_detected: list[str] = Field(default_factory=list)
    status: str = "generated_pending_review"


class StrategyReviewReport(BaseModel):
    review_id: str
    spec_id: str
    code_package_id: str | None = None
    review_status: str
    blocking_issues: list[str] = Field(default_factory=list)
    non_blocking_issues: list[str] = Field(default_factory=list)
    template_compliance_score: float = Field(default=1.0, ge=0.0, le=1.0)
    contract_compliance_score: float = Field(default=1.0, ge=0.0, le=1.0)
    lookahead_safety_score: float = Field(default=1.0, ge=0.0, le=1.0)
    risk_compatibility_score: float = Field(default=1.0, ge=0.0, le=1.0)
    test_completeness_score: float = Field(default=1.0, ge=0.0, le=1.0)
    readiness_for_backtest: bool = False
    required_fixes: list[str] = Field(default_factory=list)
    audit_refs: list[str] = Field(default_factory=list)


class StrategyHandoffPackage(BaseModel):
    handoff_id: str
    spec_id: str
    code_package_id: str
    strategy_version: str
    generated_file_manifest: list[str]
    target_symbol: str
    target_timeframe: str
    data_requirements: list[str]
    cost_assumptions: list[str]
    execution_assumptions: list[str]
    risk_assumptions: list[str]
    test_plan: list[str]
    robustness_requirements: list[str]
    research_evidence_refs: list[str]
    reviewer_status: str
    known_limitations: list[str] = Field(default_factory=list)
    expected_failure_modes: list[str] = Field(default_factory=list)
    lifecycle_state: StrategyLifecycleState = StrategyLifecycleState.APPROVED_FOR_BACKTEST
