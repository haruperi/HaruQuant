from __future__ import annotations

from haruquant.risk import RecommendationEngine, RiskScorecardEngine, RiskSnapshotEngine
from haruquant.risk import build_risk_snapshot_report, build_scenario_report
from haruquant.risk import RiskRepository, RiskSnapshotStore
from backend.data.database.sqlite import SQLiteDatabase
from tests.fixtures.risk_portfolios import build_risk_portfolio_cases


def test_complete_risk_pipeline_from_state_to_report(tmp_path):
    cases = build_risk_portfolio_cases()
    state = cases["balanced"].state

    snapshot = RiskSnapshotEngine().build_snapshot(state)
    scorecard = RiskScorecardEngine().build_scorecard(snapshot)
    recommendations = RecommendationEngine().build_recommendations(
        state,
        snapshot=snapshot,
        scorecard=scorecard,
        candidate_symbols=["XAUUSD"],
        hedge_symbols=["USDJPY", "XAUUSD"],
        max_recommendations=5,
    )

    db = SQLiteDatabase(db_path=str(tmp_path / "risk_pipeline.db"))
    assert db.initialize_database()
    store = RiskSnapshotStore(RiskRepository(db))
    run_id = store.create_run(label="phase12-integration", source="integration-test")
    snapshot_id = store.store_snapshot_bundle(
        run_id=run_id,
        snapshot=snapshot,
        scorecard=scorecard,
        recommendations=recommendations,
    )

    bundle = store.load_snapshot_bundle(snapshot_id)
    run = store.load_run(run_id)
    risk_report = build_risk_snapshot_report(bundle, run=run)
    scenario_report = build_scenario_report(bundle, run=run)

    assert bundle["snapshot"]["run_id"] == run_id
    assert len(bundle["metric_rows"]) == len(snapshot.metric_rows)
    assert len(bundle["score_rows"]) == len(scorecard.score_rows)
    assert len(bundle["recommendations"]) == len(recommendations.recommendations)
    assert risk_report["snapshot_header"]["snapshot_id"] == snapshot_id
    assert risk_report["scorecard"]["summary"]["score_count"] > 0
    assert scenario_report["scenario_count"] > 0
