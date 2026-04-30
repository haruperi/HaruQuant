"""
Grid Search Optimization.

Exhaustive search over parameter space.
"""

import inspect
import time
from concurrent.futures import ProcessPoolExecutor, as_completed
from itertools import product
from typing import Any, Callable, Dict, List, Optional, Type

from backend.common.logger import logger
from backend.services.strategy import BaseStrategy

from ..execution import run_strategy_backtest, run_strategy_backtest_from_path
from ..result import OptimizationResult, OptimizationSummary
from ..scoring import sharpe_score

BacktestResult = Any


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
        result = run_strategy_backtest_from_path(
            strategy_path=strategy_path,
            class_name=strategy_class_name,
            data=data,
            symbol=symbol,
            params=params,
            initial_balance=initial_balance,
            engine_type=engine_type,
            position_size=0.1,
        )
        result_metrics = result.summary()
        score = scoring_func(result)
        opt_result = OptimizationResult(
            parameters=params, result=result, metrics=result_metrics, score=score
        )
        return (params, opt_result, None)

    except Exception as e:
        return (params, None, str(e))


def grid_search(  # noqa: C901
    strategy_class: Type[BaseStrategy],
    data,
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
    random_subset: Optional[int] = None,
) -> OptimizationSummary:
    """Grid search over parameter space."""
    if verbose:
        logger.info("Starting grid search optimization")
        if random_subset:
            logger.info(f"Randomly sampling {random_subset} combinations from grid")
        logger.info(f"Parameters: {param_grid}")

    param_names = list(param_grid.keys())
    param_values = list(param_grid.values())
    combinations = list(product(*param_values))

    param_sets = [dict(zip(param_names, combo)) for combo in combinations]
    if constraint:
        param_sets = [params for params in param_sets if constraint(params)]

    if random_subset and random_subset < len(param_sets):
        import random
        param_sets = random.sample(param_sets, random_subset)

    total = len(param_sets)

    if verbose:
        logger.info(f"Total combinations: {total}")

    start_time = time.time()
    all_results = []
    completed = 0
    failed = 0
    best_score_so_far = float("-inf")
    best_params_so_far = None
    use_parallel = max_workers is not None and max_workers > 1 and total > 1

    if use_parallel:
        if verbose:
            logger.info(f"Running parallel execution with {max_workers} workers")

        try:
            strategy_path = strategy_file_path or inspect.getfile(strategy_class)
            strategy_name = strategy_class.__name__
            strategy_info = (strategy_path, strategy_name)
        except Exception as e:
            logger.warning(
                f"Could not get strategy file path: {e}. Falling back to sequential execution."
            )
            raise RuntimeError(f"Cannot run parallel optimization: {e}")

        if not symbol:
            symbol = data.name if hasattr(data, "name") else "UNKNOWN"

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

        with ProcessPoolExecutor(max_workers=max_workers) as executor:
            future_to_params = {
                executor.submit(_run_single_backtest, task): task[3] for task in tasks
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
        if not symbol:
            symbol = data.name if hasattr(data, "name") else "UNKNOWN"

        for i, params in enumerate(param_sets):
            if verbose and (i + 1) % max(1, total // 10) == 0:
                logger.info(f"Progress: {i + 1}/{total} ({(i + 1) / total * 100:.1f}%)")

            try:
                result = run_strategy_backtest(
                    strategy_class=strategy_class,
                    data=data,
                    symbol=symbol,
                    params=params,
                    initial_balance=initial_balance,
                    engine_type=engine_type,
                    position_size=0.1,
                )
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

                if score > best_score_so_far:
                    best_score_so_far = score
                    best_params_so_far = params

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
