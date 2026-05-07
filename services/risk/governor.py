"""Deterministic RiskGovernor service for HaruQuant."""

from __future__ import annotations

from dataclasses import asdict
from datetime import datetime, timezone
from typing import Any

from .approval_tokens import create_approval_token
from .audit import write_risk_audit
from .calculators import proposed_trade_risk, risk_reward_value, stop_loss_distance
from .contracts import RiskGovernorDecision, RiskProposal
from .exceptions import RiskError
from .policies import POLICY_VERSION, approved_volume_for_policy, evaluate_policy
from .signatures import sign_payload, stable_hash
from .thresholds import DEFAULT_RISK_THRESHOLDS, config_version_hash, load_risk_thresholds, validate_config_hash


def _normalize_proposal(proposal: dict[str, Any]) -> RiskProposal:
    requested = float(proposal.get("requested_volume", proposal.get("requested_size", proposal.get("size", 0.0))) or 0.0)
    return RiskProposal(
        proposal_id=str(proposal.get("proposal_id", "proposal-unknown")),
        proposal_type=str(proposal.get("proposal_type", "trade")),
        source_department=str(proposal.get("source_department", "portfolio")),
        source_agent=str(proposal.get("source_agent", "execution_planner_agent")),
        strategy_id=str(proposal.get("strategy_id", "strategy-unknown")),
        strategy_name=str(proposal.get("strategy_name", proposal.get("strategy_id", "strategy-unknown"))),
        strategy_version=str(proposal.get("strategy_version", "0.1.0")),
        strategy_code_hash=str(proposal.get("strategy_code_hash", "unknown")),
        strategy_lifecycle_state=str(proposal.get("strategy_lifecycle_state", "paper_approved")),
        symbol=str(proposal.get("symbol", "UNKNOWN")),
        asset_class=str(proposal.get("asset_class", "forex")),
        timeframe=str(proposal.get("timeframe", "H1")),
        side=str(proposal.get("side", "buy")),
        order_type=str(proposal.get("order_type", proposal.get("entry_type", "market"))),
        requested_volume=requested,
        requested_price=float(proposal.get("requested_price", proposal.get("price", 1.0)) or 1.0),
        stop_loss=proposal.get("stop_loss"),
        take_profit=proposal.get("take_profit"),
        expected_entry_time=proposal.get("expected_entry_time"),
        expected_holding_period=proposal.get("expected_holding_period"),
        setup_id=proposal.get("setup_id"),
        group_id=proposal.get("group_id"),
        risk_model=proposal.get("risk_model", {"requires_stop_loss": False}),
        strategy_risk_controls=proposal.get("strategy_risk_controls", {}),
        evidence_refs=proposal.get("evidence_refs", []),
        context_revision=proposal.get("context_revision"),
        created_at=str(proposal.get("created_at", datetime.now(timezone.utc).isoformat())),
    )


class RiskGovernor:
    component_name = "risk_governor"

    def __init__(self, *, thresholds: dict[str, Any] | None = None, config_hash: str | None = None) -> None:
        self.thresholds = {**load_risk_thresholds(), **(thresholds or {})}
        self.config_hash = config_hash or config_version_hash(self.thresholds)
        self.policy_version = POLICY_VERSION

    def evaluate_trade(
        self,
        *,
        proposal: dict[str, Any],
        portfolio_snapshot: dict[str, Any] | None = None,
        market_snapshot: dict[str, Any] | None = None,
    ) -> RiskGovernorDecision:
        portfolio_snapshot = portfolio_snapshot or {}
        market_snapshot = market_snapshot or {}
        try:
            if not validate_config_hash(self.thresholds, self.thresholds.get("config_hash")):
                return self._fail_closed(proposal_id=str(proposal.get("proposal_id", "proposal-unknown")), reason="invalid_config_hash")
            normalized = _normalize_proposal(proposal)
            account_equity = float(portfolio_snapshot.get("equity", 100000.0))
            trade_risk = proposed_trade_risk({**proposal, "requested_volume": normalized.requested_volume}, account_equity)
            policy = evaluate_policy(
                proposal={**asdict(normalized), **proposal},
                portfolio_snapshot=portfolio_snapshot,
                market_snapshot=market_snapshot,
                thresholds=self.thresholds,
                proposed_trade_risk=trade_risk,
            )
            decision_status, approved_volume = approved_volume_for_policy(normalized.requested_volume, trade_risk, self.thresholds)
            failures = policy["failures"]
            if failures:
                decision_status = "blocked" if policy["critical"] or "kill_switch_active" in failures else "rejected"
                approved_volume = 0.0
            decision_id = f"risk-decision-{stable_hash({'proposal_id': normalized.proposal_id, 'created_at': normalized.created_at})[:16]}"
            audit_payload = {
                "request_id": normalized.proposal_id,
                "component_name": self.component_name,
                "component_type": "deterministic_service",
                "proposal_id": normalized.proposal_id,
                "strategy_id": normalized.strategy_id,
                "strategy_code_hash": normalized.strategy_code_hash,
                "risk_config_hash": self.config_hash,
                "policy_version": self.policy_version,
                "rules_checked": self._rules_checked(),
                "rules_failed": failures,
                "decision": decision_status,
                "risk_level": self._risk_level(policy["metrics"], failures),
                "approved_volume": approved_volume,
                "blocked_actions": ["execute_trade_without_valid_token", "override_risk_governor"],
                "fallback_used": False,
                "error_if_any": None,
            }
            audit_ref = write_risk_audit("risk_governor", audit_payload)
            token = None
            approval_token_ref = None
            if decision_status in {"approved", "approved_with_reduced_size"}:
                token_obj = create_approval_token(
                    decision_id=decision_id,
                    proposal=normalized,
                    approved_volume=approved_volume,
                    risk_metrics_snapshot=policy["metrics"],
                    portfolio_snapshot=portfolio_snapshot,
                    market_snapshot=market_snapshot,
                    config_hash=self.config_hash,
                    policy_version=self.policy_version,
                    ttl_seconds=int(self.thresholds["approval_token_ttl_seconds"]),
                    audit_ref=audit_ref,
                )
                token = asdict(token_obj)
                approval_token_ref = token_obj.approval_id
            signature_payload = {"decision_id": decision_id, "decision": decision_status, "proposal_id": normalized.proposal_id, "approved_volume": approved_volume, "metrics": policy["metrics"]}
            signature = sign_payload(signature_payload, namespace="risk_governor_decision")
            rules_checked = self._rules_checked()
            rules_failed = failures
            rules_passed = [rule for rule in rules_checked if rule not in rules_failed]
            return RiskGovernorDecision(
                approval_id=approval_token_ref or f"risk-rejected-{signature[:16]}",
                proposal_id=normalized.proposal_id,
                decision=decision_status,
                approved_size=approved_volume,
                expires_at=token["expires_at"] if token else datetime.now(timezone.utc).isoformat(),
                risk_metrics_snapshot={**policy["metrics"], "r_value": risk_reward_value(asdict(normalized)), "stop_loss_distance": stop_loss_distance(asdict(normalized))},
                config_version_hash=self.config_hash,
                signature=signature,
                reasons=rules_failed,
                decision_id=decision_id,
                requested_volume=normalized.requested_volume,
                approved_volume=approved_volume,
                risk_level=self._risk_level(policy["metrics"], failures),
                rules_checked=rules_checked,
                rules_passed=rules_passed,
                rules_failed=rules_failed,
                rejection_reasons=rules_failed,
                warnings=policy["warnings"],
                required_actions=["submit_to_portfolio_department_with_token"] if token else ["resolve_risk_rejections"],
                approval_token_ref=approval_token_ref,
                approval_token=token,
                policy_version=self.policy_version,
                audit_ref=audit_ref,
            )
        except Exception as exc:
            if isinstance(exc, RiskError):
                reason = str(exc)
            else:
                reason = f"policy_engine_error:{exc.__class__.__name__}"
            return self._fail_closed(proposal_id=str(proposal.get("proposal_id", "proposal-unknown")), reason=reason)

    def _fail_closed(self, *, proposal_id: str, reason: str) -> RiskGovernorDecision:
        audit_ref = write_risk_audit("risk_governor_fail_closed", {"proposal_id": proposal_id, "decision": "error_fail_closed", "error_if_any": reason})
        signature = sign_payload({"proposal_id": proposal_id, "reason": reason}, namespace="risk_governor_fail_closed")
        return RiskGovernorDecision(
            approval_id=f"risk-fail-closed-{signature[:16]}",
            proposal_id=proposal_id,
            decision="error_fail_closed",
            approved_size=0.0,
            expires_at=datetime.now(timezone.utc).isoformat(),
            risk_metrics_snapshot={},
            config_version_hash=self.config_hash,
            signature=signature,
            reasons=[reason],
            decision_id=f"risk-decision-{signature[:16]}",
            risk_level="critical",
            rules_checked=self._rules_checked(),
            rules_failed=[reason],
            rejection_reasons=[reason],
            required_actions=["fail_closed_manual_review"],
            policy_version=self.policy_version,
            audit_ref=audit_ref,
        )

    def _rules_checked(self) -> list[str]:
        return [
            "proposal_schema",
            "strategy_lifecycle_state",
            "stop_loss_or_expected_risk",
            "max_risk_per_trade",
            "daily_weekly_monthly_loss",
            "portfolio_strategy_symbol_drawdown",
            "symbol_concentration",
            "currency_cluster_exposure",
            "margin_usage",
            "free_margin",
            "margin_level",
            "spread",
            "slippage",
            "news_block",
            "broker_anomaly",
            "kill_switch",
            "open_positions",
            "live_strategies",
        ]

    def _risk_level(self, metrics: dict[str, Any], failures: list[str]) -> str:
        if any(reason in failures for reason in {"kill_switch_active", "max_portfolio_drawdown", "max_daily_loss"}):
            return "critical"
        if failures:
            return "high"
        trade_risk = float(metrics.get("proposed_trade_risk", 0.0))
        if trade_risk > float(self.thresholds["preferred_risk_per_trade_pct"]):
            return "medium"
        return "low"


__all__ = ["DEFAULT_RISK_THRESHOLDS", "RiskGovernor", "RiskGovernorDecision"]
