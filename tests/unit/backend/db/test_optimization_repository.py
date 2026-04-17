from __future__ import annotations

from datetime import datetime

from backend.data.database.sqlite import SQLiteDatabase


def test_optimization_repository_persists_unsupervised_run_and_result_payloads(tmp_path) -> None:
    db = SQLiteDatabase(db_path=str(tmp_path / "optimization.db"))
    assert db.initialize_database()

    backtest_id = db.create_backtest_run(
        strategy_name="EMA Cross",
        strategy_version="1.0.0",
        start_date=datetime(2025, 1, 1),
        end_date=datetime(2025, 1, 10),
        engine_type="vectorised",
        data_resolution="H1",
        config_hash="cfg-001",
        symbols=["EURUSD"],
        timeframes=["H1"],
    )
    optimization_id = db.create_optimization_run(
        strategy_name="EMA Cross",
        strategy_version="1.0.0",
        optimization_type="parameter",
        optimization_method="grid",
        start_date=datetime(2025, 1, 1),
        end_date=datetime(2025, 1, 10),
        parameter_space={"fast_period": [20, 30]},
        objective_function="sharpe",
        symbols=["EURUSD"],
        timeframes=["H1"],
        unsupervised_config={"enabled": True, "n_clusters": 3},
    )

    assert db.update_optimization_status(
        optimization_id,
        "running",
        unsupervised_status="completed",
        unsupervised_report={"status": "COMPLETED", "feature_columns": ["return_1"]},
        unsupervised_context={"strategy_context": {"allowed_clusters": [1]}, "risk_context": {"regime_name": "FAVORABLE"}},
    )
    saved_results = db.save_optimization_results(
        optimization_id,
        [
            {
                "backtest_id": backtest_id,
                "parameters": {"fast_period": 20},
                "score": 1.2,
                "rank": 1,
                "total_trades": 10,
                "win_rate": 0.6,
                "profit_factor": 1.5,
                "sharpe_ratio": 1.2,
                "max_drawdown": 0.08,
                "is_best": True,
                "is_top_10": True,
                "unsupervised_report": {"status": "COMPLETED", "strategy_context": {"allowed_clusters": [1]}},
            }
        ],
    )

    run = db.get_optimization_run(optimization_id)
    results = db.get_optimization_results(optimization_id)
    report = db.get_optimization_unsupervised_report(optimization_id)

    assert saved_results == 1
    assert run is not None
    assert run["unsupervised_config"]["enabled"] is True
    assert run["unsupervised_status"] == "completed"
    assert run["unsupervised_context"]["risk_context"]["regime_name"] == "FAVORABLE"
    assert results[0]["unsupervised_report"]["strategy_context"]["allowed_clusters"] == [1]
    assert report is not None
    assert report["report"]["feature_columns"] == ["return_1"]
