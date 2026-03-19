"""Recommendation engine built on risk snapshots, scorecards, and governance."""

from __future__ import annotations

from typing import Iterable, Optional

from apps.risk.metrics import RiskSnapshot
from apps.risk.models import PortfolioState
from apps.risk.optimization import (
    AllocationOptimizer,
    CapitalEfficiencyRanker,
    HedgeOptimizer,
    MarginalRiskEvaluator,
    RecommendationBatch,
    RebalanceSuggestionEngine,
)
from apps.risk.scoring import RiskScorecard

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
        recommendations = []
        recommendations.extend(
            self.capital_efficiency_ranker.build_reduce_candidates(
                state=state,
                snapshot=baseline_snapshot,
                scorecard=baseline_scorecard,
                evaluator=self.evaluator,
                max_items=2,
            )
        )
        recommendations.extend(
            self.allocation_optimizer.generate(
                state=state,
                snapshot=baseline_snapshot,
                scorecard=baseline_scorecard,
                evaluator=self.evaluator,
                candidate_symbols=candidate_symbols,
                max_items=5,
            )
        )
        recommendations.extend(
            self.rebalance_engine.generate(
                state=state,
                snapshot=baseline_snapshot,
                scorecard=baseline_scorecard,
                evaluator=self.evaluator,
                max_items=3,
            )
        )
        if hedge_symbols is not None:
            recommendations.extend(
                self.hedge_optimizer.generate(
                    state=state,
                    snapshot=baseline_snapshot,
                    scorecard=baseline_scorecard,
                    evaluator=self.evaluator,
                    hedge_symbols=hedge_symbols,
                    max_items=3,
                )
            )

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
        summary = self._build_summary(baseline_snapshot, baseline_scorecard, ranked)
        return RecommendationBatch(
            snapshot=baseline_snapshot,
            scorecard=baseline_scorecard,
            recommendations=ranked,
            summary=summary,
        )

    def _build_summary(self, snapshot: RiskSnapshot, scorecard: RiskScorecard, recommendations) -> dict:
        best = recommendations[0] if recommendations else None
        return {
            "as_of": snapshot.summary.get("as_of"),
            "recommendation_count": len(recommendations),
            "feasible_count": sum(1 for item in recommendations if item.governance_feasible),
            "baseline_overall_score": scorecard.summary.get("overall_risk_quality_score"),
            "top_action_type": None if best is None else best.action.action_type,
            "top_action_symbol": None if best is None else best.action.symbol,
            "top_usefulness_score": None if best is None else best.recommendation_score.usefulness_score,
        }
