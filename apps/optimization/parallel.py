"""
Parallel Processing Module.

Multi-core optimization for faster backtesting.
Parallelizes grid search, random search, and walk-forward analysis.
"""

import time
from concurrent.futures import ProcessPoolExecutor, as_completed
from multiprocessing import Lock
from typing import Any, Callable, Dict, List, Optional, Tuple

import pandas as pd

from apps.logger import logger

# =========================================================================
# Progress Tracking
# =========================================================================


class ProgressTracker:
    """
    Thread-safe progress tracker for parallel operations.

    Tracks completion of parallel tasks and displays progress bar.
    """

    def __init__(self, total: int, description: str = "Processing"):
        """
        Initialize progress tracker.

        Args:
            total: Total number of tasks
            description: Description of the task
        """
        self.total = total
        self.description = description
        self.completed = 0
        self.start_time = time.time()
        self.lock = Lock()

    def update(self, increment: int = 1) -> None:
        """
        Update progress (thread-safe).

        Args:
            increment: Number of tasks completed
        """
        with self.lock:
            self.completed += increment
            self._print_progress()

    def _print_progress(self) -> None:
        """Print progress bar to console."""
        if self.total == 0:
            return

        pct = (self.completed / self.total) * 100
        elapsed = time.time() - self.start_time

        # Calculate ETA
        if self.completed > 0:
            rate = self.completed / elapsed
            remaining = self.total - self.completed
            eta = remaining / rate if rate > 0 else 0
            eta_str = f"ETA: {eta:.0f}s"
        else:
            eta_str = "ETA: --"

        # Progress bar
        bar_width = 40
        filled = int(bar_width * self.completed / self.total)
        bar = "=" * filled + "-" * (bar_width - filled)

        print(
            f"\r{self.description}: [{bar}] {self.completed}/{self.total} "
            f"({pct:.1f}%) | {elapsed:.1f}s | {eta_str}",
            end="",
            flush=True,
        )

        if self.completed >= self.total:
            print()  # New line when complete


# =========================================================================
# Worker Function
# =========================================================================


def _run_backtest_worker(args: Tuple) -> Dict[str, Any]:
    """
    Worker function for running a single backtest.

    This function must be pickleable (top-level function) for multiprocessing.

    Args:
        args: Tuple of (engine_factory, params, task_id)
            engine_factory: Callable that creates and runs engine
            params: Dict of strategy parameters
            task_id: Unique task identifier

    Returns:
        Dict with backtest results and metadata
    """
    engine_factory, params, task_id = args

    try:
        # Run backtest
        start_time = time.time()
        result = engine_factory(params)
        duration = time.time() - start_time

        # Extract key metrics
        return {
            "task_id": task_id,
            "params": params,
            "result": result,
            "success": True,
            "error": None,
            "duration": duration,
            # Key metrics for quick access
            "total_return": result.total_return_pct if result else 0,
            "sharpe_ratio": result.sharpe_ratio if result else 0,
            "max_drawdown": result.max_drawdown_pct if result else 0,
            "total_trades": result.total_trades if result else 0,
        }

    except Exception as e:
        logger.error(f"Worker error for task {task_id}: {e}")
        return {
            "task_id": task_id,
            "params": params,
            "result": None,
            "success": False,
            "error": str(e),
            "duration": 0,
            "total_return": 0,
            "sharpe_ratio": 0,
            "max_drawdown": 0,
            "total_trades": 0,
        }


# =========================================================================
# Parallel Optimization Functions
# =========================================================================


def parallel_grid_search(
    engine_factory: Callable,
    param_grid: Dict[str, List[Any]],
    n_jobs: int = -1,
    show_progress: bool = True,
) -> List[Dict[str, Any]]:
    """
    Parallel grid search optimization.

    Runs backtest for all parameter combinations using multiple CPU cores.

    Args:
        engine_factory: Function that takes params dict and returns BacktestResult
        param_grid: Dict mapping parameter names to lists of values
            Example: {'ema_fast': [10, 20, 30], 'ema_slow': [50, 100]}
        n_jobs: Number of parallel jobs (-1 for all cores)
        show_progress: Show progress bar

    Returns:
        List of result dicts, sorted by total_return descending

    Example:
        ```python
        def engine_factory(params):
            strategy = MyStrategy(params)
            engine = EventDrivenEngine(strategy, data)
            return engine.run()

        results = parallel_grid_search(
            engine_factory,
            param_grid={'fast': [10, 20], 'slow': [50, 100]},
            n_jobs=4
        )
        ```
    """
    # Generate all parameter combinations
    param_names = list(param_grid.keys())
    param_values = list(param_grid.values())

    # Cartesian product
    from itertools import product

    combinations = list(product(*param_values))
    param_combinations = [dict(zip(param_names, combo)) for combo in combinations]

    total_combinations = len(param_combinations)

    logger.info(
        f"Starting parallel grid search: {total_combinations} combinations, "
        f"{n_jobs if n_jobs > 0 else 'all'} cores"
    )

    # Determine number of workers
    if n_jobs == -1:
        import os

        n_jobs = os.cpu_count() or 1

    # Create tasks
    tasks = [(engine_factory, params, i) for i, params in enumerate(param_combinations)]

    # Initialize progress tracker
    if show_progress:
        progress = ProgressTracker(total_combinations, "Grid Search")

    # Run in parallel
    results = []
    with ProcessPoolExecutor(max_workers=n_jobs) as executor:
        # Submit all tasks
        futures = {executor.submit(_run_backtest_worker, task): task for task in tasks}

        # Collect results as they complete
        for future in as_completed(futures):
            result = future.result()
            results.append(result)

            if show_progress:
                progress.update(1)

    # Sort by total return (descending)
    results.sort(key=lambda x: x["total_return"], reverse=True)

    logger.info(
        f"Grid search complete: Best return = {results[0]['total_return']:.2f}%, "
        f"Best params = {results[0]['params']}"
    )

    return results


def parallel_random_search(
    engine_factory: Callable,
    param_distributions: Dict[str, Callable],
    n_iter: int = 100,
    n_jobs: int = -1,
    random_seed: Optional[int] = None,
    show_progress: bool = True,
) -> List[Dict[str, Any]]:
    """
    Parallel random search optimization.

    Samples random parameter combinations and evaluates them in parallel.

    Args:
        engine_factory: Function that takes params dict and returns BacktestResult
        param_distributions: Dict mapping param names to sampling functions
            Example: {
                'ema_fast': lambda: random.randint(10, 30),
                'ema_slow': lambda: random.randint(50, 150)
            }
        n_iter: Number of random samples to evaluate
        n_jobs: Number of parallel jobs (-1 for all cores)
        random_seed: Random seed for reproducibility
        show_progress: Show progress bar

    Returns:
        List of result dicts, sorted by total_return descending

    Example:
        ```python
        import random

        results = parallel_random_search(
            engine_factory,
            param_distributions={
                'fast': lambda: random.randint(10, 30),
                'slow': lambda: random.randint(50, 150)
            },
            n_iter=100,
            n_jobs=4
        )
        ```
    """
    if random_seed is not None:
        import random

        random.seed(random_seed)

    logger.info(
        f"Starting parallel random search: {n_iter} iterations, "
        f"{n_jobs if n_jobs > 0 else 'all'} cores"
    )

    # Generate random parameter combinations
    param_combinations = []
    for _i in range(n_iter):
        params = {name: sampler() for name, sampler in param_distributions.items()}
        param_combinations.append(params)

    # Determine number of workers
    if n_jobs == -1:
        import os

        n_jobs = os.cpu_count() or 1

    # Create tasks
    tasks = [(engine_factory, params, i) for i, params in enumerate(param_combinations)]

    # Initialize progress tracker
    if show_progress:
        progress = ProgressTracker(n_iter, "Random Search")

    # Run in parallel
    results = []
    with ProcessPoolExecutor(max_workers=n_jobs) as executor:
        # Submit all tasks
        futures = {executor.submit(_run_backtest_worker, task): task for task in tasks}

        # Collect results as they complete
        for future in as_completed(futures):
            result = future.result()
            results.append(result)

            if show_progress:
                progress.update(1)

    # Sort by total return (descending)
    results.sort(key=lambda x: x["total_return"], reverse=True)

    logger.info(
        f"Random search complete: Best return = {results[0]['total_return']:.2f}%, "
        f"Best params = {results[0]['params']}"
    )

    return results


def parallel_walk_forward(
    engine_factory: Callable,
    data: pd.DataFrame,
    param_grid: Dict[str, List[Any]],
    train_size: int,
    test_size: int,
    n_jobs: int = -1,
    show_progress: bool = True,
) -> List[Dict[str, Any]]:
    """
    Parallel walk-forward optimization.

    Divides data into train/test windows and optimizes parameters on each window.

    Args:
        engine_factory: Function that takes (params, data, is_train) and returns BacktestResult
        data: Full dataset
        param_grid: Parameter grid for optimization
        train_size: Size of training window (in periods)
        test_size: Size of test window (in periods)
        n_jobs: Number of parallel jobs
        show_progress: Show progress bar

    Returns:
        List of walk-forward results with in-sample and out-of-sample metrics

    Example:
        ```python
        def engine_factory(params, data, is_train):
            strategy = MyStrategy(params)
            engine = EventDrivenEngine(strategy, data)
            result = engine.run()
            result.metadata['is_train'] = is_train
            return result

        wf_results = parallel_walk_forward(
            engine_factory,
            data=full_data,
            param_grid={'fast': [10, 20], 'slow': [50, 100]},
            train_size=252,  # 1 year
            test_size=63,     # 3 months
            n_jobs=4
        )
        ```
    """
    logger.info(
        f"Starting parallel walk-forward: train={train_size}, test={test_size}, "
        f"{n_jobs if n_jobs > 0 else 'all'} cores"
    )

    # Generate walk-forward windows
    windows: List[Dict[str, Any]] = []
    total_size = len(data)
    start_idx = 0

    while start_idx + train_size + test_size <= total_size:
        train_end = start_idx + train_size
        test_end = train_end + test_size

        train_data = data.iloc[start_idx:train_end]
        test_data = data.iloc[train_end:test_end]

        windows.append(
            {
                "window_id": len(windows),
                "train_data": train_data,
                "test_data": test_data,
                "train_start": data.index[start_idx],
                "train_end": data.index[train_end - 1],
                "test_start": data.index[train_end],
                "test_end": data.index[test_end - 1],
            }
        )

        # Move window forward by test_size
        start_idx += test_size

    logger.info(f"Generated {len(windows)} walk-forward windows")

    if len(windows) == 0:
        logger.warning("No walk-forward windows generated (insufficient data)")
        return []

    # Determine number of workers
    if n_jobs == -1:
        import os

        n_jobs = os.cpu_count() or 1

    # Process each window
    all_results = []

    for window in windows:
        logger.info(
            f"Processing window {window['window_id'] + 1}/{len(windows)}: "
            f"{window['train_start']} to {window['test_end']}"
        )

        # Run grid search on training data
        def train_engine_factory(params, window=window):
            return engine_factory(params, window["train_data"], is_train=True)

        train_results = parallel_grid_search(
            train_engine_factory,
            param_grid,
            n_jobs=n_jobs,
            show_progress=show_progress,
        )

        # Get best parameters from training
        best_params = train_results[0]["params"]
        best_train_result = train_results[0]["result"]

        logger.info(
            f"Best train params: {best_params}, "
            f"Train return: {train_results[0]['total_return']:.2f}%"
        )

        # Test on out-of-sample data
        test_result = engine_factory(best_params, window["test_data"], is_train=False)

        # Store results
        all_results.append(
            {
                "window_id": window["window_id"],
                "train_start": window["train_start"],
                "train_end": window["train_end"],
                "test_start": window["test_start"],
                "test_end": window["test_end"],
                "best_params": best_params,
                "train_return": train_results[0]["total_return"],
                "train_sharpe": train_results[0]["sharpe_ratio"],
                "train_drawdown": train_results[0]["max_drawdown"],
                "test_return": test_result.total_return_pct if test_result else 0,
                "test_sharpe": test_result.sharpe_ratio if test_result else 0,
                "test_drawdown": test_result.max_drawdown_pct if test_result else 0,
                "train_result": best_train_result,
                "test_result": test_result,
            }
        )

    logger.info(f"Walk-forward complete: {len(all_results)} windows processed")

    return all_results


# =========================================================================
# Helper Functions
# =========================================================================


def compare_parallel_speedup(
    engine_factory: Callable,
    param_grid: Dict[str, List[Any]],
    n_jobs_list: Optional[List[int]] = None,
) -> Dict[int, float]:
    """
    Compare speedup with different numbers of parallel workers.

    Args:
        engine_factory: Function that takes params dict and returns BacktestResult
        param_grid: Parameter grid
        n_jobs_list: List of worker counts to test

    Returns:
        Dict mapping n_jobs to execution time (seconds)
    """
    logger.info("Benchmarking parallel speedup")

    if n_jobs_list is None:
        n_jobs_list = [1, 2, 4, -1]

    results = {}

    for n_jobs in n_jobs_list:
        logger.info(f"Testing with {n_jobs} workers...")

        start_time = time.time()
        _ = parallel_grid_search(
            engine_factory, param_grid, n_jobs=n_jobs, show_progress=False
        )
        duration = time.time() - start_time

        results[n_jobs] = duration

        logger.info(f"Completed in {duration:.2f}s")

    return results


def get_optimal_n_jobs() -> int:
    """
    Get recommended number of parallel jobs.

    Returns:
        Recommended n_jobs based on CPU count
    """
    import os

    cpu_count = os.cpu_count() or 1

    # Leave one core free for system
    optimal = max(1, cpu_count - 1)

    logger.debug(f"Optimal n_jobs: {optimal} (CPU count: {cpu_count})")

    return optimal


def estimate_completion_time(
    single_run_time: float, total_runs: int, n_jobs: int
) -> float:
    """
    Estimate total completion time for parallel execution.

    Args:
        single_run_time: Time for single backtest (seconds)
        total_runs: Total number of backtests
        n_jobs: Number of parallel workers

    Returns:
        Estimated completion time (seconds)
    """
    # Account for overhead (assume 10%)
    overhead_factor = 1.1

    # Parallel time = (total_time / n_jobs) * overhead
    sequential_time = single_run_time * total_runs
    parallel_time = (sequential_time / n_jobs) * overhead_factor

    return parallel_time


# =========================================================================
# Result Analysis
# =========================================================================


def analyze_parallel_results(results: List[Dict[str, Any]]) -> pd.DataFrame:
    """
    Convert parallel results to DataFrame for analysis.

    Args:
        results: List of result dicts from parallel optimization

    Returns:
        DataFrame with all results and metrics
    """
    if not results:
        return pd.DataFrame()

    # Extract key fields
    rows = []
    for r in results:
        row = {
            "task_id": r["task_id"],
            "success": r["success"],
            "duration": r["duration"],
            "total_return": r["total_return"],
            "sharpe_ratio": r["sharpe_ratio"],
            "max_drawdown": r["max_drawdown"],
            "total_trades": r["total_trades"],
        }

        # Add parameters
        for param_name, param_value in r["params"].items():
            row[f"param_{param_name}"] = param_value

        rows.append(row)

    df = pd.DataFrame(rows)

    # Sort by total_return
    df = df.sort_values("total_return", ascending=False).reset_index(drop=True)

    return df


def analyze_walk_forward_results(wf_results: List[Dict[str, Any]]) -> Dict[str, Any]:
    """
    Analyze walk-forward optimization results.

    Args:
        wf_results: Results from parallel_walk_forward

    Returns:
        Dict with walk-forward analysis
    """
    if not wf_results:
        return {}

    # Extract metrics
    train_returns = [r["train_return"] for r in wf_results]
    test_returns = [r["test_return"] for r in wf_results]

    import numpy as np

    analysis = {
        "num_windows": len(wf_results),
        "avg_train_return": np.mean(train_returns),
        "avg_test_return": np.mean(test_returns),
        "std_train_return": np.std(train_returns),
        "std_test_return": np.std(test_returns),
        "train_test_correlation": (
            np.corrcoef(train_returns, test_returns)[0, 1]
            if len(train_returns) > 1
            else 0
        ),
        "overfitting_ratio": (
            np.mean(test_returns) / np.mean(train_returns)
            if np.mean(train_returns) != 0
            else 0
        ),
        "windows": wf_results,
    }

    # Check for overfitting
    if analysis["overfitting_ratio"] < 0.5:
        analysis["overfitting_assessment"] = "Severe overfitting"
    elif analysis["overfitting_ratio"] < 0.7:
        analysis["overfitting_assessment"] = "Moderate overfitting"
    elif analysis["overfitting_ratio"] < 0.9:
        analysis["overfitting_assessment"] = "Slight overfitting"
    else:
        analysis["overfitting_assessment"] = "No overfitting detected"

    return analysis
