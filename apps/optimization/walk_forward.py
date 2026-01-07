"""
Walk-Forward Analysis.

Optimizes on rolling training windows and tests on out-of-sample data.
"""

from typing import Any, Callable, Dict, List, Optional, Type

import numpy as np

import apps.backtest.stats as stats
from apps.backtest.engine import VectorizedEngine
from apps.backtest.result import BacktestResult
from apps.logger import logger
from apps.strategy import BaseStrategy

from .methods.grid_search import grid_search
from .result import OptimizationSummary
from .scoring import sharpe_score


def walk_forward(  # noqa: C901
    strategy_class: Type[BaseStrategy],
    data,  # pd.DataFrame
    param_grid: Dict[str, List[Any]],
    train_period: int = 252,  # bars
    test_period: int = 63,  # bars
    initial_balance: float = 10000.0,
    scoring_func: Callable[[BacktestResult], float] = sharpe_score,
    verbose: bool = True,
    progress_callback: Optional[Callable] = None,
    strategy_file_path: Optional[str] = None,
    symbol: Optional[str] = None,
) -> Dict[str, Any]:
    """
    Walk-forward optimization.

    Optimizes on rolling training windows and tests on out-of-sample data.

    Args:
        strategy_class: Strategy class to optimize
        data: OHLCV DataFrame
        param_grid: Parameter grid
        train_period: Training window size (bars)
        test_period: Testing window size (bars)
        initial_balance: Starting balance
        scoring_func: Scoring function
        verbose: Print progress
        progress_callback: Optional callback(window_num, total_windows, window_result)
        strategy_file_path: Optional path to strategy file (passed to grid_search)

    Returns:
        Dictionary with walk-forward results

    Example:
        >>> results = walk_forward(
        ...     TrendFollowingStrategy,
        ...     data,
        ...     param_grid={'ema_fast': [10, 20], 'ema_slow': [40, 50]},
        ...     train_period=500,
        ...     test_period=100
        ... )
    """
    if verbose:
        logger.info("Starting walk-forward analysis")
        logger.info(
            f"Train period: {train_period} bars, Test period: {test_period} bars"
        )

    # Get symbol (prefer explicit parameter, fallback to data.name)
    # Note: data.name is not preserved during pickling for multiprocessing
    if not symbol:
        symbol = data.name if hasattr(data, "name") else "UNKNOWN"

    total_bars = len(data)
    windows = []
    current_start = 0

    # Generate windows
    while current_start + train_period + test_period <= total_bars:
        train_start = current_start
        train_end = current_start + train_period
        test_start = train_end
        test_end = test_start + test_period

        windows.append(
            {
                "train_start": train_start,
                "train_end": train_end,
                "test_start": test_start,
                "test_end": test_end,
            }
        )

        current_start += test_period

    # Check if we're optimizing or just testing default parameters
    optimize_params = param_grid and any(
        len(values) > 1 for values in param_grid.values()
    )

    if verbose:
        logger.info(f"Generated {len(windows)} walk-forward windows")
        if optimize_params:
            logger.info(f"Mode: Optimization with parameter grid: {param_grid}")
        else:
            logger.info("Mode: Testing with default parameters (no optimization)")

    # Run walk-forward
    wf_results = []

    for i, window in enumerate(windows):
        if verbose:
            logger.info(f"Window {i + 1}/{len(windows)}")

        # Get train and test data
        train_data = data.iloc[window["train_start"] : window["train_end"]]
        test_data = data.iloc[window["test_start"] : window["test_end"]]

        if optimize_params:
            # Optimize on train data
            train_summary = grid_search(
                strategy_class,
                train_data,
                param_grid,
                initial_balance=initial_balance,
                scoring_func=scoring_func,
                engine_type="vectorized",
                verbose=False,
                strategy_file_path=strategy_file_path,
                symbol=symbol,
            )

            # Test best params on test data
            best_params = train_summary.best_params
            train_score = train_summary.best_score
        else:
            # No optimization - use default parameters
            # Create strategy with just symbol to get default params
            full_params = {"symbol": symbol}
            strategy = strategy_class(params=full_params)

            # Run on train data to get train score
            engine = VectorizedEngine(
                strategy, train_data, initial_balance=initial_balance
            )
            train_result = engine.run()
            train_score = scoring_func(train_result)

            # Extract the actual params used (excluding symbol)
            best_params = {k: v for k, v in strategy.params.items() if k != "symbol"}

        # Test params on test data
        full_params = best_params.copy()
        full_params["symbol"] = symbol
        strategy = strategy_class(params=full_params)
        engine = VectorizedEngine(strategy, test_data, initial_balance=initial_balance)
        test_result = engine.run()

        window_result = {
            "window": i + 1,
            "train_period": (
                data.index[window["train_start"]],
                data.index[window["train_end"] - 1],
            ),
            "test_period": (
                data.index[window["test_start"]],
                data.index[window["test_end"] - 1],
            ),
            "best_params": best_params,
            "train_score": train_score,
            "test_score": scoring_func(test_result),
            "test_return": stats.total_return(test_result),
        }

        wf_results.append(window_result)

        # Progress callback
        if progress_callback:
            progress_callback(
                window_num=i + 1,
                total_windows=len(windows),
                window_result=window_result,
            )

    # Aggregate results
    avg_test_score = np.mean([r["test_score"] for r in wf_results])
    avg_test_return = np.mean([r["test_return"] for r in wf_results])

    summary = {
        "windows": wf_results,
        "n_windows": len(windows),
        "avg_test_score": avg_test_score,
        "avg_test_return": avg_test_return,
        "train_period_bars": train_period,
        "test_period_bars": test_period,
    }

    if verbose:
        logger.success("Walk-forward analysis complete")
        logger.info(f"Average test score: {avg_test_score:.4f}")
        logger.info(f"Average test return: {avg_test_return:.2f}%")

    return summary


def print_optimization_report(summary: OptimizationSummary, top_n: int = 10) -> None:
    """
    Print formatted optimization report.

    Args:
        summary: OptimizationSummary
        top_n: Number of top results to show
    """
    print("\n" + "=" * 80)
    print("OPTIMIZATION REPORT")
    print("=" * 80)

    print(f"\nTotal combinations: {summary.total_combinations}")
    print(f"Completed: {summary.completed}")
    print(f"Failed: {summary.failed}")
    print(f"Duration: {summary.duration_seconds:.2f}s")

    print("\nBEST PARAMETERS:")
    print("-" * 80)
    for param, value in summary.best_params.items():
        print(f"  {param:<20} = {value}")

    print(f"\nBest Score: {summary.best_score:.4f}")

    best_metrics = summary.all_results[0].metrics if summary.all_results else {}
    print("\nBest Performance:")
    print(f"  Total Return:    {best_metrics.get('total_return_pct', 0):.2f}%")
    print(f"  Sharpe Ratio:    {best_metrics.get('sharpe_ratio', 0):.2f}")
    print(f"  Max Drawdown:    {best_metrics.get('max_drawdown_pct', 0):.2f}%")
    print(f"  Win Rate:        {best_metrics.get('win_rate_pct', 0):.1f}%")
    print(f"  Profit Factor:   {best_metrics.get('profit_factor', 0):.2f}")

    print(f"\nTOP {top_n} RESULTS:")
    print("-" * 80)

    top_results = summary.get_top_n(top_n)
    for opt_result in top_results:
        print(f"\nRank {opt_result.rank}: Score = {opt_result.score:.4f}")
        print(f"  Parameters: {opt_result.parameters}")
        print(
            f"  Return: {opt_result.metrics['total_return_pct']:.2f}%, "
            f"Sharpe: {opt_result.metrics['sharpe_ratio']:.2f}, "
            f"DD: {opt_result.metrics['max_drawdown_pct']:.2f}%"
        )

    print("\n" + "=" * 80)
