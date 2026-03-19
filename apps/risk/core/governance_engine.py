"""Canonical governance entry point built on shared risk engines."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, List, Literal, Optional

from apps.risk.limits import (
    GovernanceState,
    LimitEvent,
    OverrideRecord,
    PolicyEngine,
    RiskLimits,
)
from apps.risk.models import PortfolioState
from apps.risk.regimes import RegimeState

from .portfolio_risk_engine import PortfolioRiskEngine

Decision = Literal["ACCEPT", "REJECT"]


@dataclass(frozen=True)
class GovernanceReport:
    """Normalized governance decision/report object."""

    decision: Decision
    reason: str
    current_var: float
    new_var: float
    delta_var: float
    current_es: float
    new_es: float
    delta_es: float
    current_margin_used: Optional[float] = None
    new_margin_used: Optional[float] = None
    rc_map_new: Optional[Dict[str, float]] = None
    rc_violations: Optional[List[str]] = None
    cluster_violations: Optional[List[str]] = None
    warnings: Optional[List[LimitEvent]] = None
    breaches: Optional[List[LimitEvent]] = None
    overrides: Optional[List[OverrideRecord]] = None
    governance_state: Optional[GovernanceState] = None
    policy_events: Optional[List[LimitEvent]] = None


class GovernanceEngine:
    """Evaluate governance decisions from raw positions or canonical state."""

    def __init__(
        self,
        risk_engine: PortfolioRiskEngine,
        limits: RiskLimits,
        policy_engine: Optional[PolicyEngine] = None,
    ):
        self.risk_engine = risk_engine
        self.limits = limits
        self.policy_engine = policy_engine or PolicyEngine()

    def effective_limits(self, regime: Optional[RegimeState]) -> RiskLimits:
        """Return the effective limits after regime overrides."""
        return self.policy_engine.effective_policy(self.limits, regime)[0]

    def evaluate_add_position(
        self,
        current_positions: Dict[str, float],
        candidate_symbol: str,
        candidate_lots: float,
        symbol_to_cluster: Optional[Dict[str, str]] = None,
        regime: Optional[RegimeState] = None,
    ) -> GovernanceReport:
        """Evaluate a candidate position change from raw position maps."""
        new_positions = dict(current_positions)
        new_positions[candidate_symbol] = (
            new_positions.get(candidate_symbol, 0.0) + candidate_lots
        )
        if abs(new_positions[candidate_symbol]) < 1e-12:
            del new_positions[candidate_symbol]

        forced_decision: Optional[Decision] = None
        forced_reason: Optional[str] = None
        if len(new_positions) < len(current_positions):
            forced_decision = "ACCEPT"
            forced_reason = "Candidate reduces or nets existing exposure."

        return self.evaluate_transition(
            current_positions=current_positions,
            new_positions=new_positions,
            symbol_to_cluster=symbol_to_cluster,
            regime=regime,
            forced_decision=forced_decision,
            forced_reason=forced_reason,
        )

    def evaluate_transition(
        self,
        current_positions: Dict[str, float],
        new_positions: Dict[str, float],
        symbol_to_cluster: Optional[Dict[str, str]] = None,
        regime: Optional[RegimeState] = None,
        forced_decision: Optional[Decision] = None,
        forced_reason: Optional[str] = None,
    ) -> GovernanceReport:
        """Evaluate a raw position transition."""
        eff = self.effective_limits(regime)
        equity = float(self.risk_engine.mt5_client.get_account_equity())
        cur_var, cur_es, cur_margin, _ = self.risk_engine.compute_portfolio_risk(
            current_positions,
            equity,
            eff,
        )
        new_var, new_es, new_margin, rc_map_new = self.risk_engine.compute_portfolio_risk(
            new_positions,
            equity,
            eff,
        )
        delta_var = new_var - cur_var
        delta_es = new_es - cur_es
        cluster_metrics = self.risk_engine.compute_cluster_metrics(
            new_positions,
            equity,
            symbol_to_cluster,
            eff,
        )
        policy_decision = self.policy_engine.evaluate_pre_trade(
            equity=equity,
            current_var=cur_var,
            new_var=new_var,
            delta_var=delta_var,
            current_es=cur_es,
            new_es=new_es,
            delta_es=delta_es,
            current_margin_used=cur_margin,
            new_margin_used=new_margin,
            rc_map_new=rc_map_new,
            cluster_metrics=cluster_metrics,
            policy=eff,
            regime=regime,
            peak_equity=self._get_peak_equity(),
        )
        if forced_decision is not None and forced_reason is not None:
            policy_decision = type(policy_decision)(
                decision=forced_decision,
                reason=forced_reason,
                breaches=policy_decision.breaches,
                warnings=policy_decision.warnings,
                overrides=policy_decision.overrides,
                governance_state=policy_decision.governance_state,
                circuit_breaker_state=policy_decision.circuit_breaker_state,
            )
        return self._build_report(
            policy_decision=policy_decision,
            current_var=cur_var,
            new_var=new_var,
            delta_var=delta_var,
            current_es=cur_es,
            new_es=new_es,
            delta_es=delta_es,
            current_margin_used=cur_margin,
            new_margin_used=new_margin,
            rc_map_new=rc_map_new,
        )

    def evaluate_portfolio_positions(
        self,
        positions: Dict[str, float],
        symbol_to_cluster: Optional[Dict[str, str]] = None,
        regime: Optional[RegimeState] = None,
    ) -> GovernanceReport:
        """Evaluate the current raw portfolio compliance state."""
        eff = self.effective_limits(regime)
        equity = float(self.risk_engine.mt5_client.get_account_equity())
        portfolio_var, portfolio_es, margin_used, rc_map = self.risk_engine.compute_portfolio_risk(
            positions,
            equity,
            eff,
        )
        cluster_metrics = self.risk_engine.compute_cluster_metrics(
            positions,
            equity,
            symbol_to_cluster,
            eff,
        )
        policy_decision = self.policy_engine.evaluate_post_trade(
            equity=equity,
            portfolio_var=portfolio_var,
            portfolio_es=portfolio_es,
            margin_used=margin_used,
            rc_map=rc_map,
            cluster_metrics=cluster_metrics,
            policy=eff,
            regime=regime,
            peak_equity=self._get_peak_equity(),
        )
        return self._build_report(
            policy_decision=policy_decision,
            current_var=portfolio_var,
            new_var=portfolio_var,
            delta_var=0.0,
            current_es=portfolio_es,
            new_es=portfolio_es,
            delta_es=0.0,
            current_margin_used=margin_used,
            new_margin_used=margin_used,
            rc_map_new=rc_map,
        )

    def evaluate_portfolio_state(
        self,
        state: PortfolioState,
        regime: Optional[RegimeState] = None,
    ) -> GovernanceReport:
        """Evaluate current compliance from canonical portfolio state."""
        eff = self.effective_limits(regime)
        portfolio_var, portfolio_es, margin_used, rc_map = self.risk_engine.compute_portfolio_risk_from_state(
            state,
            limits=eff,
        )
        cluster_metrics = self.risk_engine.compute_cluster_metrics_from_state(
            state,
            limits=eff,
        )
        policy_decision = self.policy_engine.evaluate_post_trade(
            equity=float(state.account.equity),
            portfolio_var=portfolio_var,
            portfolio_es=portfolio_es,
            margin_used=margin_used,
            rc_map=rc_map,
            cluster_metrics=cluster_metrics,
            policy=eff,
            regime=regime,
            peak_equity=self._extract_peak_equity_from_state(state),
        )
        return self._build_report(
            policy_decision=policy_decision,
            current_var=portfolio_var,
            new_var=portfolio_var,
            delta_var=0.0,
            current_es=portfolio_es,
            new_es=portfolio_es,
            delta_es=0.0,
            current_margin_used=margin_used,
            new_margin_used=margin_used,
            rc_map_new=rc_map,
        )

    def _build_report(
        self,
        policy_decision,
        current_var: float,
        new_var: float,
        delta_var: float,
        current_es: float,
        new_es: float,
        delta_es: float,
        current_margin_used: Optional[float],
        new_margin_used: Optional[float],
        rc_map_new: Optional[Dict[str, float]],
    ) -> GovernanceReport:
        return GovernanceReport(
            decision=policy_decision.decision,
            reason=policy_decision.reason,
            current_var=current_var,
            new_var=new_var,
            delta_var=delta_var,
            current_es=current_es,
            new_es=new_es,
            delta_es=delta_es,
            current_margin_used=current_margin_used,
            new_margin_used=new_margin_used,
            rc_map_new=rc_map_new,
            rc_violations=self._rc_violation_symbols(policy_decision.breaches) or None,
            cluster_violations=self._cluster_violation_messages(policy_decision.breaches) or None,
            warnings=policy_decision.warnings or None,
            breaches=policy_decision.breaches or None,
            overrides=policy_decision.overrides or None,
            governance_state=policy_decision.governance_state,
            policy_events=policy_decision.policy_events or None,
        )

    def _rc_violation_symbols(self, breaches: Optional[List[LimitEvent]]) -> List[str]:
        if not breaches:
            return []
        return [
            event.scope_key
            for event in breaches
            if event.rule_key == "single_rc_cap" and event.scope_key
        ]

    def _cluster_violation_messages(self, breaches: Optional[List[LimitEvent]]) -> List[str]:
        if not breaches:
            return []
        messages = []
        for event in breaches:
            if event.scope != "cluster" or event.scope_key is None:
                continue
            if event.observed_value is None or event.threshold_value is None:
                messages.append(event.message)
                continue
            messages.append(
                f"{event.scope_key}: {event.message} {event.observed_value:,.2f} > {event.threshold_value:,.2f}"
            )
        return messages

    def _get_peak_equity(self) -> Optional[float]:
        if self.risk_engine.mt5_client is None or not hasattr(self.risk_engine.mt5_client, "get_peak_equity"):
            return None
        peak_equity = self.risk_engine.mt5_client.get_peak_equity()
        return None if peak_equity is None else float(peak_equity)

    def _extract_peak_equity_from_state(self, state: PortfolioState) -> Optional[float]:
        peak_equity = state.metadata.get("peak_equity")
        return None if peak_equity is None else float(peak_equity)
