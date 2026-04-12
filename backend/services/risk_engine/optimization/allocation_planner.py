"""Soft RC-budget allocation planner built on shared portfolio math."""

from __future__ import annotations

from typing import Dict, List, Optional

import numpy as np

from backend.services.risk_engine.core import GovernanceEngine
from backend.services.risk_engine.limits import CorrelationPreference
from backend.services.risk_engine.regimes import RegimeState


class AllocationPlanner:
    """Compute target lots using risk-contribution budgeting."""

    def __init__(
        self,
        risk_source: GovernanceEngine,
        corr_pref: Optional[CorrelationPreference] = None,
    ):
        self.risk_source = risk_source
        self.corr_pref = corr_pref or CorrelationPreference()

    def compute_target_lots(
        self,
        symbols: List[str],
        base_lots: Dict[str, float],
        budgets: Optional[Dict[str, float]] = None,
        regime: Optional[RegimeState] = None,
        max_iters: int = 50,
        lr: float = 0.25,
    ) -> Dict[str, float]:
        math_source = self._math_source()
        data = math_source.get_data(symbols, exclude_current_bar=True)
        returns_df = math_source.build_returns_df(data, symbols)
        if returns_df.empty:
            return base_lots

        eff = self.risk_source.effective_limits(regime)
        cov = math_source.estimate_covariance(returns_df, symbols, eff)

        if not budgets:
            budgets = dict.fromkeys(symbols, 1.0)
        normalized = {symbol: float(budgets.get(symbol, 0.0)) for symbol in symbols}
        total_budget = sum(normalized.values())
        if total_budget <= 0:
            normalized = {symbol: 1.0 / len(symbols) for symbol in symbols}
        else:
            normalized = {
                symbol: value / total_budget for symbol, value in normalized.items()
            }

        weights0 = math_source.build_weights_from_positions(base_lots, data, symbols)
        corr_map = math_source.portfolio_correlation_map(weights0, cov, symbols)
        normalized = self._apply_correlation_penalty(normalized, corr_map)

        lots = {symbol: float(base_lots.get(symbol, 0.0)) for symbol in symbols}
        for _ in range(max_iters):
            weights = math_source.build_weights_from_positions(lots, data, symbols)
            rc_pct = math_source.compute_risk_contributions_pct(weights, cov, symbols)

            max_err = 0.0
            for symbol in symbols:
                err = rc_pct.get(symbol, 0.0) - normalized[symbol]
                max_err = max(max_err, abs(err))
                scale = float(np.exp(-lr * err))
                lots[symbol] *= scale

            if max_err < 0.01:
                break

        return lots

    def lots_to_deltas(
        self,
        current: Dict[str, float],
        target: Dict[str, float],
    ) -> Dict[str, float]:
        keys = set(current) | set(target)
        return {symbol: float(target.get(symbol, 0.0) - current.get(symbol, 0.0)) for symbol in keys}

    def _apply_correlation_penalty(
        self,
        budgets: Dict[str, float],
        corr_map: Dict[str, float],
    ) -> Dict[str, float]:
        target_corr = self.corr_pref.target_corr
        penalty_strength = self.corr_pref.penalty_strength
        floor = self.corr_pref.min_budget_frac

        adjusted: Dict[str, float] = {}
        for symbol, budget in budgets.items():
            corr = abs(float(corr_map.get(symbol, 0.0)))
            if corr <= target_corr:
                adjusted[symbol] = budget
            else:
                penalty = float(np.exp(-penalty_strength * (corr - target_corr)))
                adjusted[symbol] = max(budget * penalty, floor * budget)

        total = sum(adjusted.values())
        if total > 0:
            adjusted = {symbol: value / total for symbol, value in adjusted.items()}
        return adjusted

    def _math_source(self):
        return self.risk_source.risk_engine
