from __future__ import annotations

from backend_retiring.api.routes.edge import _run_edge_lab_symbol_profile_sync


def test_automation_runner_builds_completed_snapshot(isolated_edge_lab_env):
    result = _run_edge_lab_symbol_profile_sync(
        symbol="TRENDUSD",
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
        trigger_type="integration",
        run_reason="completed_snapshot",
        user_id=1,
    )

    assert result["status"] == "completed"
    assert result["snapshot_saved"] is True
    assert result["snapshot"] is not None
    assert result["scorecard_summary"]["final_score"] is not None
    assert result["market_structure_summary"]["verdict"] in {"TREND_BIASED", "REVERSION_BIASED", "MIXED"}
    assert result["unsupervised_summary"]["status"] in {"COMPLETED", "SKIPPED"}
    assert result["automation_metadata"]["stage_timings"]["dataset_prepare_seconds"] >= 0.0
    assert result["automation_metadata"]["stage_timings"]["total_seconds"] >= 0.0
    assert result["snapshot"]["dataset_meta"]["dataset_fingerprint"]
    assert result["snapshot"]["dataset_meta"]["config_fingerprint"]
    assert "unsupervised_summary" in result["snapshot"]
    assert result["snapshot"]["scorecard_summary"]["readiness_label"] in {
        "RESEARCH_READY",
        "USE_WITH_CAUTION",
        "INSUFFICIENT_SAMPLE",
    }


def test_automation_runner_uses_cache_for_matching_full_rerun(isolated_edge_lab_env):
    first = _run_edge_lab_symbol_profile_sync(
        symbol="TRENDUSD",
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
        trigger_type="integration",
        run_reason="seed_cache",
        user_id=1,
    )
    second = _run_edge_lab_symbol_profile_sync(
        symbol="TRENDUSD",
        timeframe="H1",
        data_source="dukascopy",
        range_by="bars",
        start_date=None,
        end_date=None,
        number_of_bars=240,
        metric_families=None,
        save_snapshot=True,
        use_cache=True,
        force_rerun=False,
        trigger_type="integration",
        run_reason="cache_lookup",
        user_id=1,
    )

    assert first["snapshot"]["snapshot_id"] is not None
    assert second["status"] == "cached"
    assert second["snapshot"]["snapshot_id"] == first["snapshot"]["snapshot_id"]
    assert second["automation_metadata"]["cache_hit"] is True
    assert second["automation_metadata"]["stage_timings"]["cache_lookup_seconds"] >= 0.0


def test_automation_runner_supports_partial_recompute_metadata(isolated_edge_lab_env):
    _run_edge_lab_symbol_profile_sync(
        symbol="RANGEUSD",
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
        trigger_type="integration",
        run_reason="seed_partial",
        user_id=1,
    )
    partial = _run_edge_lab_symbol_profile_sync(
        symbol="RANGEUSD",
        timeframe="H1",
        data_source="dukascopy",
        range_by="bars",
        start_date=None,
        end_date=None,
        number_of_bars=240,
        metric_families=["market_structure"],
        save_snapshot=True,
        use_cache=False,
        force_rerun=False,
        trigger_type="integration",
        run_reason="partial_recompute",
        user_id=1,
    )

    assert partial["status"] == "completed"
    assert partial["snapshot_saved"] is False
    assert partial["automation_metadata"]["partial_snapshot"] is True
    assert "core_metric" in partial["automation_metadata"]["recomputed_families"]
    assert "seasonality" in partial["automation_metadata"]["recomputed_families"]
    assert "market_structure" in partial["automation_metadata"]["recomputed_families"]
    assert partial["automation_metadata"]["reused_families"] == ["unsupervised_structure", "scorecard"]


def test_automation_runner_supports_unsupervised_only_family(isolated_edge_lab_env):
    _run_edge_lab_symbol_profile_sync(
        symbol="RANGEUSD",
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
        trigger_type="integration",
        run_reason="seed_unsupervised_only",
        user_id=1,
    )
    result = _run_edge_lab_symbol_profile_sync(
        symbol="RANGEUSD",
        timeframe="H1",
        data_source="dukascopy",
        range_by="bars",
        start_date=None,
        end_date=None,
        number_of_bars=240,
        metric_families=["unsupervised_structure"],
        save_snapshot=True,
        use_cache=False,
        force_rerun=False,
        trigger_type="integration",
        run_reason="unsupervised_only",
        user_id=1,
    )

    assert result["status"] == "completed"
    assert result["snapshot_saved"] is False
    assert result["automation_metadata"]["partial_snapshot"] is True
    assert result["automation_metadata"]["recomputed_families"] == ["core_metric", "unsupervised_structure"]
    assert result["automation_metadata"]["reused_families"] == ["seasonality", "market_structure", "scorecard"]
    assert result["unsupervised_summary"]["status"] in {"COMPLETED", "SKIPPED"}
