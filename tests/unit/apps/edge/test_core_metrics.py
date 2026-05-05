from __future__ import annotations

from pathlib import Path

import pandas as pd

from haruquant.research import build_core_metric_profile, build_default_registry
from haruquant.utils import prepare_ohlcvs_dataset
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
    idx = pd.date_range("2024-01-01", periods=12, freq="h")
    return pd.DataFrame(
        {
            "Open": [1.1000, 1.1002, 1.1003, 1.1004, 1.1001, 1.1005, 1.1008, 1.1010, 1.1012, 1.1011, 1.1014, 1.1016],
            "High": [1.1004, 1.1005, 1.1007, 1.1008, 1.1006, 1.1009, 1.1011, 1.1014, 1.1015, 1.1016, 1.1018, 1.1020],
            "Low": [1.0998, 1.1000, 1.1001, 1.1002, 1.0999, 1.1003, 1.1006, 1.1008, 1.1010, 1.1009, 1.1012, 1.1014],
            "Close": [1.1002, 1.1003, 1.1004, 1.1003, 1.1005, 1.1008, 1.1010, 1.1012, 1.1011, 1.1014, 1.1016, 1.1018],
            "Volume": [10, 11, 13, 9, 8, 14, 15, 12, 10, 16, 17, 20],
            "Spread": [8, 9, 8, 10, 11, 8, 7, 9, 10, 8, 7, 8],
        },
        index=idx,
    )


def test_core_metric_registry_exposes_expected_families():
    registry = build_default_registry()

    assert registry.families() == [
        "candles",
        "ranges",
        "returns",
        "roc",
        "spread",
        "volatility",
        "volume_activity",
    ]


def test_core_metric_profile_builds_normalized_values():
    prepared = prepare_ohlcvs_dataset(
        DummySource(_sample_df()),
        symbol="EURUSD",
        timeframe="H1",
        start_pos=0,
        end_pos=20,
        exclude_last_bar=False,
    )

    profile = build_core_metric_profile(
        prepared,
        symbol="EURUSD",
        timeframe="H1",
        data_source="dukascopy",
        range_by="bars",
        number_of_bars=20,
    )

    assert profile.summary["is_valid"] is True
    assert profile.summary["family_count"] == 7
    assert any(value.family == "returns" and value.key == "total_return" for value in profile.values)
    assert any(value.family == "spread" and value.key == "mean_pips" for value in profile.values)
    assert any(value.family == "volume_activity" and value.key == "mean" for value in profile.values)


def test_core_metric_profile_persists_normalized_values():
    db_path = Path(".tmp_core_metric_test.db")
    if db_path.exists():
        db_path.unlink()
    db = SQLiteDatabase(db_path=str(db_path))
    assert db.initialize_database()

    prepared = prepare_ohlcvs_dataset(
        DummySource(_sample_df()),
        symbol="EURUSD",
        timeframe="H1",
        start_pos=0,
        end_pos=20,
        exclude_last_bar=False,
    )
    profile = build_core_metric_profile(
        prepared,
        symbol="EURUSD",
        timeframe="H1",
        data_source="dukascopy",
        range_by="bars",
        number_of_bars=20,
    )

    run_id = db.save_core_metric_profile(profile, user_id=1)
    assert run_id is not None

    runs = db.get_core_metric_runs(symbol="EURUSD")
    assert len(runs) == 1
    assert runs[0]["symbol"] == "EURUSD"

    stored = db.get_core_metric_run(run_id)
    assert stored is not None
    assert stored["summary"]["metric_count"] == profile.summary["metric_count"]
    assert any(value["family"] == "returns" for value in stored["values"])
    if db_path.exists():
        db_path.unlink()
