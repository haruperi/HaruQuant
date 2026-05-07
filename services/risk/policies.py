"""Deterministic risk policy rules."""

from __future__ import annotations

from typing import Any

from .broker_risk import broker_risk_state
from .correlation import correlation_failures, correlation_impact
from .drawdown import drawdown_state
from .exposure import concentration_failures, proposed_exposure_impact
from .margin import margin_failures, margin_impact

POLICY_VERSION = "risk_policy_v1"
APPROVED_LIFECYCLE_STATES = {"paper_approved", "paper_trading_candidate", "micro_live", "limited_live", "normal_live", "approved_for_paper"}


def validate_proposal(proposal: dict[str, Any]) -> list[str]:
    failures: list[str] = []
    for field in ("proposal_id", "strategy_id", "strategy_code_hash", "symbol", "side"):
        if not proposal.get(field):
            failures.append(f"missing_{field}")
    if float(proposal.get("requested_volume", proposal.get("requested_size", 0.0)) or 0.0) <= 0:
        failures.append("missing_requested_volume")
    lifecycle = proposal.get("strategy_lifecycle_state", "paper_approved")
    if lifecycle not in APPROVED_LIFECYCLE_STATES:
        failures.append("strategy_lifecycle_not_approved")
    if proposal.get("risk_model", {}).get("requires_stop_loss", True) and proposal.get("stop_loss") is None and not proposal.get("expected_risk"):
        failures.append("missing_stop_loss")
    return failures


def evaluate_policy(
    *,
    proposal: dict[str, Any],
    portfolio_snapshot: dict[str, Any],
    market_snapshot: dict[str, Any],
    thresholds: dict[str, Any],
    proposed_trade_risk: float,
) -> dict[str, Any]:
    failures = validate_proposal(proposal)
    warnings: list[str] = []
    if proposed_trade_risk > float(thresholds["max_risk_per_trade_pct"]):
        failures.append("max_risk_per_trade")
    elif proposed_trade_risk > float(thresholds["preferred_risk_per_trade_pct"]):
        warnings.append("preferred_risk_target_exceeded")
    drawdown = drawdown_state(portfolio_snapshot, thresholds)
    failures.extend(drawdown["failures"])
    exposure = proposed_exposure_impact(proposal, portfolio_snapshot)
    failures.extend(concentration_failures(exposure, thresholds))
    corr = correlation_impact(proposal, portfolio_snapshot)
    failures.extend(correlation_failures(corr, thresholds))
    margin = margin_impact(proposal, portfolio_snapshot)
    failures.extend(margin_failures(margin, thresholds))
    broker = broker_risk_state(market_snapshot, thresholds)
    failures.extend(broker["failures"])
    if portfolio_snapshot.get("kill_switch_active") or market_snapshot.get("kill_switch_active"):
        failures.append("kill_switch_active")
    if market_snapshot.get("news_block", False):
        failures.append("news_block")
    if int(portfolio_snapshot.get("open_positions", 0)) >= int(thresholds["max_open_positions"]):
        failures.append("max_open_positions")
    if int(portfolio_snapshot.get("live_strategies", 0)) > int(thresholds["max_live_strategies"]):
        failures.append("max_live_strategies")
    metrics = {
        "proposed_trade_risk": proposed_trade_risk,
        "drawdown": drawdown,
        "exposure": exposure,
        "correlation": corr,
        "margin": margin,
        "broker": broker,
        "open_positions": int(portfolio_snapshot.get("open_positions", 0)),
        "live_strategies": int(portfolio_snapshot.get("live_strategies", 0)),
    }
    return {"failures": list(dict.fromkeys(failures)), "warnings": warnings, "metrics": metrics, "critical": drawdown["critical"] or "kill_switch_active" in failures}


def approved_volume_for_policy(requested_volume: float, proposed_trade_risk: float, thresholds: dict[str, Any]) -> tuple[str, float]:
    preferred = float(thresholds["preferred_risk_per_trade_pct"])
    hard = float(thresholds["max_risk_per_trade_pct"])
    if proposed_trade_risk <= preferred:
        return "approved", requested_volume
    if proposed_trade_risk <= hard and proposed_trade_risk > 0:
        return "approved_with_reduced_size", max(0.0, requested_volume * preferred / proposed_trade_risk)
    return "rejected", 0.0
