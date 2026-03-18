from __future__ import annotations

from apps.edge.market_structure_calibration import (
    build_calibration_grid,
    classify_with_candidate,
    evaluate_calibration_candidates,
)


def test_calibration_grid_builds_candidates():
    grid = build_calibration_grid()
    assert len(grid) > 0
    assert all(abs((row.reversion_score_weight + row.chop_score_weight) - 1.0) < 1e-9 for row in grid)


def test_classify_with_candidate_respects_gap_and_confidence():
    candidate = build_calibration_grid()[0]
    verdict = classify_with_candidate(
        trend_bias_score=60.0,
        reversion_bias_score=20.0,
        trend_confidence_score=50.0,
        reversion_confidence_score=50.0,
        candidate=candidate,
    )
    assert verdict == "TREND_BIASED"


def test_calibration_ranking_returns_best_candidate_summary():
    run_rows = [
        {
            "run_id": 1,
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

    report = evaluate_calibration_candidates(run_rows, validation_rows)
    assert report["total_candidates"] > 0
    assert report["best"] is not None
    assert report["rows"]
    assert report["rows"][0]["accuracy"] >= report["rows"][-1]["accuracy"]
