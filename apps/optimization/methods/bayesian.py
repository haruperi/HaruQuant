"""
Bayesian Optimization.

Uses Gaussian Process-based optimization with Expected Improvement acquisition.
More efficient than random search, intelligently explores parameter space.
"""

import time
from typing import Any, Callable, Dict, Optional, Tuple, Type

from backend.common.logger import logger
from backend.services.strategy import BaseStrategy

from ..execution import run_strategy_backtest
from ..result import OptimizationResult, OptimizationSummary
from ..scoring import sharpe_score

BacktestResult = Any


def bayesian_optimization(  # noqa: C901
    strategy_class: Type[BaseStrategy],
    data,
    param_space: Dict[str, Tuple[float, float]],
    param_types: Optional[Dict[str, str]] = None,
    n_iterations: int = 50,
    n_initial_points: int = 10,
    initial_balance: float = 10000.0,
    scoring_func: Callable[[BacktestResult], float] = sharpe_score,
    engine_type: str = "vectorized",
    max_workers: Optional[int] = None,
    random_state: Optional[int] = None,
    verbose: bool = True,
    progress_callback: Optional[Callable] = None,
    symbol: Optional[str] = None,
) -> OptimizationSummary:
    """Bayesian optimization using Gaussian Processes."""
    _ = max_workers
    try:
        from skopt import gp_minimize
        from skopt.space import Integer, Real
    except ImportError:
        raise ImportError(
            "scikit-optimize is required for Bayesian optimization. "
            "Install it with: pip install scikit-optimize==0.9.0"
        )

    if verbose:
        logger.info(f"Starting Bayesian optimization: {n_iterations} iterations")
        logger.info(f"Parameter space: {param_space}")
        logger.info(f"Initial random points: {n_initial_points}")

    if param_types is None:
        param_types = {}
        for param_name, (min_val, max_val) in param_space.items():
            param_types[param_name] = "int" if isinstance(min_val, int) and isinstance(max_val, int) else "float"

    param_names = list(param_space.keys())
    dimensions = []
    for param_name in param_names:
        min_val, max_val = param_space[param_name]
        if param_types.get(param_name) == "int":
            dimensions.append(Integer(min_val, max_val, name=param_name))
        else:
            dimensions.append(Real(min_val, max_val, name=param_name))

    all_results = []
    best_score_so_far = float("-inf")
    best_params_so_far = None
    completed = 0
    start_time = time.time()

    if not symbol:
        symbol = data.name if hasattr(data, "name") else "UNKNOWN"

    def objective(param_values):
        nonlocal completed, best_score_so_far, best_params_so_far

        params = {}
        for i, param_name in enumerate(param_names):
            value = param_values[i]
            if param_types.get(param_name) == "int":
                value = int(round(value))
            params[param_name] = value

        if verbose and (completed + 1) % max(1, n_iterations // 10) == 0:
            logger.info(
                f"Progress: {completed + 1}/{n_iterations} ({(completed + 1) / n_iterations * 100:.1f}%)"
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
                parameters=params.copy(),
                result=result,
                metrics=result_metrics,
                score=score,
            )
            all_results.append(opt_result)

            if score > best_score_so_far:
                best_score_so_far = score
                best_params_so_far = params.copy()

            if progress_callback:
                progress_callback(
                    completed=completed + 1,
                    total=n_iterations,
                    current_params=params,
                    best_score=best_score_so_far,
                    best_params=best_params_so_far,
                )

            completed += 1
            return -score

        except Exception as e:
            logger.error(f"Failed for params {params}: {e}")
            completed += 1
            return 1e10

    if verbose:
        logger.info("Running Gaussian Process optimization...")

    _ = gp_minimize(
        objective,
        dimensions,
        n_calls=n_iterations,
        n_initial_points=n_initial_points,
        random_state=random_state,
        verbose=False,
        n_jobs=1,
    )

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
        total_combinations=n_iterations,
        completed=completed,
        failed=max(0, n_iterations - completed),
        duration_seconds=duration,
    )

    if verbose:
        logger.success(f"Bayesian optimization complete in {duration:.2f}s")
        logger.info(f"Best params: {summary.best_params}")
        logger.info(f"Best score: {summary.best_score:.4f}")
        logger.info(f"Completed: {completed}/{n_iterations}")

    return summary
