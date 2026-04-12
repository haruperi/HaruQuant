"""Recommendation engine built on risk snapshots, scorecards, and governance."""

from __future__ import annotations

from typing import Iterable, Optional

from backend.services.risk_engine.metrics import RiskSnapshot
from backend.services.risk_engine.models import PortfolioState
from backend.services.risk_engine.optimization import (
    AllocationOptimizer,
    CapitalEfficiencyRanker,
    HedgeOptimizer,
    MarginalRiskEvaluator,
    RecommendationBatch,
    RebalanceSuggestionEngine,
)
from backend.services.risk_engine.scoring import RiskScorecard

from .risk_scorecard_engine import RiskScorecardEngine
from .risk_snapshot_engine import RiskSnapshotEngine


class RecommendationEngine:
    """Build a ranked recommendation batch from the current portfolio state."""

    def __init__(
        self,
        snapshot_engine: Optional[RiskSnapshotEngine] = None,
        scorecard_engine: Optional[RiskScorecardEngine] = None,
        evaluator: Optional[MarginalRiskEvaluator] = None,
        allocation_optimizer: Optional[AllocationOptimizer] = None,
        hedge_optimizer: Optional[HedgeOptimizer] = None,
        rebalance_engine: Optional[RebalanceSuggestionEngine] = None,
        capital_efficiency_ranker: Optional[CapitalEfficiencyRanker] = None,
    ):
        self.snapshot_engine = snapshot_engine or RiskSnapshotEngine()
        self.scorecard_engine = scorecard_engine or RiskScorecardEngine()
        self.evaluator = evaluator or MarginalRiskEvaluator(
            snapshot_engine=self.snapshot_engine,
            scorecard_engine=self.scorecard_engine,
        )
        self.capital_efficiency_ranker = capital_efficiency_ranker or CapitalEfficiencyRanker()
        self.allocation_optimizer = allocation_optimizer or AllocationOptimizer(
            capital_efficiency_ranker=self.capital_efficiency_ranker
        )
        self.hedge_optimizer = hedge_optimizer or HedgeOptimizer()
        self.rebalance_engine = rebalance_engine or RebalanceSuggestionEngine()

    def build_recommendations(
        self,
        state: PortfolioState,
        snapshot: Optional[RiskSnapshot] = None,
        scorecard: Optional[RiskScorecard] = None,
        candidate_symbols: Optional[Iterable[str]] = None,
        hedge_symbols: Optional[Iterable[str]] = None,
        max_recommendations: int = 10,
    ) -> RecommendationBatch:
        """Build one ranked recommendation batch for the supplied portfolio state."""
        baseline_snapshot = snapshot or self.snapshot_engine.build_snapshot(state)
        baseline_scorecard = scorecard or self.scorecard_engine.build_scorecard(baseline_snapshot)
        reduce_candidates = self.capital_efficiency_ranker.build_reduce_candidates(
            state=state,
            snapshot=baseline_snapshot,
            scorecard=baseline_scorecard,
            evaluator=self.evaluator,
            max_items=2,
        )
        allocation_candidates = self.allocation_optimizer.generate(
            state=state,
            snapshot=baseline_snapshot,
            scorecard=baseline_scorecard,
            evaluator=self.evaluator,
            candidate_symbols=candidate_symbols,
            max_items=5,
        )
        rebalance_candidates = self.rebalance_engine.generate(
            state=state,
            snapshot=baseline_snapshot,
            scorecard=baseline_scorecard,
            evaluator=self.evaluator,
            max_items=3,
        )
        hedge_candidates = []
        if hedge_symbols is not None:
            hedge_candidates = self.hedge_optimizer.generate(
                state=state,
                snapshot=baseline_snapshot,
                scorecard=baseline_scorecard,
                evaluator=self.evaluator,
                hedge_symbols=hedge_symbols,
                max_items=3,
            )
        recommendations = [
            *reduce_candidates,
            *allocation_candidates,
            *rebalance_candidates,
            *hedge_candidates,
        ]
        capital_efficiency = self.capital_efficiency_ranker.rank(baseline_snapshot)

        unique = {}
        for item in recommendations:
            key = (
                item.action.action_type,
                item.action.symbol,
                round(float(item.action.delta_lots), 8),
            )
            existing = unique.get(key)
            if existing is None or item.recommendation_score.usefulness_score > existing.recommendation_score.usefulness_score:
                unique[key] = item

        ranked = sorted(
            unique.values(),
            key=lambda item: (
                item.recommendation_score.usefulness_score,
                1 if item.governance_feasible else 0,
                -abs(item.action.delta_lots),
            ),
            reverse=True,
        )[:max_recommendations]
        summary = self._build_summary(
            baseline_snapshot,
            baseline_scorecard,
            ranked,
            reduce_candidates=reduce_candidates,
            allocation_candidates=allocation_candidates,
            hedge_candidates=hedge_candidates,
            rebalance_candidates=rebalance_candidates,
            capital_efficiency=capital_efficiency,
        )
        return RecommendationBatch(
            snapshot=baseline_snapshot,
            scorecard=baseline_scorecard,
            recommendations=ranked,
            summary=summary,
        )

    def _build_summary(
        self,
        snapshot: RiskSnapshot,
        scorecard: RiskScorecard,
        recommendations,
        *,
        reduce_candidates=None,
        allocation_candidates=None,
        hedge_candidates=None,
        rebalance_candidates=None,
        capital_efficiency=None,
    ) -> dict:
        best = recommendations[0] if recommendations else None
        return {
            "as_of": snapshot.summary.get("as_of"),
            "recommendation_count": len(recommendations),
            "feasible_count": sum(1 for item in recommendations if item.governance_feasible),
            "baseline_overall_score": scorecard.summary.get("overall_risk_quality_score"),
            "top_action_type": None if best is None else best.action.action_type,
            "top_action_symbol": None if best is None else best.action.symbol,
            "top_usefulness_score": None if best is None else best.recommendation_score.usefulness_score,
            "marginal_risk_recommendation": None if not reduce_candidates else reduce_candidates[0],
            "allocation_candidates": list(allocation_candidates or []),
            "hedge_candidates": list(hedge_candidates or []),
            "rebalance_candidates": list(rebalance_candidates or []),
            "capital_efficiency": list(capital_efficiency or []),
        }
