from __future__ import annotations

from haruquant.research import (
    build_metric_calibration_grid,
    evaluate_metric_calibration_candidates,
)


def test_metric_calibration_grid_builds_candidates():
    grid = build_metric_calibration_grid()
    assert len(grid) > 0
    assert hasattr(grid[0], "pullback_depth_lo")
    assert hasattr(grid[0], "false_break_lo")


def test_metric_calibration_returns_ranked_snapshot():
    run_rows = [
        {
            "run_id": 1,
            "summary": {},
            "score_rows": [
                {"group": "direction", "key": "swing_bias_balance", "raw_value": 12.0, "score": 70.0, "weight": 0.18, "contribution": 12.6},
                {"group": "direction", "key": "chain_strength", "raw_value": 4.2, "score": 80.0, "weight": 0.18, "contribution": 14.4},
                {"group": "direction", "key": "follow_through_probability", "raw_value": 0.7, "score": 60.0, "weight": 0.16, "contribution": 9.6},
                {"group": "direction", "key": "pullback_quality", "raw_value": {"depth": 0.5}, "score": 55.0, "weight": 0.20, "contribution": 11.0},
                {"group": "direction", "key": "directional_efficiency", "raw_value": {"efficiency_ratio": 0.8}, "score": 65.0, "weight": 0.16, "contribution": 10.4},
                {"group": "confidence", "key": "sample_quality", "raw_value": {"swing_points": 60}, "score": 75.0, "weight": 0.30, "contribution": 22.5},
                {"group": "confidence", "key": "structural_cleanliness", "raw_value": {"broken_trends": 2}, "score": 70.0, "weight": 0.30, "contribution": 21.0},
                {"group": "confidence", "key": "directional_asymmetry", "raw_value": 0.75, "score": 70.0, "weight": 0.15, "contribution": 10.5},
                {"group": "confidence", "key": "eds2_confirmation", "raw_value": {"confirmed": True}, "score": 65.0, "weight": 0.25, "contribution": 16.25},
                {"group": "reversion", "key": "range_state_detection", "raw_value": {"range_state_rate": 0.2}, "score": 20.0, "weight": 0.22, "contribution": 4.4},
                {"group": "reversion", "key": "false_break_reentry", "raw_value": {"false_break_frequency": 0.1, "reentry_probability": 0.2}, "score": 15.0, "weight": 0.20, "contribution": 3.0},
                {"group": "reversion", "key": "mean_reversion_metrics", "raw_value": {"half_life_bars": 18.0, "zscore_reentry_rate": 0.2, "band_reentry_rate": 0.25}, "score": 30.0, "weight": 0.28, "contribution": 8.4},
                {"group": "reversion", "key": "eds1_confirmation", "raw_value": {"confirmed": False}, "score": 10.0, "weight": 0.15, "contribution": 1.5},
                {"group": "chop", "key": "choppiness_whipsaw", "raw_value": {"choppiness_index": 42.0, "whipsaw_rate": 0.15, "direction_flip_rate": 0.18}, "score": 28.0, "weight": 0.15, "contribution": 4.2},
            ],
        },
        {
            "run_id": 2,
            "summary": {},
            "score_rows": [
                {"group": "direction", "key": "swing_bias_balance", "raw_value": 2.0, "score": 10.0, "weight": 0.18, "contribution": 1.8},
                {"group": "direction", "key": "chain_strength", "raw_value": 1.8, "score": 25.0, "weight": 0.18, "contribution": 4.5},
                {"group": "direction", "key": "follow_through_probability", "raw_value": 0.3, "score": 20.0, "weight": 0.16, "contribution": 3.2},
                {"group": "direction", "key": "pullback_quality", "raw_value": {"depth": 1.3}, "score": 25.0, "weight": 0.20, "contribution": 5.0},
                {"group": "direction", "key": "directional_efficiency", "raw_value": {"efficiency_ratio": 0.3}, "score": 20.0, "weight": 0.16, "contribution": 3.2},
                {"group": "confidence", "key": "sample_quality", "raw_value": {"swing_points": 55}, "score": 70.0, "weight": 0.30, "contribution": 21.0},
                {"group": "confidence", "key": "structural_cleanliness", "raw_value": {"broken_trends": 5}, "score": 45.0, "weight": 0.30, "contribution": 13.5},
                {"group": "confidence", "key": "directional_asymmetry", "raw_value": 0.35, "score": 30.0, "weight": 0.15, "contribution": 4.5},
                {"group": "confidence", "key": "eds2_confirmation", "raw_value": {"confirmed": False}, "score": 20.0, "weight": 0.25, "contribution": 5.0},
                {"group": "reversion", "key": "range_state_detection", "raw_value": {"range_state_rate": 0.7}, "score": 75.0, "weight": 0.22, "contribution": 16.5},
                {"group": "reversion", "key": "false_break_reentry", "raw_value": {"false_break_frequency": 0.6, "reentry_probability": 0.65}, "score": 62.5, "weight": 0.20, "contribution": 12.5},
                {"group": "reversion", "key": "mean_reversion_metrics", "raw_value": {"half_life_bars": 6.0, "zscore_reentry_rate": 0.65, "band_reentry_rate": 0.60}, "score": 70.0, "weight": 0.28, "contribution": 19.6},
                {"group": "reversion", "key": "eds1_confirmation", "raw_value": {"confirmed": True}, "score": 60.0, "weight": 0.15, "contribution": 9.0},
                {"group": "chop", "key": "choppiness_whipsaw", "raw_value": {"choppiness_index": 58.0, "whipsaw_rate": 0.40, "direction_flip_rate": 0.35}, "score": 60.0, "weight": 0.15, "contribution": 9.0},
            ],
        },
    ]
    validation_rows = [
        {"run_id": 1, "realized_verdict": "TREND_BIASED"},
        {"run_id": 2, "realized_verdict": "REVERSION_BIASED"},
    ]

    report = evaluate_metric_calibration_candidates(run_rows, validation_rows)
    assert report["total_candidates"] > 0
    assert report["best"] is not None
    assert report["rows"]
    assert report["rows"][0]["accuracy"] >= report["rows"][-1]["accuracy"]
