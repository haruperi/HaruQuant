"""Shared Simulation Department contracts."""

from __future__ import annotations

from typing import Any

from pydantic import BaseModel, Field, field_validator


class SimulationRequestPayload(BaseModel):
    strategy_id: str
    strategy_version: str = "0.1.0"
    strategy_code_hash: str
    strategy_spec_id: str | None = None
    symbol: str
    timeframe: str
    data_start: str
    data_end: str
    initial_balance: float = Field(gt=0)
    commission_model: dict[str, Any]
    spread_model: dict[str, Any]
    slippage_model: dict[str, Any]
    swap_model: dict[str, Any] | None = None
    execution_mode: str
    data_mode: str = "ohlcv"
    margin_mode: str | None = None
    benchmark_symbol: str | None = None
    strategy_review_status: str = "approved_for_backtest"
    tags: list[str] = Field(default_factory=list)
    optimization_requested: bool = False
    robustness_requested: bool = True
    statistical_validation_requested: bool = True
    research_evidence_refs: list[str] = Field(default_factory=list)
    historical_data: list[dict[str, Any]] = Field(default_factory=list)
    returns: list[float] = Field(default_factory=list)
    metrics: dict[str, Any] = Field(default_factory=dict)

    @field_validator("strategy_id", "strategy_code_hash", "symbol", "timeframe", "data_start", "data_end", "execution_mode")
    @classmethod
    def _required_text(cls, value: str) -> str:
        if not value or not value.strip():
            raise ValueError("field must not be empty")
        return value


class BacktestRunManifest(BaseModel):
    run_id: str
    strategy_id: str
    strategy_version: str
    strategy_code_hash: str
    strategy_spec_id: str | None = None
    symbol: str
    timeframe: str
    data_start: str
    data_end: str
    data_hash: str
    config_hash: str
    engine_version: str
    analytics_version: str
    created_at: str
    artifact_root: str
    status: str


class BacktestResultPackage(BaseModel):
    run_id: str
    artifact_root: str
    config_path: str
    trades_path: str
    orders_path: str
    deals_path: str
    equity_curve_path: str
    metrics_path: str
    analytics_path: str
    report_path: str
    audit_path: str
    manifest_path: str


class SimulationDecisionArtifact(BaseModel):
    lifecycle_state: str
    acceptance_status: str
    evidence_quality: str
    deployment_recommendation: str
    reasons: list[str] = Field(default_factory=list)
    blocked_next_steps: list[str] = Field(default_factory=list)
    allowed_next_steps: list[str] = Field(default_factory=list)
    required_followups: list[str] = Field(default_factory=list)


class SimulationToRiskHandoff(BaseModel):
    strategy_id: str
    strategy_version: str
    strategy_code_hash: str
    strategy_spec_id: str | None = None
    baseline_backtest_run_id: str
    diagnosis_report_id: str
    optimization_run_id: str | None = None
    recommended_parameter_set_id: str | None = None
    robustness_report_id: str
    statistical_validation_report_id: str
    evidence_rating: str
    robustness_score: float
    simulation_acceptance_status: str
    known_failure_modes: list[str] = Field(default_factory=list)
    risk_concerns: list[str] = Field(default_factory=list)
    cost_sensitivity: dict[str, Any] = Field(default_factory=dict)
    drawdown_profile: dict[str, Any] = Field(default_factory=dict)
    tail_risk_profile: dict[str, Any] = Field(default_factory=dict)
    recommended_risk_limits: dict[str, Any] = Field(default_factory=dict)
    blocked_conditions: list[str] = Field(default_factory=list)
    paper_trading_recommendation: str = "risk_review_required"
    evidence_refs: list[str] = Field(default_factory=list)
    artifact_refs: list[str] = Field(default_factory=list)
    audit_refs: list[str] = Field(default_factory=list)
