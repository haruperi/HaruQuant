"""Capital-efficiency ranking helpers for the recommendation layer."""

from __future__ import annotations

from typing import Dict, List

from apps.risk.metrics import RiskSnapshot
from apps.risk.models import PortfolioState
from apps.risk.scoring import RiskScorecard

from .marginal_risk import MarginalRiskEvaluator, lookup_metric_value
from .models import RecommendationAction, RecommendationResult


class CapitalEfficiencyRanker:
    """Rank positions by risk burden relative to portfolio weight."""

    def rank(self, snapshot: RiskSnapshot) -> List[Dict[str, float]]:
        ranked: List[Dict[str, float]] = []
        for position in snapshot.state.positions:
            symbol = position.symbol
            portfolio_weight = float(
                lookup_metric_value(snapshot, "portfolio_weight", scope="symbol", scope_key=symbol) or 0.0
            )
            rc_frac = float(
                lookup_metric_value(snapshot, "risk_contribution_frac", scope="symbol", scope_key=symbol) or 0.0
            )
            gross_notional = float(
                lookup_metric_value(snapshot, "gross_notional", scope="symbol", scope_key=symbol) or 0.0
            )
            inefficiency = rc_frac / portfolio_weight if portfolio_weight > 1e-12 else 0.0
            ranked.append(
                {
                    "symbol": symbol,
                    "gross_notional": gross_notional,
                    "portfolio_weight": portfolio_weight,
                    "risk_contribution_frac": rc_frac,
                    "capital_efficiency_ratio": inefficiency,
                }
            )
        ranked.sort(key=lambda item: (item["capital_efficiency_ratio"], item["gross_notional"]), reverse=True)
        return ranked

    def build_reduce_candidates(
        self,
        state: PortfolioState,
        snapshot: RiskSnapshot,
        scorecard: RiskScorecard,
        evaluator: MarginalRiskEvaluator,
        max_items: int = 2,
        reduction_frac: float = 0.25,
    ) -> List[RecommendationResult]:
        results: List[RecommendationResult] = []
        for item in self.rank(snapshot)[:max_items]:
            symbol = str(item["symbol"])
            current_lots = float(state.position_map.get(symbol, 0.0))
            delta = -current_lots * reduction_frac
            action = RecommendationAction(
                action_type="reduce",
                symbol=symbol,
                delta_lots=delta,
                current_lots=current_lots,
                projected_lots=current_lots + delta,
                rationale="Reduce the least capital-efficient position.",
                context=item,
            )
            results.append(evaluator.evaluate_action(state, action, snapshot=snapshot, scorecard=scorecard))
        results.sort(key=lambda item: item.recommendation_score.usefulness_score, reverse=True)
        return results
