"""Orchestration engine for the Phase 2 core risk metric MVP."""

from __future__ import annotations

from typing import Any, Dict, Optional

from apps.risk.limits import GovernanceState, LimitEvent
from apps.risk.metrics import MetricContext, RiskSnapshot
from apps.risk.metrics.registry import MetricRegistry, build_default_metric_registry
from apps.risk.models import PortfolioState
from .governance_engine import GovernanceEngine
from .portfolio_risk_engine import PortfolioRiskEngine


class RiskSnapshotEngine:
    """Build one current-state normalized risk snapshot from PortfolioState."""

    def __init__(self, registry: Optional[MetricRegistry] = None):
        self.registry = registry or build_default_metric_registry()

    def build_snapshot(
        self,
        state: PortfolioState,
        shared: Optional[Dict[str, Any]] = None,
    ) -> RiskSnapshot:
        """Compute all registered metrics and return a normalized snapshot."""
        context = MetricContext(state=state, shared=dict(shared or {}))
        rows = self.registry.compute_all(context)
        governance_state, policy_events = self._build_governance(state)
        summary = self._build_summary(state, rows, governance_state)
        return RiskSnapshot(
            state=state,
            metric_rows=rows,
            summary=summary,
            governance_state=governance_state,
            policy_events=policy_events,
        )

    def _build_summary(
        self,
        state: PortfolioState,
        rows,
        governance_state: Optional[GovernanceState],
    ) -> Dict[str, Any]:
        summary: Dict[str, Any] = {
            "as_of": state.as_of,
            "active_symbols": state.active_symbols,
            "has_validation_errors": state.validation_summary.has_errors,
            "has_validation_warnings": state.validation_summary.has_warnings,
            "metric_count": len(rows),
        }
        if governance_state is not None:
            summary["compliance_state"] = governance_state.status
            summary["governance_decision"] = governance_state.decision
            summary["governance_reason"] = governance_state.reason
            summary["governance_warnings_count"] = governance_state.warnings_count
            summary["governance_breaches_count"] = governance_state.breaches_count
        for row in rows:
            if row.scope != "portfolio":
                continue
            if row.metric_key in {
                "gross_exposure",
                "net_exposure",
                "portfolio_var",
                "portfolio_es",
                "gross_exposure_to_equity",
                "gross_leverage",
                "margin_used",
                "margin_used_frac",
                "portfolio_realized_volatility",
                "portfolio_vol_shock_loss_estimate",
                "average_pair_correlation",
                "max_pair_correlation",
                "hidden_overlap_score",
                "effective_independent_bets",
                "diversification_ratio",
                "current_drawdown",
                "max_drawdown",
                "portfolio_var_parametric",
                "portfolio_cvar_parametric",
                "worst_scenario_loss",
            }:
                summary[row.metric_key] = row.numeric_value
            if row.metric_key in {"worst_scenario_name"}:
                summary[row.metric_key] = row.text_value
        return summary

    def _build_governance(
        self,
        state: PortfolioState,
    ) -> tuple[Optional[GovernanceState], list[LimitEvent]]:
        if state.limits is None:
            return None, []

        governance_engine = GovernanceEngine(
            risk_engine=PortfolioRiskEngine(
                mt5_client=_PortfolioStateRiskAdapter(state),
                timeframe=str(state.metadata.get("timeframe", "H1")),
                start_pos=0,
                end_pos=max(max((market.row_count for market in state.markets.values()), default=0), 1),
            ),
            limits=state.limits,
        )
        report = governance_engine.evaluate_portfolio_state(
            state=state,
        )
        return report.governance_state, list(report.policy_events or [])


class _PortfolioStateRiskAdapter:
    """Minimal governor adapter backed by canonical portfolio state."""

    def __init__(self, state: PortfolioState):
        self._state = state

    def get_account_equity(self):
        return float(self._state.account.equity)

    def get_peak_equity(self):
        peak_equity = self._state.metadata.get("peak_equity")
        if peak_equity is None:
            return None
        return float(peak_equity)

    def get_symbol_info(self, symbol):
        spec = self._state.symbols[symbol]
        return {
            "trade_contract_size": spec.contract_size,
            "trade_tick_value": spec.tick_value,
            "trade_tick_size": spec.tick_size,
        }

    def get_margin_required(self, symbol, lots):
        if self._state.account.margin_used is None:
            return None
        gross_lots = sum(abs(float(position.lots)) for position in self._state.positions)
        if gross_lots <= 0:
            return 0.0
        return abs(float(self._state.account.margin_used)) * (abs(float(lots)) / gross_lots)

    def get_bars(self, symbol, timeframe, count=100, start_pos=0):
        market = self._state.markets.get(symbol)
        if market is None:
            return None
        bars = market.bars.copy()
        if "Close" in bars.columns and "close" not in bars.columns:
            bars = bars.rename(columns={"Close": "close"})
        if start_pos > 0:
            bars = bars.iloc[start_pos:]
        if count is not None and count > 0:
            bars = bars.tail(int(count))
        return bars
