from __future__ import annotations

from pathlib import Path

from data.database.sqlite import SQLiteDatabase


def _snapshot_payload(final_score: float, breakout_score: float) -> dict:
    return {
        "dataset": {
            "request": {
                "symbol": "EURUSD",
                "timeframe": "H1",
                "data_source": "dukascopy",
                "range_by": "bars",
            },
            "meta": {
                "symbol": "EURUSD",
                "timeframe": "H1",
                "n_rows": 120,
                "start": "2024-01-01T00:00:00",
                "end": "2024-01-05T23:00:00",
                "session_basis": "dataset_index",
            },
        },
        "core_metric_profile": {
            "run_id": 11,
            "symbol": "EURUSD",
            "timeframe": "H1",
            "data_source": "dukascopy",
            "range_by": "bars",
            "summary": {
                "metric_count": 20,
                "warning_count": 0,
                "is_valid": True,
            },
            "values": [
                {
                    "family": "spread",
                    "metric_key": "mean_pips",
                    "value": 1.1,
                    "value_type": "number",
                    "context": {},
                },
                {
                    "family": "ranges",
                    "metric_key": "mean_pips",
                    "value": 14.2,
                    "value_type": "number",
                    "context": {},
                },
            ],
        },
        "seasonality_result": {
            "meta": {
                "filtered_rows": 120,
                "total_rows": 120,
            },
            "session_summary": [
                {
                    "session": "london",
                    "bars": 35,
                    "avg_range_pips": 15.0,
                    "avg_spread_pips": 1.1,
                    "avg_abs_co_pips": 7.5,
                    "avg_volume": 120.0,
                    "win_rate": 0.58,
                    "opportunity_score": 74.0,
                    "label": "Strong",
                    "high_rate": 0.42,
                    "low_rate": 0.31,
                }
            ],
            "opportunity_windows": {
                "best_sessions": [
                    {
                        "session": "london",
                        "bars": 35,
                        "avg_range_pips": 15.0,
                        "avg_spread_pips": 1.1,
                        "avg_abs_co_pips": 7.5,
                        "win_rate": 0.58,
                        "opportunity_score": 74.0,
                        "label": "Strong",
                    }
                ],
                "dead_sessions": [],
                "best_hours": [
                    {
                        "hour": 10,
                        "bars": 12,
                        "avg_range_pips": 6.0,
                        "avg_spread_pips": 1.0,
                        "avg_abs_co_pips": 3.0,
                        "win_rate": 0.57,
                        "opportunity_score": 69.0,
                        "label": "Good",
                    }
                ],
                "dead_hours": [],
            },
        },
        "market_structure_profile": {
            "run_id": 22,
            "symbol": "EURUSD",
            "timeframe": "H1",
            "data_source": "dukascopy",
            "range_by": "bars",
            "summary": {
                "final_score": final_score,
                "verdict": "TREND_BIASED",
                "trend_bias_score": 71.0,
                "reversion_bias_score": 32.0,
                "decision_confidence_score": 68.0,
                "model_version": "market_structure_baseline_v1",
                "baseline_id": "ms_baseline_2026_03_17",
                "distribution": {
                    "tail_metrics": {
                        "left_tail_p01": -12.0,
                    }
                },
                "breakout_analysis": {
                    "follow_through_probability": 0.62,
                    "retest_success_rate": 0.55,
                    "extension_behavior": {
                        "avg_extension_pips": breakout_score,
                    },
                },
                "excursions": {
                    "breakout": {
                        "avg_mfe_pips": 18.0,
                        "avg_mae_pips": 6.0,
                    }
                },
                "calibration_metadata": {
                    "profile_overrides": {
                        "profile_key": "major_fx|intraday_swing",
                    }
                },
            },
            "values": [
                {
                    "family": "summary",
                    "metric_key": "final_score",
                    "value": final_score,
                    "value_type": "number",
                    "context": {},
                }
            ],
        },
        "unsupervised_result": {
            "status": "COMPLETED",
            "summary": {
                "status": "COMPLETED",
                "model_version": "unsupervised_structure_v1",
                "feature_columns": ["return_1", "rolling_volatility", "momentum", "range_pct", "ema_spread"],
                "cluster_count": 3,
                "pca_explained_variance_ratio": [0.56, 0.24],
                "top_outperforming_cluster": {
                    "cluster_label": 2,
                    "outperformance_vs_overall": 0.0018,
                    "observations": 28,
                },
                "weakest_cluster": {
                    "cluster_label": 1,
                    "outperformance_vs_overall": -0.0011,
                    "observations": 19,
                },
                "top_risk_factors": [
                    {
                        "component": "PC1",
                        "feature": "momentum",
                        "loading": 0.78,
                        "abs_loading": 0.78,
                        "direction": "positive",
                        "explained_variance_ratio": 0.56,
                    }
                ],
            },
            "report": {
                "cluster_outperformance": [
                    {
                        "cluster_label": 2,
                        "observations": 28,
                        "mean_forward_return": 0.0024,
                        "hit_rate": 0.61,
                        "outperformance_vs_overall": 0.0018,
                    }
                ],
                "risk_factors": [
                    {
                        "component": "PC1",
                        "feature": "momentum",
                        "loading": 0.78,
                        "abs_loading": 0.78,
                        "direction": "positive",
                        "explained_variance_ratio": 0.56,
                    }
                ],
            },
            "risk_context": {
                "top_outperforming_cluster": {
                    "cluster_label": 2,
                    "outperformance_vs_overall": 0.0018,
                    "observations": 28,
                },
                "weakest_cluster": {
                    "cluster_label": 1,
                    "outperformance_vs_overall": -0.0011,
                    "observations": 19,
                },
            },
            "strategy_context": {
                "cluster_count": 3,
                "allowed_clusters": [2],
                "blocked_clusters": [1],
            },
        },
        "market_structure_stability": {
            "agreement_rate": 0.72,
            "direction_agreement_rate": 0.8,
            "final_score_std": 8.0,
        },
        "market_structure_robustness": {
            "verdict_agreement_rate": 0.69,
            "direction_agreement_rate": 0.77,
            "final_score_std": 10.0,
        },
        "scorecard_report": {
            "finalScore": final_score,
            "finalLabel": "High Opportunity" if final_score >= 70 else "Moderate Opportunity",
            "overallConfidence": "High",
            "rows": [
                {
                    "key": "trendability",
                    "label": "Trendability Score",
                    "score": 73.0,
                    "confidence": "High",
                    "explanation": "Trend stays dominant.",
                    "inputs": {
                        "trend_bias": 71.0,
                    },
                },
                {
                    "key": "breakout_quality",
                    "label": "Breakout Quality Score",
                    "score": breakout_score,
                    "confidence": "Moderate",
                    "explanation": "Breakouts keep extending.",
                    "inputs": {
                        "avg_extension": breakout_score,
                    },
                },
            ],
            "strategyFit": {
                "primary": {
                    "archetype": "Trend Breakout",
                    "fitScore": 76.0,
                    "rationale": "Trend inputs dominate.",
                    "warnings": ["False-break frequency is elevated."],
                    "antiFitConditions": [],
                    "inputs": {"trend_bias": 71.0},
                },
                "ranked": [
                    {
                        "archetype": "Trend Breakout",
                        "fitScore": 76.0,
                        "rationale": "Trend inputs dominate.",
                        "warnings": ["False-break frequency is elevated."],
                        "antiFitConditions": [],
                        "inputs": {"trend_bias": 71.0},
                    }
                ],
            },
        },
    }


def test_profile_snapshot_persists_and_compares():
    db_path = Path(".tmp_profile_snapshot_test.db")
    if db_path.exists():
        db_path.unlink()
    db = SQLiteDatabase(db_path=str(db_path))
    assert db.initialize_database()

    left_id = db.save_profile_snapshot(_snapshot_payload(72.0, 66.0), user_id=1)
    right_id = db.save_profile_snapshot(_snapshot_payload(58.0, 49.0), user_id=1)

    assert left_id is not None
    assert right_id is not None

    rows = db.get_profile_snapshots(symbol="EURUSD")
    assert len(rows) == 2

    stored = db.get_profile_snapshot(left_id)
    assert stored is not None
    assert stored["scorecard_summary"]["final_score"] == 72.0
    assert any(row["section"] == "seasonality_session" for row in stored["metrics"])
    assert any(row["section"] == "unsupervised_cluster" for row in stored["metrics"])
    assert any(row["score_key"] == "trendability" for row in stored["scores"])
    assert stored["strategy_fit"][0]["archetype"] == "Trend Breakout"
    assert stored["unsupervised_summary"]["summary"]["cluster_count"] == 3

    comparison = db.compare_profile_snapshots(left_id, right_id)
    assert comparison["left_snapshot"]["snapshot_id"] == left_id
    assert comparison["right_snapshot"]["snapshot_id"] == right_id
    assert any(diff["score_key"] == "breakout_quality" for diff in comparison["score_diffs"])

    report = db.export_profile_snapshot_reports(left_id)
    assert report is not None
    assert len(report["artifacts"]) == 2
    assert all(Path(artifact["artifact_ref"]).exists() for artifact in report["artifacts"])

    comparison_report = db.export_profile_snapshot_comparison_markdown(left_id, right_id)
    assert comparison_report is not None
    assert Path(comparison_report["artifact"]["artifact_ref"]).exists()

    artifact = db.export_profile_snapshot_metrics_parquet(left_id)
    assert artifact is not None
    assert Path(artifact["artifact_ref"]).exists()

    stored_after_export = db.get_profile_snapshot(left_id)
    assert stored_after_export is not None
    assert any(row["artifact_type"] == "parquet_wide_metrics" for row in stored_after_export["artifacts"])

    if db_path.exists():
        db_path.unlink()
