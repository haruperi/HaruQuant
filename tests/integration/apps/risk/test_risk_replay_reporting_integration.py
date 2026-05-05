from __future__ import annotations

from haruquant.risk import (
    HypotheticalOrderAction,
    RecommendationEngine,
    RiskScorecardEngine,
    RiskSnapshotEngine,
    WhatIfEngine,
)
from haruquant.risk import build_replay_report
from haruquant.risk import ReplayFrame, build_cockpit_state
from haruquant.risk import RiskRepository, RiskSnapshotStore
from backend.data.database.sqlite import SQLiteDatabase
from tests.fixtures.risk_portfolios import build_risk_portfolio_cases


def test_replay_storage_and_reporting_stays_consistent(tmp_path):
    cases = build_risk_portfolio_cases()
    state = cases["high_correlation_clustered"].state

    snapshot = RiskSnapshotEngine().build_snapshot(state)
    scorecard = RiskScorecardEngine().build_scorecard(snapshot)
    recommendations = RecommendationEngine().build_recommendations(
        state,
        snapshot=snapshot,
        scorecard=scorecard,
        candidate_symbols=["XAUUSD"],
        hedge_symbols=["USDJPY"],
        max_recommendations=3,
    )
    baseline = ReplayFrame(
        frame_index=0,
        timestamp=snapshot.summary["as_of"],
        capture_timestamp=snapshot.summary["as_of"],
        state=state,
        snapshot=snapshot,
        scorecard=scorecard,
        recommendations=recommendations,
        cockpit_state=None,
        context={"mode": "integration-test"},
    )
    baseline = ReplayFrame(
        frame_index=baseline.frame_index,
        timestamp=baseline.timestamp,
        capture_timestamp=baseline.capture_timestamp,
        state=baseline.state,
        snapshot=baseline.snapshot,
        scorecard=baseline.scorecard,
        recommendations=baseline.recommendations,
        cockpit_state=build_cockpit_state(baseline),
        context=baseline.context,
    )

    what_if = WhatIfEngine().evaluate(
        baseline,
        actions=[HypotheticalOrderAction(action_type="reduce", symbol="EURUSD", delta_lots=0.08)],
        include_recommendations=True,
        candidate_symbols=["XAUUSD"],
        hedge_symbols=["USDJPY"],
        max_recommendations=3,
    )

    db = SQLiteDatabase(db_path=str(tmp_path / "risk_replay_pipeline.db"))
    assert db.initialize_database()
    store = RiskSnapshotStore(RiskRepository(db))
    run_id = store.create_run(label="phase12-replay", source="integration-test")
    snapshot_id = store.store_snapshot_bundle(run_id=run_id, snapshot=snapshot, scorecard=scorecard)
    store.store_replay_frame(run_id=run_id, frame=baseline, snapshot_id=snapshot_id, what_if=what_if)

    replay_frames = store.load_replay_frames(run_id)
    replay_report = build_replay_report(replay_frames, run=store.load_run(run_id))

    assert baseline.state.position_map["EURUSD"] == state.position_map["EURUSD"]
    assert what_if.projected_state.position_map["EURUSD"] < baseline.state.position_map["EURUSD"]
    assert replay_report["frame_count"] == 1
    assert replay_report["summary"]["what_if_available"] is True
    assert replay_frames[0]["what_if_summary_json"]["var_delta"] is not None
