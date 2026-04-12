from __future__ import annotations

import pandas as pd

from backend.services.research.market_structure_validation import (
    build_validation_summary,
    confidence_bucket,
    label_realized_market_behavior,
)


def test_realized_market_behavior_labels_trend_window():
    idx = pd.date_range("2024-01-01", periods=12, freq="h")
    close = [1.1000, 1.1006, 1.1010, 1.1015, 1.1020, 1.1026, 1.1030, 1.1035, 1.1040, 1.1045, 1.1048, 1.1052]
    df = pd.DataFrame(
        {
            "Close": close,
            "High": [value + 0.0002 for value in close],
            "Low": [value - 0.0002 for value in close],
        },
        index=idx,
    )
    outcome = label_realized_market_behavior(df, symbol="EURUSD")
    assert outcome["realized_verdict"] == "TREND_BIASED"
    assert outcome["continuation_label"] == "high"


def test_realized_market_behavior_labels_reversion_window():
    idx = pd.date_range("2024-01-01", periods=12, freq="h")
    close = [1.1000, 1.1020, 1.0980, 1.1015, 1.0990, 1.1008, 1.0995, 1.1005, 1.0998, 1.1002, 1.1000, 1.1001]
    df = pd.DataFrame(
        {
            "Close": close,
            "High": [value + 0.0004 for value in close],
            "Low": [value - 0.0004 for value in close],
        },
        index=idx,
    )
    outcome = label_realized_market_behavior(df, symbol="EURUSD")
    assert outcome["realized_verdict"] == "REVERSION_BIASED"
    assert outcome["range_reentry_label"] == "high"
    assert outcome["breakout_failure_label"] == "high"


def test_validation_summary_groups_accuracy_by_confidence_bucket():
    rows = [
        {"symbol": "EURUSD", "timeframe": "H1", "predicted_verdict": "TREND_BIASED", "realized_verdict": "TREND_BIASED", "matched": True, "confidence_bucket": "high"},
        {"symbol": "EURUSD", "timeframe": "H1", "predicted_verdict": "TREND_BIASED", "realized_verdict": "MIXED", "matched": False, "confidence_bucket": "high"},
        {"symbol": "XAUUSD", "timeframe": "M15", "predicted_verdict": "REVERSION_BIASED", "realized_verdict": "REVERSION_BIASED", "matched": True, "confidence_bucket": "medium"},
    ]
    summary = build_validation_summary(rows)
    assert summary["evaluated_runs"] == 3
    assert summary["matched_runs"] == 2
    assert summary["by_confidence_bucket"]["high"]["total"] == 2
    assert summary["by_predicted_verdict"]["TREND_BIASED"]["trend_hits"] == 1
    assert summary["by_symbol"]["EURUSD"]["total"] == 2
    assert summary["by_timeframe"]["H1"]["total"] == 2
    assert summary["by_realized_verdict"]["TREND_BIASED"]["correct"] == 1


def test_confidence_bucket_maps_expected_ranges():
    assert confidence_bucket(80) == "high"
    assert confidence_bucket(50) == "medium"
    assert confidence_bucket(20) == "low"
