import pandas as pd

from apps.edge.data.enrichment import EnrichmentConfig, enrich_dataset
from apps.edge.data.models import CanonicalOHLCVSSchema


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
