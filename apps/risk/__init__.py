"""Risk engine compatibility shim.
Re-exports from backend.services.risk_engine for apps/live/ until Phase 15.
"""

from backend.services.risk_engine import (
    # core
    GovernanceEngine,
    GovernanceReport,
    PortfolioRiskEngine,
    PortfolioStateEngine,
    RecommendationEngine,
    RiskScorecardEngine,
    RiskSnapshotEngine,
    TimelineReconstructor,
    TimelinePoint,
    # limits
    BudgetUtilization,
    CircuitBreakerState,
    CorrelationPreference,
    GovernanceState,
    LimitEvent,
    OverrideRecord,
    PolicyDecision,
    PolicyEngine,
    RiskLimits,
    RiskPolicy,
    # models
    AccountState,
    MarketState,
    PortfolioState,
    PositionState,
    SymbolState,
    # position_sizing
    PositionSizer,
    estimate_kelly_parameters,
    validate_position_size,
    # optimization
    AllocationOptimizer,
    AllocationPlanner,
    CapitalEfficiencyRanker,
    HedgeOptimizer,
    MarginalRiskEvaluator,
    RecommendationAction,
    RecommendationBatch,
    RecommendationResult,
    RecommendationScore,
    RebalanceSuggestionEngine,
    clone_state_with_delta,
    # regimes
    CrisisRegimeDetector,
    LiquidityRegimeDetector,
    MarketRegimeDetector,
    RegimeEngine,
    RegimeReport,
    RegimeSignal,
    RegimeState,
    RegimeTransition,
    RegimeTransitionReport,
    RiskRegimeDetector,
    VolatilityRegimeDetector,
    build_regime_transition,
    # scenarios
    ScenarioRegistry,
    ScenarioResult,
    StressScenario,
    build_default_scenario_registry,
    evaluate_scenarios,
    # scoring
    RiskScorecard,
    ScoreContext,
    ScoreFamily,
    ScoreRegistry,
    ScoreRow,
    build_default_score_registry,
    # simulation
    CockpitStatePayload,
    HypotheticalOrderAction,
    ReplayClock,
    ReplayFrame,
    ReplayRun,
    WhatIfComparison,
    WhatIfEngine,
    apply_hypothetical_actions,
    build_cockpit_state,
    # storage
    RiskRepository,
    RiskScenarioStore,
    RiskSnapshotStore,
    # metrics
    MetricContext,
    MetricFamily,
    MetricRegistry,
    MetricRow,
    RiskSnapshot,
    build_default_metric_registry,
    build_returns_df,
    compute_portfolio_var_es,
    extract_currency_exposure,
    estimate_margin_used,
    symbol_notional_value,
    # validators
    ValidationIssue,
    ValidationSummary,
    validate_account_state,
    validate_market_states,
    validate_position_states,
    validate_risk_limits,
    validate_symbol_states,
)

__all__ = [
    # core
    "GovernanceEngine", "GovernanceReport", "PortfolioRiskEngine",
    "PortfolioStateEngine", "RecommendationEngine", "RiskScorecardEngine",
    "RiskSnapshotEngine", "TimelineReconstructor", "TimelinePoint",
    # limits
    "BudgetUtilization", "CircuitBreakerState", "CorrelationPreference",
    "GovernanceState", "LimitEvent", "OverrideRecord", "PolicyDecision",
    "PolicyEngine", "RiskLimits", "RiskPolicy",
    # models
    "AccountState", "MarketState", "PortfolioState", "PositionState", "SymbolState",
    # position_sizing
    "PositionSizer", "estimate_kelly_parameters", "validate_position_size",
    # optimization
    "AllocationOptimizer", "AllocationPlanner", "CapitalEfficiencyRanker",
    "HedgeOptimizer", "MarginalRiskEvaluator", "RecommendationAction",
    "RecommendationBatch", "RecommendationResult", "RecommendationScore",
    "RebalanceSuggestionEngine", "clone_state_with_delta",
    # regimes
    "CrisisRegimeDetector", "LiquidityRegimeDetector", "MarketRegimeDetector",
    "RegimeEngine", "RegimeReport", "RegimeSignal", "RegimeState",
    "RegimeTransition", "RegimeTransitionReport", "RiskRegimeDetector",
    "VolatilityRegimeDetector", "build_regime_transition",
    # scenarios
    "ScenarioRegistry", "ScenarioResult", "StressScenario",
    "build_default_scenario_registry", "evaluate_scenarios",
    # scoring
    "RiskScorecard", "ScoreContext", "ScoreFamily", "ScoreRegistry", "ScoreRow",
    "build_default_score_registry",
    # simulation
    "CockpitStatePayload", "HypotheticalOrderAction", "ReplayClock",
    "ReplayFrame", "ReplayRun", "WhatIfComparison", "WhatIfEngine",
    "apply_hypothetical_actions", "build_cockpit_state",
    # storage
    "RiskRepository", "RiskScenarioStore", "RiskSnapshotStore",
    # metrics
    "MetricContext", "MetricFamily", "MetricRegistry", "MetricRow",
    "RiskSnapshot", "build_default_metric_registry", "build_returns_df",
    "compute_portfolio_var_es", "extract_currency_exposure",
    "estimate_margin_used", "symbol_notional_value",
    # validators
    "ValidationIssue", "ValidationSummary", "validate_account_state",
    "validate_market_states", "validate_position_states", "validate_risk_limits",
    "validate_symbol_states",
]
