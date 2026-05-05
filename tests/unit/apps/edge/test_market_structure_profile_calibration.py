from __future__ import annotations

from services.research.market_structure_profile_calibration import evaluate_profile_calibration


def test_profile_calibration_groups_rows_by_profile_key():
    run_rows = [
        {
            "run_id": 1,
            "symbol": "EURUSD",
            "timeframe": "H1",
            "summary": {
                "trend_bias_score": 60.0,
                "reversion_score": 20.0,
                "reversion_bias_score": 20.0,
                "trend_confidence_score": 55.0,
                "reversion_confidence_score": 40.0,
                "chop_score": 10.0,
            },
        },
        {
            "run_id": 2,
            "symbol": "XAUUSD",
            "timeframe": "M15",
            "summary": {
                "trend_bias_score": 18.0,
                "reversion_score": 55.0,
                "reversion_bias_score": 40.0,
                "trend_confidence_score": 45.0,
                "reversion_confidence_score": 60.0,
                "chop_score": 20.0,
            },
        },
    ]
    validation_rows = [
        {"run_id": 1, "realized_verdict": "TREND_BIASED"},
        {"run_id": 2, "realized_verdict": "REVERSION_BIASED"},
    ]

    report = evaluate_profile_calibration(run_rows, validation_rows)
    assert report["profile_count"] == 2
    assert any(row["profile_key"] == "major_fx::intraday_swing" for row in report["rows"])
    assert any(row["profile_key"] == "metals::intraday_fast" for row in report["rows"])
