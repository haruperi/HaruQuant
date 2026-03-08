"""Risk Budget Allocator module."""

from __future__ import annotations

from typing import Dict, List, Optional

import numpy as np

from .governor import RiskGovernor
from .regime import RegimeState
from .risk_limits import CorrelationPreference


class RiskBudgetAllocator:
    """Planner that computes target lots using RC budgeting (risk parity style)."""

    def __init__(
        self, governor: RiskGovernor, corr_pref: Optional[CorrelationPreference] = None
    ):
        """Initialize allocator with governor and preferences."""
        self.gov = governor
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
        """Compute target lots for each symbol using risk parity."""
        data = self.gov._get_data(symbols, exclude_current_bar=True)
        returns_df = self.gov._build_returns_df(data, symbols)
        if returns_df.empty:
            return base_lots

        eff = self.gov.effective_limits(regime)
        cov = self.gov._estimate_covariance(returns_df, symbols, eff)

        # Normalize base budgets
        if not budgets:
            budgets = dict.fromkeys(symbols, 1.0)
        b = {s: float(budgets.get(s, 0.0)) for s in symbols}
        ssum = sum(b.values())
        if ssum <= 0:
            b = {s: 1.0 / len(symbols) for s in symbols}
        else:
            b = {s: v / ssum for s, v in b.items()}

        # --- Pro move: soft correlation preference ---
        weights0 = self.gov._build_weights_from_positions(base_lots, data, symbols)
        corr_map = self.gov._portfolio_correlation_map(weights0, cov, symbols)
        b = self._apply_correlation_penalty(b, corr_map)

        # Initialize lots from base lots
        lots = {s: float(base_lots.get(s, 0.0)) for s in symbols}

        # Iteratively align RC% to budgets
        for _ in range(max_iters):
            w = self.gov._build_weights_from_positions(lots, data, symbols)
            rc_pct = self.gov._compute_risk_contributions_pct(w, cov, symbols)

            max_err = 0.0
            for s in symbols:
                err = rc_pct.get(s, 0.0) - b[s]
                max_err = max(max_err, abs(err))
                scale = float(np.exp(-lr * err))
                lots[s] *= scale

            if max_err < 0.01:
                break

        return lots

    def lots_to_deltas(
        self, current: Dict[str, float], target: Dict[str, float]
    ) -> Dict[str, float]:
        """Calculate difference between target and current lots."""
        keys = set(current) | set(target)
        return {s: float(target.get(s, 0.0) - current.get(s, 0.0)) for s in keys}

    def _apply_correlation_penalty(
        self, budgets: Dict[str, float], corr_map: Dict[str, float]
    ) -> Dict[str, float]:
        tgt = self.corr_pref.target_corr
        k = self.corr_pref.penalty_strength
        floor = self.corr_pref.min_budget_frac

        adjusted: Dict[str, float] = {}
        for s, b in budgets.items():
            c = abs(float(corr_map.get(s, 0.0)))
            if c <= tgt:
                adjusted[s] = b
            else:
                penalty = float(np.exp(-k * (c - tgt)))
                adjusted[s] = max(b * penalty, floor * b)

        ssum = sum(adjusted.values())
        if ssum > 0:
            adjusted = {s: v / ssum for s, v in adjusted.items()}
        return adjusted
