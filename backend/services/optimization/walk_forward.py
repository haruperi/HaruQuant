"""
Walk-Forward Analysis.

Optimizes on rolling training windows and tests on out-of-sample data.
"""

from typing import Any, Callable, Dict, List, Optional, Type

import numpy as np

from backend.common.logger import logger

from .execution import run_strategy_backtest
from .methods.grid_search import grid_search
from .result import OptimizationSummary
from .scoring import sharpe_score

BacktestResult = Any
BaseStrategy = Any


def walk_forward(  # noqa: C901
    strategy_class: Type[BaseStrategy],
    data,
    param_grid: Dict[str, List[Any]],
    train_period: int = 252,
    test_period: int = 63,
    initial_balance: float = 10000.0,
    scoring_func: Callable[[BacktestResult], float] = sharpe_score,
    verbose: bool = True,
    progress_callback: Optional[Callable] = None,
    strategy_file_path: Optional[str] = None,
    symbol: Optional[str] = None,
) -> Dict[str, Any]:
    """Walk-forward optimization."""
    if verbose:
        logger.info("Starting walk-forward analysis")
        logger.info(
            f"Train period: {train_period} bars, Test period: {test_period} bars"
        )

    if not symbol:
        symbol = data.name if hasattr(data, "name") else "UNKNOWN"

    total_bars = len(data)
    windows = []
    current_start = 0

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

    optimize_params = bool(param_grid) and any(len(values) > 1 for values in param_grid.values())

    if verbose:
        logger.info(f"Generated {len(windows)} walk-forward windows")
        if optimize_params:
            logger.info(f"Mode: Optimization with parameter grid: {param_grid}")
        else:
            logger.info("Mode: Testing with default parameters (no optimization)")

    wf_results = []

    for i, window in enumerate(windows):
        if verbose:
            logger.info(f"Window {i + 1}/{len(windows)}")

        train_data = data.iloc[window["train_start"] : window["train_end"]]
        test_data = data.iloc[window["test_start"] : window["test_end"]]

        if optimize_params:
            train_summary = grid_search(
                strategy_class,
                train_data,
                param_grid,
                initial_balance=initial_balance,
                scoring_func=scoring_func,
                engine_type="vectorised",
                verbose=False,
                strategy_file_path=strategy_file_path,
                symbol=symbol,
            )
            best_params = train_summary.best_params
            train_result = train_summary.best_result
            train_score = train_summary.best_score
        else:
            train_result = run_strategy_backtest(
                strategy_class=strategy_class,
                data=train_data,
                symbol=symbol,
                params={},
                initial_balance=initial_balance,
                engine_type="vectorised",
                position_size=0.1,
            )
            train_score = scoring_func(train_result)
            strategy = strategy_class(params={"symbol": symbol})
            best_params = {k: v for k, v in getattr(strategy, "params", {}).items() if k != "symbol"}

        test_result = run_strategy_backtest(
            strategy_class=strategy_class,
            data=test_data,
            symbol=symbol,
            params=best_params,
            initial_balance=initial_balance,
            engine_type="vectorised",
            position_size=0.1,
        )
        test_score = scoring_func(test_result)

        train_return = float(getattr(train_result, "total_return_pct", 0.0) or 0.0) if train_result else 0.0
        train_sharpe = float(getattr(train_result, "sharpe_ratio", 0.0) or 0.0) if train_result else 0.0
        train_drawdown = float(getattr(train_result, "max_drawdown_pct", 0.0) or 0.0) if train_result else 0.0
        test_return = float(getattr(test_result, "total_return_pct", 0.0) or 0.0)
        test_sharpe = float(getattr(test_result, "sharpe_ratio", 0.0) or 0.0)
        test_drawdown = float(getattr(test_result, "max_drawdown_pct", 0.0) or 0.0)
        overfitting_ratio = (test_return / train_return) if train_return not in (0.0, -0.0) else 0.0

        window_result = {
            "window": i + 1,
            "window_number": i + 1,
            "train_period": (
                data.index[window["train_start"]],
                data.index[window["train_end"] - 1],
            ),
            "test_period": (
                data.index[window["test_start"]],
                data.index[window["test_end"] - 1],
            ),
            "train_start": data.index[window["train_start"]],
            "train_end": data.index[window["train_end"] - 1],
            "test_start": data.index[window["test_start"]],
            "test_end": data.index[window["test_end"] - 1],
            "best_params": best_params,
            "train_score": train_score,
            "test_score": test_score,
            "train_return": train_return,
            "train_sharpe": train_sharpe,
            "train_drawdown": train_drawdown,
            "test_return": test_return,
            "test_sharpe": test_sharpe,
            "test_drawdown": test_drawdown,
            "overfitting_ratio": overfitting_ratio,
        }

        wf_results.append(window_result)

        if progress_callback:
            progress_callback(
                window_num=i + 1,
                total_windows=len(windows),
                window_result=window_result,
            )

    avg_test_score = float(np.mean([r["test_score"] for r in wf_results])) if wf_results else 0.0
    avg_test_return = float(np.mean([r["test_return"] for r in wf_results])) if wf_results else 0.0
    avg_train_return = float(np.mean([r["train_return"] for r in wf_results])) if wf_results else 0.0
    robustness_ratio = (avg_test_return / avg_train_return) if avg_train_return not in (0.0, -0.0) else 0.0

    summary = {
        "windows": wf_results,
        "n_windows": len(windows),
        "avg_test_score": avg_test_score,
        "avg_test_return": avg_test_return,
        "avg_train_return": avg_train_return,
        "robustness_ratio": robustness_ratio,
        "train_period_bars": train_period,
        "test_period_bars": test_period,
    }

    if verbose:
        logger.success("Walk-forward analysis complete")
        logger.info(f"Average test score: {avg_test_score:.4f}")
        logger.info(f"Average test return: {avg_test_return:.2f}%")

    return summary


def print_optimization_report(summary: OptimizationSummary, top_n: int = 10) -> None:
    """Print formatted optimization report."""
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
    print(f"  Win Rate:        {best_metrics.get('win_rate', 0):.1f}%")
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
