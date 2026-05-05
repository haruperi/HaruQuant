from __future__ import annotations

import pandas as pd

from haruquant.research import MarketStructureConfig
from haruquant.research import CanonicalOHLCVSSchema, DataQualityReportModel, PreparedDataset
from haruquant.research import build_market_structure_robustness_report


def _prepared_df(rows: int = 200) -> PreparedDataset:
    idx = pd.date_range("2024-01-01", periods=rows, freq="h")
    close = [1.1000 + (i * 0.00008) for i in range(rows)]
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


def test_market_structure_robustness_reports_variants_and_summary():
    prepared = _prepared_df()
    report = build_market_structure_robustness_report(
        prepared,
        symbol="EURUSD",
        timeframe="H1",
        data_source="dukascopy",
        range_by="bars",
        config=MarketStructureConfig(
            swing_window=3,
            min_swing_atr=0.5,
            eds_boot_n=25,
            eds_perm_n=25,
            robustness_swing_windows=(2, 3),
            robustness_min_swing_atrs=(0.3, 0.5),
            robustness_range_windows=(15, 20),
            robustness_breakout_horizons=(3, 5),
        ),
    )
    assert report["variant_count"] == 16
    assert len(report["variants"]) == 16
    assert report["robustness"] in {"HIGH", "MEDIUM", "LOW"}
    assert 0.0 <= report["verdict_agreement_rate"] <= 1.0
    assert "range_window" in report["variants"][0]
    assert "breakout_horizon" in report["variants"][0]
