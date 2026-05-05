"""Deterministic RiskGovernor service for HaruQuant."""

from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone
from typing import Any


DEFAULT_RISK_THRESHOLDS = {
    "max_risk_per_trade": 0.01,
    "max_daily_loss": 0.03,
    "max_weekly_loss": 0.06,
    "max_portfolio_drawdown": 0.12,
    "max_strategy_drawdown": 0.08,
    "max_symbol_concentration": 0.2,
    "max_correlated_exposure": 0.35,
    "max_total_margin_usage": 0.5,
    "max_open_positions": 10,
    "max_live_strategies": 3,
    "max_spread": 2.0,
    "max_slippage": 1.0,
}


@dataclass(frozen=True)
class RiskGovernorDecision:
    approval_id: str
    proposal_id: str
    decision: str
    approved_size: float
    expires_at: str
    risk_metrics_snapshot: dict[str, Any]
    config_version_hash: str
    signature: str
    reasons: list[str] = field(default_factory=list)


class RiskGovernor:
    def __init__(self, *, thresholds: dict[str, float] | None = None) -> None:
        self.thresholds = {**DEFAULT_RISK_THRESHOLDS, **(thresholds or {})}
        self.config_hash = hashlib.sha256(json.dumps(self.thresholds, sort_keys=True).encode("utf-8")).hexdigest()

    def evaluate_trade(
        self,
        *,
        proposal: dict[str, Any],
        portfolio_snapshot: dict[str, Any] | None = None,
        market_snapshot: dict[str, Any] | None = None,
    ) -> RiskGovernorDecision:
        portfolio_snapshot = portfolio_snapshot or {}
        market_snapshot = market_snapshot or {}
        proposal_id = str(proposal.get("proposal_id", "proposal-unknown"))
        requested_size = float(proposal.get("requested_size", proposal.get("size", 0.0)))
        account_equity = float(portfolio_snapshot.get("equity", 100000.0))
        expected_loss = float(proposal.get("expected_risk", {}).get("amount", requested_size * 100.0))
        proposed_trade_risk = expected_loss / max(account_equity, 1.0)
        metrics = {
            "proposed_trade_risk": proposed_trade_risk,
            "open_portfolio_exposure": float(portfolio_snapshot.get("open_exposure", 0.0)),
            "symbol_exposure": float(portfolio_snapshot.get("symbol_exposure", 0.0)),
            "currency_cluster_exposure": float(portfolio_snapshot.get("currency_cluster_exposure", 0.0)),
            "margin_impact": float(proposal.get("margin_impact", 0.0)),
            "var_impact": float(proposal.get("var_impact", proposed_trade_risk * 1.5)),
            "cvar_impact": float(proposal.get("cvar_impact", proposed_trade_risk * 2.0)),
            "correlation_impact": float(proposal.get("correlation_impact", 0.0)),
            "drawdown_state": float(portfolio_snapshot.get("drawdown", 0.0)),
            "daily_loss_state": float(portfolio_snapshot.get("daily_loss", 0.0)),
            "spread": float(market_snapshot.get("spread", proposal.get("max_spread", 0.0))),
            "slippage": float(market_snapshot.get("slippage", proposal.get("max_slippage", 0.0))),
            "open_positions": int(portfolio_snapshot.get("open_positions", 0)),
            "live_strategies": int(portfolio_snapshot.get("live_strategies", 0)),
            "news_block": bool(market_snapshot.get("news_block", False)),
            "broker_anomaly": bool(market_snapshot.get("broker_anomaly", False)),
        }
        reasons = self._rule_failures(metrics)
        decision = "approved" if not reasons else "rejected"
        approved_size = requested_size if decision == "approved" else 0.0
        expires_at = (datetime.now(timezone.utc) + timedelta(minutes=15)).isoformat()
        approval_id = f"risk-{hashlib.sha256((proposal_id + expires_at).encode('utf-8')).hexdigest()[:16]}"
        signature_payload = {"proposal_id": proposal_id, "decision": decision, "approved_size": approved_size, "metrics": metrics, "config_hash": self.config_hash}
        signature = hashlib.sha256(json.dumps(signature_payload, sort_keys=True).encode("utf-8")).hexdigest()
        return RiskGovernorDecision(
            approval_id=approval_id,
            proposal_id=proposal_id,
            decision=decision,
            approved_size=approved_size,
            expires_at=expires_at,
            risk_metrics_snapshot=metrics,
            config_version_hash=self.config_hash,
            signature=signature,
            reasons=reasons,
        )

    def _rule_failures(self, metrics: dict[str, Any]) -> list[str]:
        failures: list[str] = []
        checks = {
            "max_risk_per_trade": metrics["proposed_trade_risk"],
            "max_daily_loss": metrics["daily_loss_state"],
            "max_portfolio_drawdown": metrics["drawdown_state"],
            "max_symbol_concentration": metrics["symbol_exposure"],
            "max_correlated_exposure": metrics["correlation_impact"],
            "max_total_margin_usage": metrics["margin_impact"],
            "max_spread": metrics["spread"],
            "max_slippage": metrics["slippage"],
        }
        for key, value in checks.items():
            if value > self.thresholds[key]:
                failures.append(key)
        if metrics["open_positions"] >= self.thresholds["max_open_positions"]:
            failures.append("max_open_positions")
        if metrics["live_strategies"] > self.thresholds["max_live_strategies"]:
            failures.append("max_live_strategies")
        if metrics["news_block"]:
            failures.append("news_block")
        if metrics["broker_anomaly"]:
            failures.append("broker_anomaly")
        return failures


__all__ = ["DEFAULT_RISK_THRESHOLDS", "RiskGovernor", "RiskGovernorDecision"]
