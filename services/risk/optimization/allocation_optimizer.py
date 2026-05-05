"""Small bounded allocation recommendation helpers."""

from __future__ import annotations

from typing import Iterable, List, Optional

from services.risk.metrics import RiskSnapshot
from services.risk.models import PortfolioState
from services.risk.scoring import RiskScorecard

from .capital_efficiency import CapitalEfficiencyRanker
from .marginal_risk import MarginalRiskEvaluator
from .models import RecommendationAction, RecommendationResult


class AllocationOptimizer:
    """Generate simple add, remove, and resize candidates."""

    def __init__(self, capital_efficiency_ranker: Optional[CapitalEfficiencyRanker] = None):
        self.capital_efficiency_ranker = capital_efficiency_ranker or CapitalEfficiencyRanker()

    def generate(
        self,
        state: PortfolioState,
        snapshot: RiskSnapshot,
        scorecard: RiskScorecard,
        evaluator: MarginalRiskEvaluator,
        candidate_symbols: Optional[Iterable[str]] = None,
        max_items: int = 5,
    ) -> List[RecommendationResult]:
        results: List[RecommendationResult] = []
        efficiency = self.capital_efficiency_ranker.rank(snapshot)
        if efficiency:
            worst = efficiency[0]
            symbol = str(worst["symbol"])
            current_lots = float(state.position_map.get(symbol, 0.0))
            results.append(
                evaluator.evaluate_action(
                    state,
                    RecommendationAction(
                        action_type="remove",
                        symbol=symbol,
                        delta_lots=-current_lots,
                        current_lots=current_lots,
                        projected_lots=0.0,
                        rationale="Remove the highest risk-burden position.",
                        context=worst,
                    ),
                    snapshot=snapshot,
                    scorecard=scorecard,
                )
            )
            results.append(
                evaluator.evaluate_action(
                    state,
                    RecommendationAction(
                        action_type="resize",
                        symbol=symbol,
                        delta_lots=-(current_lots * 0.25),
                        current_lots=current_lots,
                        projected_lots=current_lots * 0.75,
                        rationale="Shrink the highest risk-burden position.",
                        context=worst,
                    ),
                    snapshot=snapshot,
                    scorecard=scorecard,
                )
            )
            best_current = efficiency[-1]
            best_symbol = str(best_current["symbol"])
            best_lots = float(state.position_map.get(best_symbol, 0.0))
            results.append(
                evaluator.evaluate_action(
                    state,
                    RecommendationAction(
                        action_type="resize",
                        symbol=best_symbol,
                        delta_lots=best_lots * 0.20,
                        current_lots=best_lots,
                        projected_lots=best_lots * 1.20,
                        rationale="Resize the most capital-efficient current exposure.",
                        context=best_current,
                    ),
                    snapshot=snapshot,
                    scorecard=scorecard,
                )
            )

        current_symbols = set(state.position_map.keys())
        for symbol in candidate_symbols or []:
            if symbol in current_symbols or symbol not in state.symbols or symbol not in state.markets:
                continue
            volume_min = float(state.symbols[symbol].volume_min or 0.01)
            results.append(
                evaluator.evaluate_action(
                    state,
                    RecommendationAction(
                        action_type="add",
                        symbol=symbol,
                        delta_lots=volume_min,
                        current_lots=0.0,
                        projected_lots=volume_min,
                        rationale="Add a small candidate position to test diversification impact.",
                    ),
                    snapshot=snapshot,
                    scorecard=scorecard,
                )
            )
            if len(results) >= max_items:
                break

        results.sort(key=lambda item: item.recommendation_score.usefulness_score, reverse=True)
        return results[:max_items]
