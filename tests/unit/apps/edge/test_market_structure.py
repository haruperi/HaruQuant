from __future__ import annotations

from pathlib import Path

import pandas as pd

from services.research.market_structure import build_market_structure_profile
from services.research.config import MarketStructureConfig
from services.utils.datasets import prepare_ohlcvs_dataset
from services.research.market_structure import _detect_swings
from services.research.market_structure import _weighted_group_score
from backend.data.database.sqlite import SQLiteDatabase


class DummySource:
    def __init__(self, df: pd.DataFrame):
        self._df = df

    def fetch_data(
        self,
        symbol: str,
        timeframe: str,
        start_pos: int,
        end_pos: int,
    ) -> pd.DataFrame:
        return self._df.copy()


def _sample_df() -> pd.DataFrame:
    idx = pd.date_range("2024-01-01", periods=32, freq="h")
    base = [
        1.1000, 1.1010, 1.1020, 1.1014, 1.1028, 1.1038, 1.1030, 1.1042,
        1.1055, 1.1047, 1.1061, 1.1072, 1.1064, 1.1078, 1.1090, 1.1081,
        1.1095, 1.1108, 1.1099, 1.1112, 1.1124, 1.1115, 1.1128, 1.1140,
        1.1132, 1.1146, 1.1158, 1.1149, 1.1162, 1.1174, 1.1166, 1.1180,
    ]
    open_prices = [base[0]] + base[:-1]
    high = [price + 0.0006 for price in base]
    low = [price - 0.0006 for price in base]
    return pd.DataFrame(
        {
            "Open": open_prices,
            "High": high,
            "Low": low,
            "Close": base,
            "Volume": [100 + i for i in range(len(base))],
            "Spread": [10 for _ in base],
        },
        index=idx,
    )


def _same_bar_extreme_df() -> pd.DataFrame:
    idx = pd.date_range("2024-01-01", periods=7, freq="h")
    close = [1.1000, 1.1003, 1.1001, 1.1002, 1.1004, 1.1003, 1.1005]
    open_prices = [close[0]] + close[:-1]
    high = [1.1002, 1.1005, 1.1018, 1.1004, 1.1006, 1.1005, 1.1007]
    low = [1.0998, 1.1001, 1.0984, 1.1000, 1.1002, 1.1001, 1.1003]
    return pd.DataFrame(
        {
            "Open": open_prices,
            "High": high,
            "Low": low,
            "Close": close,
            "Volume": [100] * len(close),
            "Spread": [10] * len(close),
        },
        index=idx,
    )


def test_market_structure_builds_swings_legs_and_scores():
    prepared = prepare_ohlcvs_dataset(
        DummySource(_sample_df()),
        symbol="EURUSD",
        timeframe="H1",
        start_pos=0,
        end_pos=40,
        exclude_last_bar=False,
    )

    profile = build_market_structure_profile(
        prepared,
        symbol="EURUSD",
        timeframe="H1",
        data_source="dukascopy",
        range_by="bars",
        number_of_bars=40,
        config=MarketStructureConfig(swing_window=1, min_swing_atr=0.1, eds_boot_n=50, eds_perm_n=50),
    )

    assert profile.summary["trend_leg_count"] > 0
    assert profile.summary["swing_count"] > 0
    assert profile.summary["verdict"] in {
        "TREND_BIASED",
        "REVERSION_BIASED",
        "MIXED",
    }
    assert any(point.label in {"HH", "HL", "LH", "LL"} for point in profile.swing_points)
    assert any(row.key == "chain_strength" for row in profile.score_rows)
    assert any(row.group == "confidence" for row in profile.score_rows)
    assert any(row.group == "reversion" for row in profile.score_rows)
    assert any(row.group == "chop" for row in profile.score_rows)
    follow_through_row = next(row for row in profile.score_rows if row.key == "follow_through_probability")
    assert float(follow_through_row.raw_value) > 0
    assert "direction_score" in profile.summary
    assert "trend_confidence_score" in profile.summary
    assert "reversion_confidence_score" in profile.summary
    assert "decision_confidence_score" in profile.summary
    assert "trend_bias_score" in profile.summary
    assert "reversion_bias_score" in profile.summary
    assert "chop_score" in profile.summary
    assert "eds1_expectancy_r" in profile.summary
    assert "false_break_frequency" in profile.summary
    assert "distribution" in profile.summary
    assert "breakout_analysis" in profile.summary
    assert "excursions" in profile.summary
    assert "phase6_commentary" in profile.summary
    assert "regime_map" in profile.summary
    assert "regime_share" in profile.summary
    assert "regime_durations" in profile.summary
    assert "regime_transition_matrix" in profile.summary
    assert "regime_conditioned_metrics" in profile.summary
    assert "regime_score_inputs" in profile.summary
    assert "calibration_metadata" in profile.summary
    assert profile.summary["calibration_metadata"]["profile_overrides"]
    assert profile.summary["model_version"] == "market_structure_baseline_v1"
    assert profile.summary["baseline_id"] == "ms_baseline_2026_03_17"
    assert profile.summary["regime_state"] in {"STABLE", "TRANSITIONAL"}
    assert "tail_metrics" in profile.summary["distribution"]
    assert "percentile_tables" in profile.summary["distribution"]
    assert "normality" in profile.summary["distribution"]
    assert "asymmetry" in profile.summary["distribution"]
    assert "retest_success_rate" in profile.summary["breakout_analysis"]
    assert "retracement_depth_distribution" in profile.summary["breakout_analysis"]
    assert "extension_behavior" in profile.summary["breakout_analysis"]
    assert "breakout" in profile.summary["excursions"]
    assert "pullback_resumption" in profile.summary["excursions"]
    assert profile.summary["phase6_commentary"]["breakout_quality"] in {"HIGH", "MEDIUM", "LOW"}
    assert len(profile.summary["regime_map"]) == profile.bar_count
    trend_share_total = sum(profile.summary["regime_share"]["trend"].values())
    assert abs(trend_share_total - 1.0) < 1e-9
    assert "trend" in profile.summary["regime_transition_matrix"]
    assert isinstance(profile.summary["regime_conditioned_metrics"]["trend"], list)
    assert "trend_share" in profile.summary["regime_score_inputs"]
    assert any(value.key == "final_score" for value in profile.values)
    assert any(value.key == "distribution_left_tail_p01" for value in profile.values)
    assert any(value.key == "breakout_avg_mfe_pips" for value in profile.values)
    assert any(value.key.startswith("regime_share_trend_") for value in profile.values)

    reversion_score = max(0.0, min(100.0, _weighted_group_score(profile.score_rows, "reversion")))
    chop_score = max(0.0, min(100.0, _weighted_group_score(profile.score_rows, "chop")))
    expected_reversion_bias = min(
        100.0,
        ((reversion_score * 0.75 + chop_score * 0.25) / (0.75 + 0.25))
        * (profile.summary["reversion_confidence_score"] / 100.0),
    )
    assert profile.summary["reversion_bias_score"] == expected_reversion_bias


def test_market_structure_skips_same_bar_dual_extremes():
    prepared = prepare_ohlcvs_dataset(
        DummySource(_same_bar_extreme_df()),
        symbol="EURUSD",
        timeframe="H1",
        start_pos=0,
        end_pos=10,
        exclude_last_bar=False,
    )

    swings = _detect_swings(
        prepared.data,
        symbol="EURUSD",
        cfg=MarketStructureConfig(swing_window=1, min_swing_atr=0.1),
        high_col=prepared.schema.high,
        low_col=prepared.schema.low,
        close_col=prepared.schema.close,
    )

    target_time = prepared.data.index[2].isoformat()
    assert not any(point.timestamp == target_time for point in swings)


def test_market_structure_profile_persists():
    db_path = Path(".tmp_market_structure_test.db")
    if db_path.exists():
        db_path.unlink()
    db = SQLiteDatabase(db_path=str(db_path))
    assert db.initialize_database()

    prepared = prepare_ohlcvs_dataset(
        DummySource(_sample_df()),
        symbol="EURUSD",
        timeframe="H1",
        start_pos=0,
        end_pos=40,
        exclude_last_bar=False,
    )
    profile = build_market_structure_profile(
        prepared,
        symbol="EURUSD",
        timeframe="H1",
        data_source="dukascopy",
        range_by="bars",
        number_of_bars=40,
        config=MarketStructureConfig(swing_window=1, min_swing_atr=0.1, eds_boot_n=50, eds_perm_n=50),
    )

    run_id = db.save_market_structure_profile(profile, user_id=1)
    assert run_id is not None

    runs = db.get_market_structure_runs(symbol="EURUSD")
    assert len(runs) == 1
    assert runs[0]["symbol"] == "EURUSD"

    stored = db.get_market_structure_run(run_id)
    assert stored is not None
    assert stored["summary"]["verdict"] == profile.summary["verdict"]
    assert stored["calibration_metadata"]["profile_overrides"] == profile.summary["calibration_metadata"]["profile_overrides"]
    assert len(stored["score_rows"]) == len(profile.score_rows)
    assert len(stored["swing_points"]) == len(profile.swing_points)

    evaluation_row = {
        "run_id": run_id,
        "symbol": "EURUSD",
        "timeframe": "H1",
        "run_created_at": stored["created_at"],
        "predicted_verdict": stored["summary"]["verdict"],
        "realized_verdict": "TREND_BIASED",
        "matched": True,
        "decision_confidence_score": 60.0,
        "confidence_bucket": "medium",
        "forward_end": stored["created_at"],
        "net_move_pips": 30.0,
        "path_pips": 50.0,
        "efficiency": 0.6,
        "reversion_ratio": 0.2,
        "flip_rate": 0.1,
        "avg_range_pips": 12.0,
        "max_excursion_pips": 35.0,
        "continuation_label": "high",
        "range_reentry_label": "low",
        "breakout_failure_label": "low",
        "chop_label": "low",
        "calibration_metadata": stored["calibration_metadata"],
    }
    assert db.save_market_structure_evaluation(evaluation_row)
    evaluations = db.get_market_structure_evaluations(symbol="EURUSD")
    assert len(evaluations) == 1
    assert evaluations[0]["run_id"] == run_id
    if db_path.exists():
        db_path.unlink()
