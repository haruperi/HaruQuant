from __future__ import annotations

import pandas as pd

from haruquant.risk import (
    MarginalRiskEvaluator,
    PortfolioStateEngine,
    RecommendationAction,
    RecommendationEngine,
    RiskLimits,
    RiskScorecardEngine,
    RiskSnapshotEngine,
)


def _bars(periods: int = 160, start: str = "2024-01-01", scale: float = 1.0) -> pd.DataFrame:
    idx = pd.date_range(start, periods=periods, freq="h")
    base = pd.Series(range(periods), index=idx, dtype=float)
    close = 1.10 + (base * 0.00030 * scale) + ((base % 7) * 0.00012 * scale)
    return pd.DataFrame(
        {
            "Close": close,
            "Open": close - 0.0002,
            "High": close + 0.0005,
            "Low": close - 0.0005,
            "Volume": [100 + i for i in range(periods)],
            "Spread": [1 + (i % 3) for i in range(periods)],
        },
        index=idx,
    )


def _equity_curve() -> pd.Series:
    return pd.Series(
        [10000.0, 10120.0, 10070.0, 9980.0, 9890.0, 9950.0, 10010.0],
        index=pd.date_range("2024-01-01", periods=7, freq="h"),
        dtype=float,
    )


def _build_state():
    return PortfolioStateEngine().build_state(
        account={
            "equity": 10000.0,
            "balance": 10000.0,
            "free_margin": 8400.0,
            "margin_used": 1600.0,
            "currency": "USD",
        },
        positions=[
            {"symbol": "EURUSD", "volume": 0.35, "type": "BUY"},
            {"symbol": "GBPUSD", "volume": 0.12, "type": "BUY"},
            {"symbol": "USDJPY", "volume": 0.08, "type": "SELL"},
        ],
        symbol_specs={
            "EURUSD": {"trade_contract_size": 100000, "lots_step": 0.01, "volume_min": 0.01},
            "GBPUSD": {"trade_contract_size": 100000, "lots_step": 0.01, "volume_min": 0.01},
            "USDJPY": {"trade_contract_size": 100000, "lots_step": 0.01, "volume_min": 0.01},
            "XAUUSD": {"trade_contract_size": 100, "lots_step": 0.01, "volume_min": 0.01},
        },
        market_data={
            "EURUSD": _bars(scale=1.0),
            "GBPUSD": _bars(scale=1.1),
            "USDJPY": _bars(scale=0.9),
            "XAUUSD": _bars(scale=2.4),
        },
        limits=RiskLimits(var_cap_frac=0.08, es_cap_frac=0.12, vol_lookback=20, corr_lookback=40),
        symbol_to_cluster={
            "EURUSD": "FOREX",
            "GBPUSD": "FOREX",
            "USDJPY": "FOREX",
            "XAUUSD": "METALS",
        },
        timeframe="H1",
        as_of="2024-01-06T15:00:00",
        metadata={"equity_curve": _equity_curve()},
    )


def test_marginal_reduction_scores_better_than_adding_more_risk():
    state = _build_state()
    snapshot = RiskSnapshotEngine().build_snapshot(state)
    scorecard = RiskScorecardEngine().build_scorecard(snapshot)
    evaluator = MarginalRiskEvaluator()

    reduce_action = RecommendationAction(
        action_type="reduce",
        symbol="EURUSD",
        delta_lots=-0.10,
        current_lots=0.35,
        projected_lots=0.25,
        rationale="Test concentrated exposure reduction.",
    )
    add_action = RecommendationAction(
        action_type="resize",
        symbol="EURUSD",
        delta_lots=0.10,
        current_lots=0.35,
        projected_lots=0.45,
        rationale="Test concentrated exposure increase.",
    )

    reduced = evaluator.evaluate_action(state, reduce_action, snapshot=snapshot, scorecard=scorecard)
    added = evaluator.evaluate_action(state, add_action, snapshot=snapshot, scorecard=scorecard)

    assert reduced.recommendation_score.usefulness_score > added.recommendation_score.usefulness_score


def test_large_risk_addition_is_marked_infeasible():
    state = _build_state()
    snapshot = RiskSnapshotEngine().build_snapshot(state)
    scorecard = RiskScorecardEngine().build_scorecard(snapshot)
    evaluator = MarginalRiskEvaluator()

    action = RecommendationAction(
        action_type="add",
        symbol="XAUUSD",
        delta_lots=5.0,
        current_lots=0.0,
        projected_lots=5.0,
        rationale="Force a large infeasible position.",
    )
    result = evaluator.evaluate_action(state, action, snapshot=snapshot, scorecard=scorecard)

    assert result.governance_feasible is False
    assert result.governance_report is not None
    assert result.governance_report.decision == "REJECT"


def test_recommendation_engine_builds_ranked_batch():
    state = _build_state()
    engine = RecommendationEngine()

    batch = engine.build_recommendations(
        state,
        candidate_symbols=["XAUUSD"],
        hedge_symbols=["XAUUSD", "USDJPY"],
        max_recommendations=8,
    )

    assert batch.summary["recommendation_count"] > 0
    assert len(batch.recommendations) == batch.summary["recommendation_count"]
    assert batch.summary["feasible_count"] >= 0
    assert batch.summary["top_action_type"] is not None
    assert any(item.explanation for item in batch.recommendations)
    assert any(item.governance_feasible for item in batch.recommendations)
    scores = [item.recommendation_score.usefulness_score for item in batch.recommendations]
    assert scores == sorted(scores, reverse=True)
