"""
Random Search Optimization.

Randomly samples parameter combinations.
More efficient than grid search for large parameter spaces.
"""

import inspect
import time
from concurrent.futures import ProcessPoolExecutor, as_completed
from typing import Any, Callable, Dict, Optional, Tuple, Type

import numpy as np

from services.utils.logger import logger
from services.strategy import BaseStrategy

from ..execution import run_strategy_backtest, run_strategy_backtest_from_path
from ..result import OptimizationResult, OptimizationSummary
from ..scoring import sharpe_score

BacktestResult = Any


def _run_single_random_backtest(args):
    """
    Run a single backtest (pickleable for multiprocessing).
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


def random_search(  # noqa: C901
    strategy_class: Type[BaseStrategy],
    data,
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
    """Random search over parameter space."""
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

    all_param_combinations = []
    for _i in range(n_iter):
        params = {}
        for param_name, (min_val, max_val) in param_distributions.items():
            if isinstance(min_val, int) and isinstance(max_val, int):
                params[param_name] = np.random.randint(min_val, max_val + 1)
            else:
                params[param_name] = np.random.uniform(min_val, max_val)
        all_param_combinations.append(params)

    use_parallel = max_workers is not None and max_workers > 1 and n_iter > 1

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
            for params in all_param_combinations
        ]

        with ProcessPoolExecutor(max_workers=max_workers) as executor:
            future_to_params = {
                executor.submit(_run_single_random_backtest, task): task[3]
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
        if not symbol:
            symbol = data.name if hasattr(data, "name") else "UNKNOWN"

        for i, params in enumerate(all_param_combinations):
            if verbose and (i + 1) % max(1, n_iter // 10) == 0:
                logger.info(
                    f"Progress: {i + 1}/{n_iter} ({(i + 1) / n_iter * 100:.1f}%)"
                )

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
                        total=n_iter,
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
