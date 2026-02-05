"""Example 03: Strategy Optimization

This example demonstrates parameter optimization using grid search.

Topics covered:
- Basic optimization with grid_search()
- Parameter ranges and constraints
- Result analysis and visualization
- Avoiding overfitting
- Best practices

Author: HaruQuant Development Team
Created: 2025-12-03
"""

import sys
from pathlib import Path

# Add project root to path
project_root = Path(__file__).resolve().parents[4]
sys.path.insert(0, str(project_root))

import pandas as pd  # noqa: E402

# No longer need to import engine directly - handled by optimization module
from apps.logger import logger  # noqa: E402
from apps.optimization.methods.grid_search import grid_search  # noqa: E402
from apps.optimization.scoring import sharpe_score  # noqa: E402
from apps.utils.data_getters import load_mt5  # noqa: E402
from data.strategies.trend_following import TrendFollowingStrategy  # noqa: E402


def example1_basic_optimization():
    """Basic parameter optimization."""
    print("\n" + "=" * 70)
    print("Example 1: Basic Optimization")
    print("=" * 70)

    # Load data
    data = load_mt5("EURUSD", timeframe="H1", count=800)
    if data is None or data.empty:
        print("No data loaded from MT5. Exiting...")
        return
    data.name = "EURUSD"

    print(f"Loaded {len(data):,} bars")

    # Parameter grid for trend following
    print("\nOptimizing trend-following parameters...")
    print("  Fast: 10-30 (step 10)")
    print("  Slow: 50-100 (step 25)")
    print("  Filter: 100-200 (step 50)")

    param_grid = {
        "fast_period": [10, 20, 30],
        "slow_period": [50, 75, 100],
        "filter_period": [100, 150, 200],
    }
    constraint = (
        lambda p: p["fast_period"] < p["slow_period"] < p["filter_period"]
    )

    try:
        summary = grid_search(
            strategy_class=TrendFollowingStrategy,
            data=data,
            param_grid=param_grid,
            scoring_func=sharpe_score,
            engine_type="event_driven",
            initial_balance=10000.0,
            constraint=constraint,
            verbose=True,
        )

        print("\n" + "-" * 70)
        print("OPTIMIZATION RESULTS")
        print("-" * 70)

        print("\nBest Parameters:")
        for key, value in summary.best_params.items():
            print(f"  {key}: {value}")

        best_result = summary.best_result
        if best_result:
            print("\nBest Performance:")
            print(f"  Sharpe Ratio: {summary.best_score:.2f}")
            print(f"  Total Return: {best_result.total_return_pct:.2f}%")
            print(f"  Max Drawdown: {best_result.max_drawdown_pct:.2f}%")
            print(f"  Total Trades: {best_result.total_trades}")
        else:
            print("\nNo valid optimization results returned.")

    except Exception as e:
        print(f"\nOptimization failed: {e}")
        print("Note: Optimization requires sufficient data and trades")


def example2_avoiding_overfitting():
    """Demonstrate overfitting risks and solutions."""
    print("\n" + "=" * 70)
    print("Example 2: Avoiding Overfitting")
    print("=" * 70)

    print("\nOverfitting Risks:")
    print("  - Optimizing on all available data")
    print("  - Using too many parameters")
    print("  - Choosing best single result")
    print("  - Ignoring parameter stability")

    print("\nSolutions:")
    print("  - Split data: 70% train, 30% test")
    print("  - Limit parameters (2-4 max)")
    print("  - Choose robust parameters (good across range)")
    print("  - Use walk-forward analysis")
    print("  - Test on out-of-sample data")

    print("\nExample Split:")
    data = load_mt5("EURUSD", timeframe="H1", count=1000)
    if data is None or data.empty:
        print("  No data loaded from MT5. Skipping split example.")
        return
    data.name = "EURUSD"

    split_idx = int(len(data) * 0.7)
    train_data = data.iloc[:split_idx]
    test_data = data.iloc[split_idx:]

    print(f"\n  Total data: {len(data):,} bars")
    print(f"  Train (70%): {len(train_data):,} bars")
    print(f"  Test (30%): {len(test_data):,} bars")

    print("\nWorkflow:")
    print("  1. Optimize on train_data")
    print("  2. Get best parameters")
    print("  3. Test on test_data (out-of-sample)")
    print("  4. Compare performance")

    train_data.name = "EURUSD"
    test_data.name = "EURUSD"

    param_grid = {
        "fast_period": [10, 20, 30],
        "slow_period": [50, 75, 100],
        "filter_period": [100, 150, 200],
    }
    constraint = (
        lambda p: p["fast_period"] < p["slow_period"] < p["filter_period"]
    )

    print("\nRunning train optimization...")
    summary = grid_search(
        strategy_class=TrendFollowingStrategy,
        data=train_data,
        param_grid=param_grid,
        scoring_func=sharpe_score,
        engine_type="event_driven",
        initial_balance=10000.0,
        constraint=constraint,
        verbose=False,
    )

    if not summary.best_result:
        print("  No valid optimization results returned. Skipping out-of-sample test.")
        return

    print("\nBest Train Parameters:")
    for key, value in summary.best_params.items():
        print(f"  {key}: {value}")

    print("\nRunning out-of-sample test...")
    test_params = summary.best_params.copy()
    test_params["symbol"] = "EURUSD"
    test_strategy = TrendFollowingStrategy(params=test_params)
    test_engine = EventDrivenEngine(
        test_strategy, test_data, initial_balance=10000.0
    )
    test_result = test_engine.run()

    print("\nOut-of-Sample Performance:")
    print(f"  Total Return: {test_result.total_return_pct:.2f}%")
    print(f"  Max Drawdown: {test_result.max_drawdown_pct:.2f}%")
    print(f"  Total Trades: {test_result.total_trades}")


def example3_best_practices():
    """Best practices for optimization."""
    print("\n" + "=" * 70)
    print("Example 3: Best Practices")
    print("=" * 70)

    print("\n1. Parameter Selection:")
    print("   - Keep it simple (2-4 parameters)")
    print("   - Use meaningful ranges")
    print("   - Appropriate step sizes")

    print("\n2. Optimization Metrics:")
    print("   - Sharpe Ratio: Risk-adjusted return")
    print("   - Sortino Ratio: Downside risk focus")
    print("   - Calmar Ratio: Return/drawdown")
    print("   - Custom: Return / Max Drawdown")

    print("\n3. Constraints:")
    print("   Example constraints to enforce valid parameters")
    print("   - fast_period < slow_period")
    print("   - filter_period > slow_period")

    print("\n4. Result Analysis:")
    print("   - Don't just pick best result")
    print("   - Look for parameter stability")
    print("   - Check nearby parameters")
    print("   - Verify results make sense")

    print("\n5. Performance Tips:")
    print("   - Limit parameter ranges")
    print("   - Use larger step sizes initially")
    print("   - Refine around good regions")
    print("   - Consider parallel optimization")

    print("\n6. Common Mistakes:")
    print("   - Optimizing on all data")
    print("   - Too many parameters")
    print("   - Too fine granularity")
    print("   - Ignoring transaction costs")
    print("   - Not validating results")


def main():
    """Run all examples."""
    print("\n" + "=" * 70)
    print("OPTIMIZATION EXAMPLES")
    print("=" * 70)

    try:
        example1_basic_optimization()
        example2_avoiding_overfitting()
        example3_best_practices()

        print("\n" + "=" * 70)
        print("ALL EXAMPLES COMPLETED")
        print("=" * 70)

        print("\nKey Takeaways:")
        print("1. Use grid_search() for parameter tuning")
        print("2. Always validate on out-of-sample data")
        print("3. Keep strategies simple (few parameters)")
        print("4. Choose robust, stable parameters")
        print("5. Use constraints to reduce search space")

        print("\nNext Steps:")
        print("- Try 04_walk_forward.py for proper validation")
        print("- Explore 05_monte_carlo.py for risk analysis")

    except Exception as e:
        logger.error(f"Error running examples: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    main()
