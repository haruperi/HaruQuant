"""Rebalance recommendation helpers built on the shared RC rebalance math."""

from __future__ import annotations

from typing import Dict, List, Optional

from services.risk.metrics import RiskSnapshot
from services.risk.models import PortfolioState
from services.risk.scoring import RiskScorecard

from .marginal_risk import MarginalRiskEvaluator, build_state_risk_engine
from .models import RecommendationAction, RecommendationResult


class RebalanceSuggestionEngine:
    """Generate explainable rebalance suggestions from RC budgeting."""

    def generate(
        self,
        state: PortfolioState,
        snapshot: RiskSnapshot,
        scorecard: RiskScorecard,
        evaluator: MarginalRiskEvaluator,
        target_rc_budget: Optional[Dict[str, float]] = None,
        max_items: int = 3,
    ) -> List[RecommendationResult]:
        if state.limits is None or len(state.position_map) < 2:
            return []
        target = target_rc_budget or {
            symbol: 1.0 / len(state.position_map) for symbol in state.position_map.keys()
        }
        deltas = build_state_risk_engine(state).propose_rc_rebalance(
            positions=state.position_map,
            target_rc_budget=target,
            limits=state.limits,
        )
        results: List[RecommendationResult] = []
        for symbol, delta in deltas.items():
            current_lots = float(state.position_map.get(symbol, 0.0))
            action = RecommendationAction(
                action_type="rebalance",
                symbol=symbol,
                delta_lots=float(delta),
                current_lots=current_lots,
                projected_lots=current_lots + float(delta),
                rationale="Shift the portfolio closer to the target risk-contribution budget.",
                context={"target_rc_budget": target},
            )
            results.append(evaluator.evaluate_action(state, action, snapshot=snapshot, scorecard=scorecard))
        results.sort(key=lambda item: item.recommendation_score.usefulness_score, reverse=True)
        return results[:max_items]
