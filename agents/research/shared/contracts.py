"""Pydantic schemas shared by Research Department agents."""

from __future__ import annotations

from enum import Enum
from typing import Any

from pydantic import BaseModel, Field

from agents._shared.base_contracts import ConfidenceLevel
from .constants import DEFAULT_DATA_WINDOW, DEFAULT_TIMEFRAME, DEPARTMENT_NAME, RESEARCH_AGENT_VERSION


class SourceType(str, Enum):
    MARKET_DATA = "market_data"
    NEWS = "news"
    SENTIMENT = "sentiment"
    MACRO = "macro"
    INTERNAL_MEMORY = "internal_memory"
    TECHNICAL_ANALYSIS = "technical_analysis"
    COMPUTED = "computed"


class EvidenceQuality(str, Enum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"


class ValidationStatus(str, Enum):
    APPROVED = "approved"
    APPROVED_WITH_CAUTION = "approved_with_caution"
    NEEDS_MORE_EVIDENCE = "needs_more_evidence"
    REJECTED = "rejected"


class StrategyFamily(str, Enum):
    TREND_FOLLOWING = "trend_following"
    MEAN_REVERSION = "mean_reversion"
    BREAKOUT = "breakout"
    MOMENTUM = "momentum"
    STATISTICAL_ARBITRAGE = "statistical_arbitrage"
    UNKNOWN = "unknown"


class ResearchRequestPayload(BaseModel):
    research_question: str | None = None
    symbol: str | None = None
    symbols: list[str] = Field(default_factory=list)
    asset_class: str | None = None
    timeframe: str | None = DEFAULT_TIMEFRAME
    timeframes: list[str] = Field(default_factory=list)
    data_window: str = DEFAULT_DATA_WINDOW
    research_objective: str | None = None
    include_tick_data: bool = False
    include_spread_analysis: bool = True
    include_session_context: bool = True
    include_volatility_context: bool = True
    constraints: dict[str, Any] = Field(default_factory=dict)
    context_revision: str | None = None
    evidence_refs: list[str] = Field(default_factory=list)


class ResearchSourceRef(BaseModel):
    source_type: SourceType = SourceType.COMPUTED
    source_name: str
    source_url_or_path: str | None = None
    retrieved_at: str | None = None
    published_at: str | None = None
    reliability_score: float = Field(default=0.75, ge=0.0, le=1.0)


class ResearchEvidenceRef(BaseModel):
    evidence_id: str
    source_type: SourceType = SourceType.COMPUTED
    source_name: str
    source_url_or_path: str | None = None
    retrieved_at: str | None = None
    published_at: str | None = None
    symbol_relevance: float = Field(default=1.0, ge=0.0, le=1.0)
    timeframe_relevance: float = Field(default=1.0, ge=0.0, le=1.0)
    claim_supported: str = ""
    evidence_summary: str = ""
    confidence: ConfidenceLevel = ConfidenceLevel.MEDIUM
    reliability_score: float = Field(default=0.75, ge=0.0, le=1.0)
    freshness_score: float = Field(default=0.75, ge=0.0, le=1.0)
    contradiction_flag: bool = False
    used_by_report_ids: list[str] = Field(default_factory=list)
    used_by_strategy_ids: list[str] = Field(default_factory=list)
    expiry_date: str | None = None
    permission_profile: str = "research_read_only_v1"
    audit: dict[str, Any] = Field(default_factory=dict)


class MarketContext(BaseModel):
    market_regime: str = "unknown"
    volatility_regime: str = "unknown"
    liquidity_regime: str = "unknown"
    spread_pips: float | None = None
    session: str | None = None


class TechnicalContext(BaseModel):
    trend_state: str = "unknown"
    momentum_state: str = "unknown"
    support_resistance_summary: str | None = None
    indicator_snapshot: dict[str, Any] = Field(default_factory=dict)


class MacroContext(BaseModel):
    macro_regime: str = "unknown"
    key_drivers: list[str] = Field(default_factory=list)
    event_risk: str = "unknown"


class SentimentContext(BaseModel):
    sentiment_label: str = "unknown"
    sentiment_score: float | None = None
    news_risk: str = "unknown"


class CrossAssetContext(BaseModel):
    related_symbols: list[str] = Field(default_factory=list)
    correlation_summary: str | None = None
    divergence_flags: list[str] = Field(default_factory=list)


class SeasonalityContext(BaseModel):
    calendar_pattern: str = "unknown"
    session_pattern: str = "unknown"
    seasonal_bias: str = "unknown"


class StrategyIdea(BaseModel):
    idea_id: str
    idea_name: str
    idea_family: StrategyFamily = StrategyFamily.UNKNOWN
    symbol: str
    timeframe: str = DEFAULT_TIMEFRAME
    market_regime: str = "unknown"
    edge_hypothesis: str = ""
    entry_concept: str = ""
    exit_concept: str = ""
    risk_concept: str = ""
    position_management_concept: str = ""
    required_indicators: list[str] = Field(default_factory=list)
    required_data: list[str] = Field(default_factory=list)
    expected_trade_frequency: str | None = None
    expected_holding_period: str | None = None
    expected_market_condition: str | None = None
    expected_failure_condition: str | None = None
    novelty_score: float = Field(default=0.5, ge=0.0, le=1.0)
    feasibility_score: float = Field(default=0.5, ge=0.0, le=1.0)
    edge_plausibility_score: float = Field(default=0.5, ge=0.0, le=1.0)
    testability_score: float = Field(default=0.5, ge=0.0, le=1.0)
    risk_compatibility_score: float = Field(default=0.5, ge=0.0, le=1.0)
    portfolio_value_score: float = Field(default=0.5, ge=0.0, le=1.0)
    complexity_score: float = Field(default=0.5, ge=0.0, le=1.0)
    execution_sensitivity_score: float = Field(default=0.5, ge=0.0, le=1.0)
    overfitting_risk_score: float = Field(default=0.5, ge=0.0, le=1.0)
    overall_research_score: float = Field(default=0.5, ge=0.0, le=1.0)
    recommended_backtest_plan: str | None = None
    recommended_robustness_tests: list[str] = Field(default_factory=list)
    minimum_acceptance_criteria: list[str] = Field(default_factory=list)
    rejection_criteria: list[str] = Field(default_factory=list)
    evidence_refs: list[str] = Field(default_factory=list)
    status: ValidationStatus = ValidationStatus.NEEDS_MORE_EVIDENCE
    audit: dict[str, Any] = Field(default_factory=dict)


class StrategyHypothesis(BaseModel):
    hypothesis_id: str
    parent_idea_id: str | None = None
    hypothesis_title: str
    hypothesis_statement: str
    edge_rationale: str = ""
    target_symbols: list[str] = Field(default_factory=list)
    target_timeframes: list[str] = Field(default_factory=list)
    target_market_regimes: list[str] = Field(default_factory=list)
    entry_logic_concept: str = ""
    exit_logic_concept: str = ""
    risk_logic_concept: str = ""
    position_management_concept: str = ""
    required_data: list[str] = Field(default_factory=list)
    required_indicators: list[str] = Field(default_factory=list)
    expected_trade_frequency: str | None = None
    expected_holding_period: str | None = None
    expected_failure_modes: list[str] = Field(default_factory=list)
    backtest_requirements: list[str] = Field(default_factory=list)
    minimum_sample_size: int = 100
    robustness_tests: list[str] = Field(default_factory=list)
    acceptance_criteria: list[str] = Field(default_factory=list)
    rejection_criteria: list[str] = Field(default_factory=list)
    evidence_refs: list[str] = Field(default_factory=list)
    validation_status: ValidationStatus = ValidationStatus.NEEDS_MORE_EVIDENCE
    audit: dict[str, Any] = Field(default_factory=dict)


class ResearchValidationResult(BaseModel):
    validation_status: ValidationStatus
    validation_score: float = Field(ge=0.0, le=1.0)
    approval_or_rejection_reasons: list[str] = Field(default_factory=list)
    bias_warnings: list[str] = Field(default_factory=list)
    missing_evidence: list[str] = Field(default_factory=list)


class ResearchToStrategyHandoff(BaseModel):
    handoff_id: str
    research_report_id: str
    approved_hypothesis_id: str
    target_symbol: str
    target_asset_class: str | None = None
    target_timeframe: str = DEFAULT_TIMEFRAME
    strategy_family: StrategyFamily = StrategyFamily.UNKNOWN
    market_regime: str = "unknown"
    volatility_regime: str = "unknown"
    session_context: str | None = None
    entry_concept: str = ""
    exit_concept: str = ""
    risk_concept: str = ""
    position_management_concept: str = ""
    required_indicators: list[str] = Field(default_factory=list)
    required_datasets: list[str] = Field(default_factory=list)
    initial_parameter_suggestions: dict[str, Any] = Field(default_factory=dict)
    backtest_design: dict[str, Any] = Field(default_factory=dict)
    robustness_test_recommendations: list[str] = Field(default_factory=list)
    minimum_acceptance_criteria: list[str] = Field(default_factory=list)
    rejection_criteria: list[str] = Field(default_factory=list)
    evidence_refs: list[str] = Field(default_factory=list)
    validation_notes: list[str] = Field(default_factory=list)
    risk_warnings: list[str] = Field(default_factory=list)
    execution_warnings: list[str] = Field(default_factory=list)
    portfolio_warnings: list[str] = Field(default_factory=list)
    validation_status: ValidationStatus = ValidationStatus.APPROVED_WITH_CAUTION
    handoff_status: str = "ready_for_strategy_development"
    audit: dict[str, Any] = Field(default_factory=dict)


class ResearchAgentArtifact(BaseModel):
    report_id: str
    report_type: str
    agent_name: str
    department: str = DEPARTMENT_NAME
    agent_version: str = RESEARCH_AGENT_VERSION
    created_at: str | None = None
    research_question: str | None = None
    symbol: str | None = None
    asset_class: str | None = None
    timeframes: list[str] = Field(default_factory=list)
    data_window: str = DEFAULT_DATA_WINDOW
    data_sources: list[str] = Field(default_factory=list)
    sources_used: list[ResearchSourceRef] = Field(default_factory=list)
    data_quality_score: float = Field(default=0.75, ge=0.0, le=1.0)
    research_scope: str | None = None
    assumptions: list[str] = Field(default_factory=list)
    limitations: list[str] = Field(default_factory=list)
    evidence_refs: list[str] = Field(default_factory=list)
    audit: dict[str, Any] = Field(default_factory=dict)


class ResearchReportArtifact(ResearchAgentArtifact):
    market_context: MarketContext | None = None
    market_regime: str = "unknown"
    volatility_regime: str = "unknown"
    liquidity_regime: str = "unknown"
    session_context: str | None = None
    macro_context: MacroContext | None = None
    sentiment_context: SentimentContext | None = None
    technical_context: TechnicalContext | None = None
    intermarket_context: CrossAssetContext | None = None
    seasonality_context: SeasonalityContext | None = None
    strategy_family_suitability: dict[str, float] = Field(default_factory=dict)
    candidate_ideas: list[StrategyIdea] = Field(default_factory=list)
    hypotheses: list[StrategyHypothesis] = Field(default_factory=list)
    rejected_ideas: list[StrategyIdea] = Field(default_factory=list)
    risks: list[str] = Field(default_factory=list)
    supporting_evidence: list[ResearchEvidenceRef] = Field(default_factory=list)
    contradicting_evidence: list[ResearchEvidenceRef] = Field(default_factory=list)
    unknowns: list[str] = Field(default_factory=list)
    bias_warnings: list[str] = Field(default_factory=list)
    execution_warnings: list[str] = Field(default_factory=list)
    risk_warnings: list[str] = Field(default_factory=list)
    portfolio_warnings: list[str] = Field(default_factory=list)
    recommended_next_steps: list[str] = Field(default_factory=list)
    confidence: ConfidenceLevel = ConfidenceLevel.MEDIUM
    validation_status: ValidationStatus = ValidationStatus.NEEDS_MORE_EVIDENCE
    validation_notes: list[str] = Field(default_factory=list)
    handoff_target: str | None = None
    handoff_payload: ResearchToStrategyHandoff | None = None
    expiry_date: str | None = None
    requires_refresh: bool = False
    parent_report_ids: list[str] = Field(default_factory=list)
    linked_strategy_ids: list[str] = Field(default_factory=list)
    linked_backtest_ids: list[str] = Field(default_factory=list)
    linked_evidence_ids: list[str] = Field(default_factory=list)
