"""Deterministic Simulation Department acceptance rules."""

from __future__ import annotations

from datetime import date
from typing import Any

from .constants import MAX_DRAWDOWN, MAX_PROFIT_CONCENTRATION, MIN_COST_EDGE_RATIO, MIN_TRADE_COUNT, SUPPORTED_EXECUTION_MODES, SUPPORTED_MARGIN_MODES, SUPPORTED_TIMEFRAMES
from .contracts import SimulationRequestPayload


def validate_request(payload: SimulationRequestPayload) -> list[str]:
    failures: list[str] = []
    if payload.strategy_review_status not in {"approved_for_backtest", "approved", "passed"}:
        failures.append("strategy_not_approved_by_reviewer")
    if not payload.strategy_code_hash:
        failures.append("missing_strategy_code_hash")
    try:
        if date.fromisoformat(payload.data_start) >= date.fromisoformat(payload.data_end):
            failures.append("invalid_simulation_period")
    except ValueError:
        failures.append("invalid_simulation_period")
    if payload.timeframe not in SUPPORTED_TIMEFRAMES:
        failures.append("unsupported_timeframe")
    if payload.execution_mode not in SUPPORTED_EXECUTION_MODES:
        failures.append("unsupported_execution_mode")
    if payload.margin_mode not in SUPPORTED_MARGIN_MODES:
        failures.append("unsupported_margin_mode")
    if not payload.commission_model:
        failures.append("missing_commission_model")
    if not payload.spread_model:
        failures.append("missing_spread_model")
    if not payload.slippage_model:
        failures.append("missing_slippage_model")
    return failures


def validate_data(payload: SimulationRequestPayload) -> list[str]:
    failures: list[str] = []
    if len(payload.historical_data) < 30:
        failures.append("insufficient_market_data")
    required = {"open", "high", "low", "close", "volume"}
    if payload.historical_data and not required.issubset(payload.historical_data[0]):
        failures.append("missing_required_ohlcv_columns")
    return failures


def evaluate_backtest(metrics: dict[str, Any]) -> list[str]:
    failures: list[str] = []
    if int(metrics.get("trade_count", 0)) < MIN_TRADE_COUNT:
        failures.append("too_few_trades")
    if float(metrics.get("profit_concentration", 1.0)) > MAX_PROFIT_CONCENTRATION:
        failures.append("profit_from_too_few_trades")
    if abs(float(metrics.get("max_drawdown", 0.0))) > MAX_DRAWDOWN:
        failures.append("drawdown_exceeds_policy")
    if float(metrics.get("cost_edge_ratio", 0.0)) < MIN_COST_EDGE_RATIO:
        failures.append("costs_destroy_edge")
    if not metrics.get("reproducible", False):
        failures.append("not_reproducible")
    return failures


def final_acceptance(child_statuses: dict[str, str], evidence_rating: str, robustness_score: float) -> tuple[str, list[str]]:
    reasons = []
    for name, status in child_statuses.items():
        if status not in {"success", "pass", "needs_more_context"}:
            reasons.append(f"{name}_failed")
    if evidence_rating == "weak":
        reasons.append("statistical_evidence_weak")
    if robustness_score < 0.8:
        reasons.append("robustness_gate_failed")
    return ("rejected" if reasons else "approved_for_risk_review", reasons or ["simulation_gates_passed"])
