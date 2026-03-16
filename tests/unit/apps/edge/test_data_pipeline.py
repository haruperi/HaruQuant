from __future__ import annotations

import pandas as pd

from apps.edge.data.cleaning import CleaningConfig
from apps.edge.data.enrichment import EnrichmentConfig
from apps.edge.datasets import prepare_ohlcvs_dataset


class DummySource:
    def __init__(self, df: pd.DataFrame):
        self._df = df

    def fetch_data(self, symbol: str, timeframe: str, start_pos: int, end_pos: int) -> pd.DataFrame:
        return self._df.copy()


def test_prepare_ohlcvs_dataset_enriches_and_reports_warnings():
    idx = pd.to_datetime(
        [
            "2024-01-01 00:00:00",
            "2024-01-01 00:01:00",
            "2024-01-01 00:03:00",
        ]
    )
    df = pd.DataFrame(
        {
            "open": [1.1000, 1.1002, 1.1004],
            "high": [1.1005, 1.1006, 1.1009],
            "low": [1.0998, 1.1000, 1.1001],
            "close": [1.1002, 1.1004, 1.1007],
        },
        index=idx,
    )

    prepared = prepare_ohlcvs_dataset(
        DummySource(df),
        symbol="EURUSD",
        timeframe="M1",
        start_pos=0,
        end_pos=10,
        exclude_last_bar=False,
        cleaning=CleaningConfig(timeframe="M1", missing_bar_policy="ffill_close"),
        enrichment=EnrichmentConfig(symbol="EURUSD"),
    )

    assert prepared.report.is_valid
    assert len(prepared.report.warnings) >= 1
    assert "returns" in prepared.data.columns
    assert "log_returns" in prepared.data.columns
    assert "session" in prepared.data.columns
    assert "body_pips" in prepared.data.columns
    assert len(prepared.data) == 4


def test_prepare_ohlcvs_dataset_flags_fatal_ohlc_errors():
    idx = pd.to_datetime(["2024-01-01 00:00:00", "2024-01-01 00:01:00"])
    df = pd.DataFrame(
        {
            "Open": [1.1000, 1.1002],
            "High": [1.0990, 1.1004],
            "Low": [1.1001, 1.1000],
            "Close": [1.1000, 1.1003],
            "Volume": [10, 11],
            "Spread": [1, 1],
        },
        index=idx,
    )

    prepared = prepare_ohlcvs_dataset(
        DummySource(df),
        symbol="EURUSD",
        timeframe="M1",
        start_pos=0,
        end_pos=10,
        exclude_last_bar=False,
    )

    assert not prepared.report.is_valid
    assert len(prepared.report.fatal_errors) >= 1
