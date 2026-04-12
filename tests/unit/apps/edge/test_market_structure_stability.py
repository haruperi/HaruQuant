from __future__ import annotations

import pandas as pd

from backend.services.research.config import MarketStructureConfig
from backend.services.research.data.models import CanonicalOHLCVSSchema, DataQualityReportModel, PreparedDataset
from backend.services.research.market_structure_stability import build_market_structure_stability_report


def _prepared_df(rows: int = 300) -> PreparedDataset:
    idx = pd.date_range("2024-01-01", periods=rows, freq="h")
    close = [1.1000 + (i * 0.0001) for i in range(rows)]
    frame = pd.DataFrame(
        {
            "Open": [close[0]] + close[:-1],
            "High": [value + 0.0003 for value in close],
            "Low": [value - 0.0003 for value in close],
            "Close": close,
            "Volume": [100] * rows,
            "Spread": [10] * rows,
        },
        index=idx,
    )
    report = DataQualityReportModel(metadata={"symbol": "EURUSD", "timeframe": "H1"})
    return PreparedDataset(data=frame, report=report, schema=CanonicalOHLCVSSchema())


def test_market_structure_stability_reports_insufficient_data_when_blocks_too_small():
    prepared = _prepared_df(rows=120)
    report = build_market_structure_stability_report(
        prepared,
        symbol="EURUSD",
        timeframe="H1",
        data_source="dukascopy",
        range_by="bars",
        config=MarketStructureConfig(stability_block_count=3, stability_min_bars_per_block=80),
    )
    assert report["is_evaluable"] is False
    assert report["stability"] == "INSUFFICIENT_DATA"
    assert report["confidence_drift"] == 0.0


def test_market_structure_stability_reports_block_summary_when_evaluable():
    prepared = _prepared_df(rows=300)
    report = build_market_structure_stability_report(
        prepared,
        symbol="EURUSD",
        timeframe="H1",
        data_source="dukascopy",
        range_by="bars",
        config=MarketStructureConfig(
            swing_window=1,
            min_swing_atr=0.1,
            eds_boot_n=25,
            eds_perm_n=25,
            stability_block_count=3,
            stability_min_bars_per_block=50,
            stability_modes=("early_middle_late",),
        ),
    )
    assert report["is_evaluable"] is True
    assert report["evaluated_blocks"] == 3
    assert len(report["blocks"]) == 3
    assert report["stability"] in {"HIGH", "MEDIUM", "LOW"}
    assert "confidence_drift" in report
    assert len(report["modes"]) == 1
