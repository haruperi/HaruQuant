"""
Grid Search Optimization.

Exhaustive search over parameter space.
"""

import importlib.util
import inspect
import time
from concurrent.futures import ProcessPoolExecutor, as_completed
from itertools import product
from typing import Any, Callable, Dict, List, Optional, Type, cast

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


def _run_single_backtest(args):
    """
    Run a single backtest (must be pickleable for multiprocessing).

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

        # Create strategy with parameters
        full_params = params.copy()
        full_params["symbol"] = symbol
        strategy = strategy_class(params=full_params)

        # Run backtest
        engine: BaseEngine
        if engine_type == "vectorized":
            engine = VectorizedEngine(strategy, data, initial_balance=initial_balance)
        else:
            engine = EventDrivenEngine(strategy, data, initial_balance=initial_balance)

        result = engine.run()

        # Calculate metrics
        result_metrics = result.summary()

        # Score
        score = scoring_func(result)

        # Create optimization result
        opt_result = OptimizationResult(
            parameters=params, result=result, metrics=result_metrics, score=score
        )

        return (params, opt_result, None)

    except Exception as e:
        return (params, None, str(e))


def grid_search(  # noqa: C901
    strategy_class: Type[BaseStrategy],
    data,  # pd.DataFrame but avoid import
    param_grid: Dict[str, List[Any]],
    initial_balance: float = 10000.0,
    scoring_func: Callable[[BacktestResult], float] = sharpe_score,
    engine_type: str = "vectorized",
    max_workers: Optional[int] = None,
    verbose: bool = True,
    progress_callback: Optional[Callable] = None,
    strategy_file_path: Optional[str] = None,
    symbol: Optional[str] = None,
    constraint: Optional[Callable[[Dict[str, Any]], bool]] = None,
) -> OptimizationSummary:
    """
    Grid search over parameter space.

    Exhaustively tests all parameter combinations.

    Args:
        strategy_class: Strategy class to optimize
        data: OHLCV DataFrame
        param_grid: Dictionary of parameter names to lists of values
        initial_balance: Starting balance
        scoring_func: Function to score backtest results
        engine_type: "vectorized" (fast) or "event_driven" (accurate)
        max_workers: Max parallel workers (None = auto)
        verbose: Print progress
        progress_callback: Optional callback(completed, total, current_params, best_score, best_params)
        strategy_file_path: Optional path to strategy file (needed for parallel execution with dynamic classes)
        constraint: Optional function that returns True for valid parameter sets

    Returns:
        OptimizationSummary with results

    Example:
        >>> param_grid = {
        ...     'ema_fast': [10, 20, 30],
        ...     'ema_slow': [40, 50, 60],
        ...     'atr_period': [10, 14, 20]
        ... }
        >>> summary = grid_search(
        ...     TrendFollowingStrategy,
        ...     data,
        ...     param_grid,
        ...     scoring_func=sharpe_score
        ... )
        >>> print(summary.best_params)
        {'ema_fast': 20, 'ema_slow': 50, 'atr_period': 14}
    """
    if verbose:
        logger.info("Starting grid search optimization")
        logger.info(f"Parameters: {param_grid}")

    # Generate all parameter combinations
    param_names = list(param_grid.keys())
    param_values = list(param_grid.values())
    combinations = list(product(*param_values))

    param_sets = [dict(zip(param_names, combo)) for combo in combinations]
    if constraint:
        param_sets = [params for params in param_sets if constraint(params)]

    total = len(param_sets)

    if verbose:
        logger.info(f"Total combinations: {total}")

    start_time = time.time()

    # Run backtests
    all_results = []
    completed = 0
    failed = 0
    best_score_so_far = float("-inf")
    best_params_so_far = None

    # Determine if we should use parallel execution
    use_parallel = max_workers is not None and max_workers > 1 and total > 1

    if use_parallel:
        # Parallel execution using ProcessPoolExecutor
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
            # Fallback logic would be needed here, or just let it fail/raise
            # For now, if we can't get the file, parallel will likely fail anyway if we tried passing class
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
            for params in param_sets
        ]

        # Run in parallel
        with ProcessPoolExecutor(max_workers=max_workers) as executor:
            # Submit all tasks
            future_to_params = {
                executor.submit(_run_single_backtest, task): task[2] for task in tasks
            }

            # Process results as they complete
            for future in as_completed(future_to_params):
                params, opt_result, error = future.result()

                if opt_result:
                    all_results.append(opt_result)
                    completed += 1

                    # Track best
                    if opt_result.score > best_score_so_far:
                        best_score_so_far = opt_result.score
                        best_params_so_far = params

                    # Progress callback
                    if progress_callback:
                        progress_callback(
                            completed=completed,
                            total=total,
                            current_params=params,
                            best_score=best_score_so_far,
                            best_params=best_params_so_far,
                        )
                else:
                    logger.error(f"Failed for params {params}: {error}")
                    failed += 1

                if verbose and completed % max(1, total // 10) == 0:
                    logger.info(
                        f"Progress: {completed}/{total} ({completed / total * 100:.1f}%)"
                    )

    else:
        # Sequential execution (original code)
        for i, params in enumerate(param_sets):

            if verbose and (i + 1) % max(1, total // 10) == 0:
                logger.info(f"Progress: {i + 1}/{total} ({(i + 1) / total * 100:.1f}%)")

            try:
                # Create strategy with parameters
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

                # Calculate metrics
                result_metrics = result.summary()

                # Score
                score = scoring_func(result)

                # Store result
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
                        total=total,
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

    # Get best
    best = all_results[0] if all_results else None

    duration = time.time() - start_time

    summary = OptimizationSummary(
        best_params=best.parameters if best else {},
        best_score=best.score if best else 0.0,
        best_result=best.result if best else None,
        all_results=all_results,
        total_combinations=total,
        completed=completed,
        failed=failed,
        duration_seconds=duration,
    )

    if verbose:
        logger.success(f"Grid search complete in {duration:.2f}s")
        logger.info(f"Best params: {summary.best_params}")
        logger.info(f"Best score: {summary.best_score:.4f}")
        logger.info(f"Completed: {completed}/{total}, Failed: {failed}")

    return summary
