from __future__ import annotations

import json
from pathlib import Path

from backend.api.routes.edge import _run_edge_lab_symbol_profile_sync


def _full_run(symbol: str):
    return _run_edge_lab_symbol_profile_sync(
        symbol=symbol,
        timeframe="H1",
        data_source="dukascopy",
        range_by="bars",
        start_date=None,
        end_date=None,
        number_of_bars=240,
        metric_families=None,
        save_snapshot=True,
        use_cache=False,
        force_rerun=True,
        trigger_type="audit",
        run_reason="audit_run",
        user_id=1,
    )


def test_reproducibility_of_full_profile_runs(isolated_edge_lab_env):
    first = _full_run("TRENDUSD")
    second = _full_run("TRENDUSD")

    assert first["scorecard_summary"]["final_score"] == second["scorecard_summary"]["final_score"]
    assert first["market_structure_summary"]["verdict"] == second["market_structure_summary"]["verdict"]
    assert first["scorecard_summary"]["final_label"] == second["scorecard_summary"]["final_label"]


def test_snapshot_comparison_detects_different_pair_profiles(isolated_edge_lab_env):
    db = isolated_edge_lab_env["db"]
    left = _full_run("TRENDUSD")
    right = _full_run("SPREADUSD")

    comparison = db.compare_profile_snapshots(
        left["snapshot"]["snapshot_id"],
        right["snapshot"]["snapshot_id"],
    )

    assert comparison is not None
    assert len(comparison["score_diffs"]) > 0
    assert len(comparison["metric_diffs"]) > 0


def test_report_exports_stay_consistent_with_snapshot_summary(isolated_edge_lab_env, tmp_path):
    db = isolated_edge_lab_env["db"]
    result = _full_run("RANGEUSD")
    snapshot_id = result["snapshot"]["snapshot_id"]

    exported = db.export_profile_snapshot_reports(snapshot_id)
    assert exported is not None
    json_artifact = next(item for item in exported["artifacts"] if item["artifact_type"] == "json_report")
    payload = json.loads(Path(json_artifact["artifact_ref"]).read_text(encoding="utf-8"))

    assert payload["summary"]["final_score"] == result["scorecard_summary"]["final_score"]
    assert payload["summary"]["market_verdict"] == result["market_structure_summary"]["verdict"]
    assert payload["summary"]["score_spec_version"] == result["snapshot"]["scorecard_summary"]["score_spec_version"]
    assert payload["summary"]["readiness_label"] == result["snapshot"]["scorecard_summary"]["readiness_label"]
