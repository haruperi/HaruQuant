"""Simple hedge candidate evaluation helpers."""

from __future__ import annotations

from typing import Iterable, List

from backend.services.risk_engine.metrics import RiskSnapshot
from backend.services.risk_engine.models import PortfolioState
from backend.services.risk_engine.scoring import RiskScorecard

from .marginal_risk import MarginalRiskEvaluator
from .models import RecommendationAction, RecommendationResult


class HedgeOptimizer:
    """Evaluate a small hedge shortlist by testing both trade directions."""

    def generate(
        self,
        state: PortfolioState,
        snapshot: RiskSnapshot,
        scorecard: RiskScorecard,
        evaluator: MarginalRiskEvaluator,
        hedge_symbols: Iterable[str],
        max_items: int = 2,
    ) -> List[RecommendationResult]:
        results: List[RecommendationResult] = []
        for symbol in hedge_symbols:
            if symbol not in state.symbols or symbol not in state.markets:
                continue
            base_size = float(state.symbols[symbol].volume_min or 0.01)
            candidates = []
            for signed_delta in (base_size, -base_size):
                current_lots = float(state.position_map.get(symbol, 0.0))
                candidates.append(
                    evaluator.evaluate_action(
                        state,
                        RecommendationAction(
                            action_type="hedge",
                            symbol=symbol,
                            delta_lots=signed_delta,
                            current_lots=current_lots,
                            projected_lots=current_lots + signed_delta,
                            rationale="Test a small hedge candidate in both directions.",
                            context={"hedge_size": base_size},
                        ),
                        snapshot=snapshot,
                        scorecard=scorecard,
                    )
                )
            if candidates:
                results.append(
                    max(candidates, key=lambda item: item.recommendation_score.usefulness_score)
                )
        results.sort(key=lambda item: item.recommendation_score.usefulness_score, reverse=True)
        return results[:max_items]
