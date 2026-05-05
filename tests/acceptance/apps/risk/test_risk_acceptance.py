from __future__ import annotations

from services.risk import (
    HypotheticalOrderAction,
    RecommendationEngine,
    RiskScorecardEngine,
    RiskSnapshotEngine,
    WhatIfEngine,
)
from services.risk.simulation import ReplayFrame
from tests.fixtures.risk_portfolios import build_risk_portfolio_cases


def test_balanced_portfolio_scores_better_than_fragile_portfolio():
    cases = build_risk_portfolio_cases()
    balanced = cases["balanced"].state
    fragile = cases["high_leverage_fragile"].state

    balanced_snapshot = RiskSnapshotEngine().build_snapshot(balanced)
    fragile_snapshot = RiskSnapshotEngine().build_snapshot(fragile)
    balanced_score = RiskScorecardEngine().build_scorecard(balanced_snapshot)
    fragile_score = RiskScorecardEngine().build_scorecard(fragile_snapshot)

    assert balanced_score.summary["overall_risk_quality_score"] > fragile_score.summary["overall_risk_quality_score"]


def test_concentrated_portfolio_triggers_concentration_or_governance_pressure():
    cases = build_risk_portfolio_cases()
    concentrated = cases["concentrated_single_currency"].state
    snapshot = RiskSnapshotEngine().build_snapshot(concentrated)
    scorecard = RiskScorecardEngine().build_scorecard(snapshot)

    assert snapshot.summary["max_single_exposure_frac"] > 0.5
    assert scorecard.summary["concentration_score"] < 70.0 or snapshot.summary["compliance_state"] != "ok"


def test_margin_stressed_portfolio_has_low_margin_safety():
    cases = build_risk_portfolio_cases()
    balanced = cases["balanced"].state
    stressed = cases["margin_stressed"].state

    balanced_score = RiskScorecardEngine().build_scorecard(RiskSnapshotEngine().build_snapshot(balanced))
    stressed_snapshot = RiskSnapshotEngine().build_snapshot(stressed)
    stressed_score = RiskScorecardEngine().build_scorecard(stressed_snapshot)

    assert stressed_snapshot.summary["margin_used_frac"] > balanced_score.snapshot.summary["margin_used_frac"]
    assert stressed_score.summary["margin_safety_score"] < balanced_score.summary["margin_safety_score"]


def test_volatility_and_correlation_stress_cases_get_worse_structural_signals():
    cases = build_risk_portfolio_cases()
    balanced = RiskSnapshotEngine().build_snapshot(cases["balanced"].state)
    vol_expansion = RiskSnapshotEngine().build_snapshot(cases["volatility_expansion"].state)
    high_corr = RiskSnapshotEngine().build_snapshot(cases["high_correlation_clustered"].state)

    assert vol_expansion.summary["worst_scenario_loss"] > balanced.summary["worst_scenario_loss"]
    assert high_corr.summary["average_pair_correlation"] >= balanced.summary["average_pair_correlation"]


def test_replay_with_hypothetical_action_insertion_produces_stable_delta():
    cases = build_risk_portfolio_cases()
    state = cases["high_leverage_fragile"].state
    snapshot = RiskSnapshotEngine().build_snapshot(state)
    scorecard = RiskScorecardEngine().build_scorecard(snapshot)
    recommendations = RecommendationEngine().build_recommendations(
        state,
        snapshot=snapshot,
        scorecard=scorecard,
        candidate_symbols=["USDJPY"],
        hedge_symbols=["USDJPY"],
        max_recommendations=3,
    )
    frame = ReplayFrame(
        frame_index=0,
        timestamp=snapshot.summary["as_of"],
        capture_timestamp=snapshot.summary["as_of"],
        state=state,
        snapshot=snapshot,
        scorecard=scorecard,
        recommendations=recommendations,
        cockpit_state=None,
        context={"mode": "acceptance"},
    )
    comparison = WhatIfEngine().evaluate(
        frame,
        actions=[HypotheticalOrderAction(action_type="reduce", symbol="XAUUSD", delta_lots=0.10)],
        include_recommendations=True,
        candidate_symbols=["USDJPY"],
        hedge_symbols=["USDJPY"],
        max_recommendations=3,
    )

    assert comparison.summary["var_delta"] <= 0.0
    assert comparison.summary["es_delta"] <= 0.0
    assert comparison.summary["overall_score_delta"] > -1e-4
