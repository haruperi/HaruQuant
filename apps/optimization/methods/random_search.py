"""
Random Search Optimization.

Randomly samples parameter combinations.
More efficient than grid search for large parameter spaces.
"""

import importlib.util
import inspect
import time
from concurrent.futures import ProcessPoolExecutor, as_completed
from typing import Any, Callable, Dict, Optional, Tuple, Type, cast

import numpy as np

from apps.logger import logger
from apps.strategy import BaseStrategy

from ..result import OptimizationResult, OptimizationSummary
from ..scoring import sharpe_score

# from apps.backtest.engine import BaseEngine, EventDrivenEngine, VectorizedEngine
# from apps.backtest.result import BacktestResult

BaseEngine = Any
EventDrivenEngine = Any
VectorizedEngine = Any
BacktestResult = Any


def _load_strategy_from_path(path: str, class_name: str) -> Type[BaseStrategy]:
    """Dynamically load strategy class from file path."""
    spec = importlib.util.spec_from_file_location("dynamic_strategy", path)
    if spec is None or spec.loader is None:
        raise ImportError(f"Could not load module spec for {path}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return cast(Type[BaseStrategy], getattr(module, class_name))


def _run_single_random_backtest(args):
    """
    Run a single backtest (pickleable for multiprocessing).

    Args:
        args: Tuple of ((strategy_path, class_name), data, symbol, params, initial_balance, engine_type, scoring_func)

    Returns:
        Tuple of (params, OptimizationResult or None, error)
    """
    strategy_info, data, symbol, params, initial_balance, engine_type, scoring_func = (
        args
    )
    strategy_path, strategy_class_name = strategy_info

    try:
        # Load strategy class dynamically
        strategy_class = _load_strategy_from_path(strategy_path, strategy_class_name)

        full_params = params.copy()
        full_params["symbol"] = symbol
        strategy = strategy_class(params=full_params)

        engine: BaseEngine
        if engine_type == "vectorized":
            engine = VectorizedEngine(strategy, data, initial_balance=initial_balance)
        else:
            engine = EventDrivenEngine(strategy, data, initial_balance=initial_balance)

        result = engine.run()
        result_metrics = result.summary()
        score = scoring_func(result)

        opt_result = OptimizationResult(
            parameters=params, result=result, metrics=result_metrics, score=score
        )

        return (params, opt_result, None)

    except Exception as e:
        return (params, None, str(e))


def random_search(  # noqa: C901
    strategy_class: Type[BaseStrategy],
    data,  # pd.DataFrame
    param_distributions: Dict[str, Tuple[Any, Any]],
    n_iter: int = 100,
    initial_balance: float = 10000.0,
    scoring_func: Callable[[BacktestResult], float] = sharpe_score,
    engine_type: str = "vectorized",
    max_workers: Optional[int] = None,
    seed: Optional[int] = None,
    verbose: bool = True,
    progress_callback: Optional[Callable] = None,
    strategy_file_path: Optional[str] = None,
    symbol: Optional[str] = None,
) -> OptimizationSummary:
    """
    Random search over parameter space.

    Randomly samples parameter combinations.
    More efficient than grid search for large parameter spaces.

    Args:
        strategy_class: Strategy class to optimize
        data: OHLCV DataFrame
        param_distributions: Dict of param names to (min, max) tuples
        n_iter: Number of random combinations to try
        initial_balance: Starting balance
        scoring_func: Function to score results
        engine_type: "vectorized" or "event_driven"
        seed: Random seed for reproducibility
        verbose: Print progress
        progress_callback: Optional callback(completed, total, current_params, best_score, best_params)
        strategy_file_path: Optional path to strategy file (needed for parallel execution with dynamic classes)

    Returns:
        OptimizationSummary with results

    Example:
        >>> param_distributions = {
        ...     'ema_fast': (5, 30),     # integers
        ...     'ema_slow': (30, 100),
        ...     'atr_period': (10, 20)
        ... }
        >>> summary = random_search(
        ...     TrendFollowingStrategy,
        ...     data,
        ...     param_distributions,
        ...     n_iter=50
        ... )
    """
    if seed is not None:
        np.random.seed(seed)

    if verbose:
        logger.info(f"Starting random search: {n_iter} iterations")
        logger.info(f"Parameter ranges: {param_distributions}")

    start_time = time.time()
    all_results = []
    completed = 0
    failed = 0
    best_score_so_far = float("-inf")
    best_params_so_far = None

    # Generate all random parameter combinations upfront
    all_param_combinations = []
    for _i in range(n_iter):
        params = {}
        for param_name, (min_val, max_val) in param_distributions.items():
            if isinstance(min_val, int) and isinstance(max_val, int):
                params[param_name] = np.random.randint(min_val, max_val + 1)
            else:
                params[param_name] = np.random.uniform(min_val, max_val)
        all_param_combinations.append(params)

    # Determine if we should use parallel execution
    use_parallel = max_workers is not None and max_workers > 1 and n_iter > 1

    if use_parallel:
        # Parallel execution
        if verbose:
            logger.info(f"Running parallel execution with {max_workers} workers")

        # Extract strategy info for pickling
        try:
            if strategy_file_path:
                strategy_path = strategy_file_path
            else:
                strategy_path = inspect.getfile(strategy_class)

            strategy_name = strategy_class.__name__
            strategy_info = (strategy_path, strategy_name)
        except Exception as e:
            logger.warning(
                f"Could not get strategy file path: {e}. Falling back to sequential execution."
            )
            raise RuntimeError(f"Cannot run parallel optimization: {e}")

        # Get symbol (prefer explicit parameter, fallback to data.name)
        # Note: data.name is not preserved during pickling for multiprocessing
        if not symbol:
            symbol = data.name if hasattr(data, "name") else "UNKNOWN"

        # Prepare tasks
        tasks = [
            (
                strategy_info,
                data,
                symbol,
                params,
                initial_balance,
                engine_type,
                scoring_func,
            )
            for params in all_param_combinations
        ]

        # Run in parallel
        with ProcessPoolExecutor(max_workers=max_workers) as executor:
            future_to_params = {
                executor.submit(_run_single_random_backtest, task): task[2]
                for task in tasks
            }

            for future in as_completed(future_to_params):
                params, opt_result, error = future.result()

                if opt_result:
                    all_results.append(opt_result)
                    completed += 1

                    if opt_result.score > best_score_so_far:
                        best_score_so_far = opt_result.score
                        best_params_so_far = params

                    if progress_callback:
                        progress_callback(
                            completed=completed,
                            total=n_iter,
                            current_params=params,
                            best_score=best_score_so_far,
                            best_params=best_params_so_far,
                        )
                else:
                    logger.error(f"Failed for params {params}: {error}")
                    failed += 1

                if verbose and completed % max(1, n_iter // 10) == 0:
                    logger.info(
                        f"Progress: {completed}/{n_iter} ({completed / n_iter * 100:.1f}%)"
                    )

    else:
        # Sequential execution
        for i, params in enumerate(all_param_combinations):
            if verbose and (i + 1) % max(1, n_iter // 10) == 0:
                logger.info(
                    f"Progress: {i + 1}/{n_iter} ({(i + 1) / n_iter * 100:.1f}%)"
                )

            try:
                # Create strategy
                full_params = params.copy()
                full_params["symbol"] = (
                    data.name if hasattr(data, "name") else "UNKNOWN"
                )
                strategy = strategy_class(params=full_params)

                # Run backtest
                engine: BaseEngine
                if engine_type == "vectorized":
                    engine = VectorizedEngine(
                        strategy, data, initial_balance=initial_balance
                    )
                else:
                    engine = EventDrivenEngine(
                        strategy, data, initial_balance=initial_balance
                    )

                result = engine.run()

                # Metrics and score
                result_metrics = result.summary()
                score = scoring_func(result)

                opt_result = OptimizationResult(
                    parameters=params,
                    result=result,
                    metrics=result_metrics,
                    score=score,
                )
                all_results.append(opt_result)
                completed += 1

                # Track best
                if score > best_score_so_far:
                    best_score_so_far = score
                    best_params_so_far = params

                # Progress callback
                if progress_callback:
                    progress_callback(
                        completed=completed,
                        total=n_iter,
                        current_params=params,
                        best_score=best_score_so_far,
                        best_params=best_params_so_far,
                    )

            except Exception as e:
                logger.error(f"Failed for params {params}: {e}")
                failed += 1

    # Rank results
    all_results.sort(key=lambda x: x.score, reverse=True)
    for i, opt_result in enumerate(all_results):
        opt_result.rank = i + 1

    best = all_results[0] if all_results else None
    duration = time.time() - start_time

    summary = OptimizationSummary(
        best_params=best.parameters if best else {},
        best_score=best.score if best else 0.0,
        best_result=best.result if best else None,
        all_results=all_results,
        total_combinations=n_iter,
        completed=completed,
        failed=failed,
        duration_seconds=duration,
    )

    if verbose:
        logger.success(f"Random search complete in {duration:.2f}s")
        logger.info(f"Best params: {summary.best_params}")
        logger.info(f"Best score: {summary.best_score:.4f}")

    return summary
