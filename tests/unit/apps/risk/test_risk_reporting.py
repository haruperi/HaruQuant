from __future__ import annotations

from pathlib import Path

from backend.services.risk_engine.reports import (
    build_replay_report,
    build_risk_snapshot_report,
    build_scenario_report,
    render_replay_report_markdown,
    render_risk_report_markdown,
    render_scenario_report_markdown,
)
from backend.services.risk_engine.storage import RiskRepository, RiskSnapshotStore
from backend.db.sqlite import SQLiteDatabase
from tests.unit.apps.risk.test_risk_storage import _build_state
from backend.services.risk_engine import RecommendationEngine, RiskScorecardEngine, RiskSnapshotEngine
from backend.services.risk_engine.simulation import ReplayFrame, build_cockpit_state


def _stored_bundle(tmp_path: Path):
    db = SQLiteDatabase(db_path=str(tmp_path / "risk_reporting.db"))
    assert db.initialize_database()

    state = _build_state()
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

    store = RiskSnapshotStore(RiskRepository(db))
    run_id = store.create_run(label="phase11-reporting", source="unit-test")
    snapshot_id = store.store_snapshot_bundle(
        run_id=run_id,
        snapshot=snapshot,
        scorecard=scorecard,
        recommendations=recommendations,
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
        context={"mode": "unit-test"},
    )
    store.store_replay_frame(
        run_id=run_id,
        frame=ReplayFrame(
            frame_index=frame.frame_index,
            timestamp=frame.timestamp,
            capture_timestamp=frame.capture_timestamp,
            state=frame.state,
            snapshot=frame.snapshot,
            scorecard=frame.scorecard,
            recommendations=frame.recommendations,
            cockpit_state=build_cockpit_state(frame),
            context=frame.context,
        ),
        snapshot_id=snapshot_id,
    )
    return db, store, run_id, snapshot_id


def test_build_risk_and_scenario_reports_from_stored_snapshot(tmp_path):
    _, store, run_id, snapshot_id = _stored_bundle(tmp_path)
    bundle = store.load_snapshot_bundle(snapshot_id)
    run = store.load_run(run_id)

    risk_report = build_risk_snapshot_report(bundle, run=run)
    scenario_report = build_scenario_report(bundle, run=run)

    assert risk_report["snapshot_header"]["snapshot_id"] == snapshot_id
    assert risk_report["portfolio_summary"]["portfolio_var"] is not None
    assert risk_report["scorecard"]["summary"]["score_count"] > 0
    assert scenario_report["snapshot_id"] == snapshot_id
    assert scenario_report["scenario_count"] > 0


def test_markdown_renderers_include_expected_sections(tmp_path):
    _, store, run_id, snapshot_id = _stored_bundle(tmp_path)
    bundle = store.load_snapshot_bundle(snapshot_id)
    run = store.load_run(run_id)
    replay_frames = store.load_replay_frames(run_id)

    risk_md = render_risk_report_markdown(build_risk_snapshot_report(bundle, run=run))
    scenario_md = render_scenario_report_markdown(build_scenario_report(bundle, run=run))
    replay_md = render_replay_report_markdown(build_replay_report(replay_frames, run=run))

    assert "# Risk Snapshot Report" in risk_md
    assert "## Scorecard" in risk_md
    assert "# Scenario Report" in scenario_md
    assert "# Replay Report" in replay_md


def test_export_helpers_write_report_files(tmp_path):
    db, store, run_id, snapshot_id = _stored_bundle(tmp_path)

    snapshot_exports = store.export_snapshot_reports(snapshot_id)
    replay_exports = store.export_replay_report(run_id)

    for artifact in snapshot_exports["artifacts"] + replay_exports["artifacts"]:
        assert Path(artifact["artifact_ref"]).exists()

    assert snapshot_exports["risk_report"]["snapshot_header"]["snapshot_id"] == snapshot_id
    assert replay_exports["replay_report"]["frame_count"] == 1
