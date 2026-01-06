"""
Usage examples for apps.sqlite.optimization.py

This module demonstrates:
- OptimizationManager class for optimization operations
- Creating and managing optimization runs
- Saving optimization results
- Walk-forward analysis
- Monte Carlo simulations
"""

from apps.sqlite import SQLiteDatabase
from datetime import datetime


def example_create_optimization_run():
    """
    Example: Create a new optimization run

    Optimization runs test multiple parameter combinations
    to find the best performing configuration.
    """
    db = SQLiteDatabase(db_path="test_optimization.db")
    db.initialize_database()

    # Define parameter space to test
    parameter_space = {
        "fast_period": [5, 8, 10, 13],
        "slow_period": [20, 21, 25, 30],
        "stop_loss_atr": [1.5, 2.0, 2.5],
        "take_profit_atr": [2.0, 3.0, 4.0]
    }

    # Create optimization run
    optimization_id = db.create_optimization_run(
        strategy_name="MA Crossover",
        strategy_version="1.0.0",
        optimization_type="grid_search",
        optimization_method="exhaustive",
        start_date=datetime(2023, 1, 1),
        end_date=datetime(2023, 12, 31),
        parameter_space=parameter_space,
        objective_function="sharpe_ratio",
        symbols=["EURUSD", "GBPUSD"],
        timeframes=["H1"],
        constraints={"min_trades": 30, "max_drawdown": 20.0},
        total_combinations=192,  # 4 * 4 * 3 * 3
        n_jobs=4  # Parallel processing
    )

    print(f"Optimization run created with ID: {optimization_id}")
    print(f"  Method: grid_search")
    print(f"  Total combinations: 192")
    print(f"  Objective: sharpe_ratio")


def example_update_optimization_status():
    """
    Example: Update optimization run status and progress

    Track optimization progress:
    - Status (pending, running, completed, failed)
    - Completed combinations
    - Best parameters found so far
    """
    db = SQLiteDatabase(db_path="test_opt_status.db")
    db.initialize_database()

    # Create optimization
    opt_id = db.create_optimization_run(
        strategy_name="Test",
        strategy_version="1.0.0",
        optimization_type="grid_search",
        optimization_method="exhaustive",
        start_date=datetime(2023, 1, 1),
        end_date=datetime(2023, 12, 31),
        parameter_space={"param1": [1, 2, 3]},
        objective_function="sharpe_ratio",
        total_combinations=3
    )

    print(f"Optimization {opt_id} created")

    # Start optimization
    db.update_optimization_status(opt_id, "running")
    print("  Status: running")

    # Update progress
    db.update_optimization_status(
        opt_id,
        "running",
        completed_combinations=50,
        best_score=1.85,
        best_parameters={"param1": 2}
    )
    print("  Progress: 50/192 combinations")
    print("  Best score so far: 1.85")

    # Complete optimization
    db.update_optimization_status(
        opt_id,
        "completed",
        completed_combinations=192,
        best_backtest_id=123,
        best_score=2.15,
        best_parameters={"param1": 2, "param2": 20},
        completed_at=datetime.now()
    )
    print("  Status: completed")
    print("  Best score: 2.15")


def example_save_optimization_results():
    """
    Example: Save optimization results

    Each result represents one parameter combination's performance.
    """
    db = SQLiteDatabase(db_path="test_opt_results.db")
    db.initialize_database()

    # Create optimization
    opt_id = db.create_optimization_run(
        strategy_name="Test",
        strategy_version="1.0.0",
        optimization_type="grid_search",
        optimization_method="exhaustive",
        start_date=datetime(2023, 1, 1),
        end_date=datetime(2023, 12, 31),
        parameter_space={"fast": [5, 10], "slow": [20, 30]},
        objective_function="sharpe_ratio",
        total_combinations=4
    )

    # Simulate optimization results
    results = [
        {
            "backtest_id": 101,
            "parameters": {"fast": 5, "slow": 20},
            "score": 1.85,
            "rank": 1,
            "total_trades": 45,
            "win_rate": 0.56,
            "profit_factor": 1.8,
            "sharpe_ratio": 1.85,
            "max_drawdown": 12.5,
            "is_best": True,
            "is_top_10": True
        },
        {
            "backtest_id": 102,
            "parameters": {"fast": 10, "slow": 20},
            "score": 1.62,
            "rank": 2,
            "total_trades": 38,
            "win_rate": 0.53,
            "profit_factor": 1.6,
            "sharpe_ratio": 1.62,
            "max_drawdown": 15.2,
            "is_best": False,
            "is_top_10": True
        },
        {
            "backtest_id": 103,
            "parameters": {"fast": 5, "slow": 30},
            "score": 1.45,
            "rank": 3,
            "total_trades": 32,
            "win_rate": 0.50,
            "profit_factor": 1.4,
            "sharpe_ratio": 1.45,
            "max_drawdown": 18.0,
            "is_best": False,
            "is_top_10": True
        }
    ]

    # Save all results
    count = db.save_optimization_results(opt_id, results)
    print(f"Saved {count} optimization results")

    # Update best result
    db.update_optimization_status(
        opt_id,
        "completed",
        best_backtest_id=results[0]["backtest_id"],
        best_score=results[0]["score"],
        best_parameters=results[0]["parameters"]
    )
    print(f"Best parameters: {results[0]['parameters']}")
    print(f"Best score: {results[0]['score']}")


def example_get_optimization_results():
    """
    Example: Retrieve optimization results

    Can sort by different metrics and limit results.
    """
    db = SQLiteDatabase(db_path="test_get_results.db")
    db.initialize_database()

    # Create and populate optimization (simplified)
    opt_id = db.create_optimization_run(
        strategy_name="Test",
        strategy_version="1.0.0",
        optimization_type="grid_search",
        optimization_method="exhaustive",
        start_date=datetime(2023, 1, 1),
        end_date=datetime(2023, 12, 31),
        parameter_space={"param": [1, 2, 3]},
        objective_function="sharpe_ratio"
    )

    # Get top results by score
    top_results = db.get_optimization_results(
        opt_id,
        limit=10,
        order_by="score",
        ascending=False
    )
    print(f"Top 10 results by score: {len(top_results)}")

    # Get results by profit factor
    pf_results = db.get_optimization_results(
        opt_id,
        limit=5,
        order_by="profit_factor",
        ascending=False
    )
    print(f"Top 5 by profit factor: {len(pf_results)}")

    # Display results
    for i, result in enumerate(top_results[:3], 1):
        print(f"\nRank {i}:")
        print(f"  Parameters: {result.get('parameters', {})}")
        print(f"  Score: {result.get('score', 0)}")
        print(f"  Win Rate: {result.get('win_rate', 0) * 100:.1f}%")
        print(f"  Profit Factor: {result.get('profit_factor', 0):.2f}")


def example_walk_forward_analysis():
    """
    Example: Walk-forward analysis

    Walk-forward splits data into:
    - Training period (in-sample): Find best parameters
    - Testing period (out-of-sample): Validate on unseen data

    Multiple windows test robustness across different market conditions.
    """
    db = SQLiteDatabase(db_path="test_walk_forward.db")
    db.initialize_database()

    # Create optimization for walk-forward
    opt_id = db.create_optimization_run(
        strategy_name="WF Strategy",
        strategy_version="1.0.0",
        optimization_type="walk_forward",
        optimization_method="grid_search",
        start_date=datetime(2023, 1, 1),
        end_date=datetime(2023, 12, 31),
        parameter_space={"param": [1, 2, 3]},
        objective_function="sharpe_ratio"
    )

    # Create walk-forward windows
    windows = [
        {
            "window_number": 1,
            "train_start": datetime(2023, 1, 1),
            "train_end": datetime(2023, 4, 30),
            "test_start": datetime(2023, 5, 1),
            "test_end": datetime(2023, 6, 30),
            "best_parameters": {"param": 2},
            "train_metrics": {
                "return": 15.5,
                "sharpe": 1.8,
                "drawdown": 8.5,
                "total_trades": 25
            },
            "test_metrics": {
                "return": 12.3,
                "sharpe": 1.5,
                "drawdown": 10.2,
                "total_trades": 12
            }
        },
        {
            "window_number": 2,
            "train_start": datetime(2023, 3, 1),
            "train_end": datetime(2023, 6, 30),
            "test_start": datetime(2023, 7, 1),
            "test_end": datetime(2023, 8, 31),
            "best_parameters": {"param": 3},
            "train_metrics": {
                "return": 18.2,
                "sharpe": 2.1,
                "drawdown": 7.8,
                "total_trades": 28
            },
            "test_metrics": {
                "return": 14.8,
                "sharpe": 1.7,
                "drawdown": 9.5,
                "total_trades": 14
            }
        }
    ]

    # Save windows
    for window in windows:
        window_id = db.create_walk_forward_window(
            optimization_id=opt_id,
            window_number=window["window_number"],
            train_start=window["train_start"],
            train_end=window["train_end"],
            test_start=window["test_start"],
            test_end=window["test_end"],
            best_parameters=window["best_parameters"],
            train_metrics=window["train_metrics"],
            test_metrics=window["test_metrics"]
        )
        print(f"Window {window['window_number']} created: ID {window_id}")

    # Get summary
    summary = db.get_walk_forward_summary(opt_id)
    if summary:
        print(f"\nWalk-Forward Summary:")
        print(f"  Total windows: {summary['total_windows']}")
        print(f"  Avg train return: {summary['avg_train_return']:.2f}%")
        print(f"  Avg test return: {summary['avg_test_return']:.2f}%")
        print(f"  Consistency: {summary['consistency_score']:.1f}%")
        print(f"  Profitable windows: {summary['profitable_windows']}/{summary['total_windows']}")


def example_monte_carlo_simulation():
    """
    Example: Monte Carlo simulation

    Monte Carlo simulations randomly resample trades to estimate:
    - Distribution of possible outcomes
    - Confidence intervals
    - Probability of profit/ruin
    - Expected shortfall (worst case scenarios)
    """
    db = SQLiteDatabase(db_path="test_monte_carlo.db")
    db.initialize_database()

    # Create a backtest first
    backtest_id = db.create_backtest_run(
        strategy_name="Test",
        strategy_version="1.0.0",
        start_date=datetime(2023, 1, 1),
        end_date=datetime(2023, 12, 31),
        engine_type="event",
        data_resolution="bar",
        config_hash="mc_test"
    )

    # Create Monte Carlo simulation
    sim_id = db.create_monte_carlo_simulation(
        backtest_id=backtest_id,
        simulation_type="shuffle_trades",
        num_simulations=1000,
        block_size=None,
        random_seed=42
    )
    print(f"Monte Carlo simulation created: ID {sim_id}")

    # Simulate results (in practice, computed by Monte Carlo engine)
    results = {
        "mean_return": 15.8,
        "median_return": 14.2,
        "std_return": 8.5,
        "ci_95_lower": 5.2,
        "ci_95_upper": 28.5,
        "ci_99_lower": 2.1,
        "ci_99_upper": 32.8,
        "probability_of_profit": 0.78,
        "probability_of_ruin": 0.02,
        "expected_shortfall_95": -12.5,
        "percentile_5": 3.2,
        "percentile_25": 9.8,
        "percentile_50": 14.2,
        "percentile_75": 20.5,
        "percentile_95": 28.5,
        "original_return": 16.2,
        "original_sharpe": 1.85,
        "original_max_dd": 12.8,
        "distribution_data": {
            "returns": [12.5, 15.8, 18.2],  # Simplified
            "drawdowns": [8.5, 12.8, 15.2],
            "sharpes": [1.5, 1.85, 2.1]
        }
    }

    # Save results
    success = db.save_monte_carlo_results(sim_id, results)
    if success:
        print("Monte Carlo results saved")
        print(f"  Mean return: {results['mean_return']:.2f}%")
        print(f"  95% CI: [{results['ci_95_lower']:.2f}%, {results['ci_95_upper']:.2f}%]")
        print(f"  Probability of profit: {results['probability_of_profit'] * 100:.1f}%")
        print(f"  Probability of ruin: {results['probability_of_ruin'] * 100:.2f}%")


def example_complete_optimization_workflow():
    """
    Example: Complete optimization workflow

    1. Create optimization run
    2. Execute parameter search
    3. Save results
    4. Identify best parameters
    5. Validate with walk-forward
    6. Assess robustness with Monte Carlo
    """
    db = SQLiteDatabase(db_path="test_opt_workflow.db")
    db.initialize_database()

    print("Step 1: Create optimization run")
    opt_id = db.create_optimization_run(
        strategy_name="Production Strategy",
        strategy_version="2.0.0",
        optimization_type="grid_search",
        optimization_method="exhaustive",
        start_date=datetime(2023, 1, 1),
        end_date=datetime(2023, 12, 31),
        parameter_space={
            "fast_ma": [8, 10, 13],
            "slow_ma": [20, 21, 25],
            "stop_atr": [2.0, 2.5]
        },
        objective_function="sharpe_ratio",
        symbols=["EURUSD"],
        timeframes=["H1"],
        total_combinations=18,  # 3 * 3 * 2
        n_jobs=4
    )
    print(f"  Optimization ID: {opt_id}")

    print("\nStep 2: Execute parameter search")
    db.update_optimization_status(opt_id, "running")
    print("  (External: Run backtest for each combination)")

    print("\nStep 3: Save results")
    # Simulate results
    results = [
        {
            "backtest_id": 201,
            "parameters": {"fast_ma": 10, "slow_ma": 21, "stop_atr": 2.0},
            "score": 2.15,
            "rank": 1,
            "total_trades": 42,
            "win_rate": 0.57,
            "profit_factor": 1.9,
            "sharpe_ratio": 2.15,
            "max_drawdown": 11.5,
            "is_best": True,
            "is_top_10": True
        }
    ]
    db.save_optimization_results(opt_id, results)
    print(f"  Saved {len(results)} results")

    print("\nStep 4: Identify best parameters")
    db.update_optimization_status(
        opt_id,
        "completed",
        best_backtest_id=201,
        best_score=2.15,
        best_parameters=results[0]["parameters"]
    )
    print(f"  Best: {results[0]['parameters']}")
    print(f"  Score: {results[0]['score']}")

    print("\nStep 5: Validate with walk-forward")
    print("  (Create walk-forward windows)")
    print("  (Test parameter stability across periods)")

    print("\nStep 6: Assess robustness with Monte Carlo")
    print("  (Run Monte Carlo simulation on best backtest)")
    print("  (Estimate distribution of outcomes)")

    print("\nOptimization workflow complete!")


if __name__ == "__main__":
    print("=" * 80)
    print("OptimizationManager Usage Examples")
    print("=" * 80)

    print("\n1. Create Optimization Run")
    print("-" * 80)
    example_create_optimization_run()

    print("\n2. Update Optimization Status")
    print("-" * 80)
    example_update_optimization_status()

    print("\n3. Save Optimization Results")
    print("-" * 80)
    example_save_optimization_results()

    print("\n4. Get Optimization Results")
    print("-" * 80)
    example_get_optimization_results()

    print("\n5. Walk-Forward Analysis")
    print("-" * 80)
    example_walk_forward_analysis()

    print("\n6. Monte Carlo Simulation")
    print("-" * 80)
    example_monte_carlo_simulation()

    print("\n7. Complete Optimization Workflow")
    print("-" * 80)
    example_complete_optimization_workflow()
