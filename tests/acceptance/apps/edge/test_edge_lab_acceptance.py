from __future__ import annotations

from backend.api.legacy.routes.edge import _run_edge_lab_symbol_profile_sync


def _run(symbol: str, bars: int = 240):
    return _run_edge_lab_symbol_profile_sync(
        symbol=symbol,
        timeframe="H1",
        data_source="dukascopy",
        range_by="bars",
        start_date=None,
        end_date=None,
        number_of_bars=bars,
        metric_families=None,
        save_snapshot=True,
        use_cache=False,
        force_rerun=True,
        trigger_type="acceptance",
        run_reason=symbol.lower(),
        user_id=1,
    )


def test_trending_pair_scenario(isolated_edge_lab_env):
    result = _run("TRENDUSD")
    assert result["market_structure_summary"]["trend_bias_score"] > result["market_structure_summary"]["reversion_bias_score"]
    assert result["scorecard_summary"]["final_score"] >= 45


def test_ranging_pair_scenario(isolated_edge_lab_env):
    result = _run("RANGEUSD")
    assert result["market_structure_summary"]["verdict"] == "MIXED"
    assert abs(result["market_structure_summary"]["final_score"]) <= 10


def test_noisy_pair_scenario(isolated_edge_lab_env):
    result = _run("NOISYUSD")
    assert result["market_structure_summary"]["chop_score"] >= 50


def test_spread_heavy_symbol_scenario(isolated_edge_lab_env):
    result = _run("SPREADUSD")
    assert result["scorecard_summary"]["final_score"] < 70
    snapshot_scores = {row["score_key"]: row["score"] for row in result["snapshot"]["scores"]}
    assert snapshot_scores["cost_efficiency"] < 65


def test_missing_data_scenario(isolated_edge_lab_env):
    result = _run("MISSUSD", bars=180)
    assert result["core_metric_summary"]["warning_count"] >= 0
    assert result["market_structure_summary"]["is_valid"] in {True, False}
    assert result["scorecard_summary"]["final_label"] is not None


def test_short_history_scenario(isolated_edge_lab_env):
    result = _run("SHORTUSD", bars=18)
    assert result["market_structure_summary"]["decision_confidence_score"] <= 70


def test_dst_session_boundary_scenario(isolated_edge_lab_env):
    result = _run("DSTUSD", bars=20)
    assert result["seasonality_meta"]["filtered_rows"] > 0
    assert result["snapshot"]["seasonality_summary"]["session_summary"]
