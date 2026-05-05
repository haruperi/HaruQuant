import pandas as pd

from haruquant.utils import prepare_ohlcvs_dataset, tag_sessions
from haruquant.research import EnrichmentConfig, enrich_dataset
from haruquant.research import CanonicalOHLCVSSchema


def test_enrich_dataset_builds_fixed_session_labels_with_overlaps():
    index = pd.to_datetime(
        [
            "2024-01-01 01:00:00",
            "2024-01-01 03:00:00",
            "2024-01-01 15:00:00",
            "2024-01-01 23:00:00",
        ]
    )
    frame = pd.DataFrame(
        {
            "Open": [1.0, 1.0, 1.0, 1.0],
            "High": [1.1, 1.1, 1.1, 1.1],
            "Low": [0.9, 0.9, 0.9, 0.9],
            "Close": [1.0, 1.0, 1.0, 1.0],
            "Volume": [1, 1, 1, 1],
            "Spread": [1, 1, 1, 1],
        },
        index=index,
    )

    enriched = enrich_dataset(
        frame,
        schema=CanonicalOHLCVSSchema(),
        config=EnrichmentConfig(
            symbol="EURUSD",
            session_basis="dataset_index",
        ),
    )

    assert enriched["session"].tolist() == ["sydney", "sydney_tokyo", "london_ny", "gap"]
    assert enriched["is_overlap"].tolist() == [False, True, True, False]
    assert enriched["is_gap"].tolist() == [False, False, False, True]
    assert enriched["session_basis"].tolist() == ["dataset_index"] * 4


class DummySource:
    def __init__(self, df: pd.DataFrame):
        self._df = df

    def fetch_data(self, symbol: str, timeframe: str, start_pos: int, end_pos: int) -> pd.DataFrame:
        return self._df.copy()


def test_prepare_dataset_reports_shared_session_hours():
    index = pd.date_range("2024-01-01", periods=8, freq="h")
    frame = pd.DataFrame(
        {
            "Open": [1.0] * 8,
            "High": [1.1] * 8,
            "Low": [0.9] * 8,
            "Close": [1.0] * 8,
            "Volume": [1] * 8,
            "Spread": [1] * 8,
        },
        index=index,
    )

    prepared = prepare_ohlcvs_dataset(
        DummySource(frame),
        symbol="EURUSD",
        timeframe="H1",
        start_pos=0,
        end_pos=8,
        exclude_last_bar=False,
    )

    assert prepared.report.metadata["session_hours"] == {
        "sydney": list(range(0, 7)),
        "tokyo": list(range(2, 9)),
        "london": list(range(10, 17)),
        "ny": list(range(15, 22)),
    }


def test_tag_sessions_uses_shared_edge_session_labels_by_default():
    index = pd.to_datetime(
        [
            "2024-01-01 01:00:00",
            "2024-01-01 03:00:00",
            "2024-01-01 15:00:00",
            "2024-01-01 23:00:00",
        ]
    )
    frame = pd.DataFrame({"Close": [1.0, 1.0, 1.0, 1.0]}, index=index)

    tagged = tag_sessions(frame)

    assert tagged["session"].tolist() == ["sydney", "sydney_tokyo", "london_ny", "gap"]
