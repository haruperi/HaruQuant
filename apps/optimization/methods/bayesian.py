"""
Bayesian Optimization.

Uses Gaussian Process-based optimization with Expected Improvement acquisition.
More efficient than random search, intelligently explores parameter space.
"""

import time
from typing import Any, Callable, Dict, Optional, Tuple, Type

from apps.utils.logger import logger
from apps.simulation.data import AccountInfoSimulator, SymbolInfoSimulator

# from apps.backtest.result import BacktestResult
from apps.simulation.simulator import TradeSimulator
from apps.strategy import BaseStrategy

from ..result import OptimizationResult, OptimizationSummary
from ..scoring import sharpe_score

BacktestResult = Any


def bayesian_optimization(  # noqa: C901
    strategy_class: Type[BaseStrategy],
    data,  # pd.DataFrame
    param_space: Dict[str, Tuple[float, float]],
    param_types: Optional[Dict[str, str]] = None,
    n_iterations: int = 50,
    n_initial_points: int = 10,
    initial_balance: float = 10000.0,
    scoring_func: Callable[[BacktestResult], float] = sharpe_score,
    engine_type: str = "vectorized",
    max_workers: Optional[int] = None,  # Not used (Bayesian is inherently sequential)
    random_state: Optional[int] = None,
    verbose: bool = True,
    progress_callback: Optional[Callable] = None,
    symbol: Optional[str] = None,
) -> OptimizationSummary:
    """
    Bayesian optimization using Gaussian Processes.

    Uses scikit-optimize to intelligently explore parameter space.
    More efficient than grid/random search for expensive objective functions.

    Args:
        strategy_class: Strategy class to optimize
        data: OHLCV DataFrame
        param_space: Dict of param names to (min, max) tuples
        param_types: Dict of param names to "int" or "float" (default: infer from values)
        n_iterations: Total number of evaluations
        n_initial_points: Number of random points before GP optimization starts
        initial_balance: Starting balance
        scoring_func: Function to score results
        engine_type: "vectorized" or "event_driven"
        random_state: Random seed for reproducibility
        verbose: Print progress
        progress_callback: Optional callback(completed, total, current_params, best_score, best_params)

    Returns:
        OptimizationSummary with results

    Example:
        >>> param_space = {
        ...     'ema_fast': (5, 30),
        ...     'ema_slow': (30, 150),
        ...     'atr_period': (10, 20)
        ... }
        >>> param_types = {'ema_fast': 'int', 'ema_slow': 'int', 'atr_period': 'int'}
        >>> summary = bayesian_optimization(
        ...     TrendFollowingStrategy,
        ...     data,
        ...     param_space,
        ...     param_types=param_types,
        ...     n_iterations=50
        ... )
    """
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

    # Infer param types if not provided
    if param_types is None:
        param_types = {}
        for param_name, (min_val, max_val) in param_space.items():
            if isinstance(min_val, int) and isinstance(max_val, int):
                param_types[param_name] = "int"
            else:
                param_types[param_name] = "float"

    # Create search space for scikit-optimize
    param_names = list(param_space.keys())
    dimensions = []
    for param_name in param_names:
        min_val, max_val = param_space[param_name]
        if param_types.get(param_name) == "int":
            dimensions.append(Integer(min_val, max_val, name=param_name))
        else:
            dimensions.append(Real(min_val, max_val, name=param_name))

    # Storage for all results
    all_results = []
    best_score_so_far = float("-inf")
    best_params_so_far = None
    completed = 0

    start_time = time.time()

    # Get symbol (prefer explicit parameter, fallback to data.name)
    # Note: data.name may not be preserved during pickling for multiprocessing
    if not symbol:
        symbol = data.name if hasattr(data, "name") else "UNKNOWN"

    # Objective function to minimize (we negate score since gp_minimize minimizes)
    def objective(param_values):
        nonlocal completed, best_score_so_far, best_params_so_far

        # Convert to parameter dict
        params = {}
        for i, param_name in enumerate(param_names):
            value = param_values[i]
            # Convert to int if needed
            if param_types.get(param_name) == "int":
                value = int(round(value))
            params[param_name] = value

        if verbose and (completed + 1) % max(1, n_iterations // 10) == 0:
            logger.info(
                f"Progress: {completed + 1}/{n_iterations} ({(completed + 1) / n_iterations * 100:.1f}%)"
            )

        try:
            # Create strategy
            full_params = params.copy()
            full_params["symbol"] = symbol
            strategy = strategy_class(params=full_params)

            # Initialize strategy
            if hasattr(strategy, "on_init"):
                strategy.on_init()

            # Calculate signals if strategy has on_bar method
            data_copy = data.copy()
            if hasattr(strategy, "on_bar"):
                data_copy = strategy.on_bar(data_copy)

            # Setup simulator components
            account_info = AccountInfoSimulator(
                balance=initial_balance,
                equity=initial_balance,
                margin_free=initial_balance,
            )
            symbol_info = SymbolInfoSimulator.from_mt5_symbol(symbol)
            symbol_info.symbol = symbol

            # Create simulator
            simulator = TradeSimulator(
                simulator_name=f"Optimization_{symbol}",
                mt5_client=None,
                account_info=account_info,
                symbols={symbol: symbol_info},
            )

            # Normalize engine_type
            sim_engine_type = engine_type.lower().replace("-", "_")
            if sim_engine_type == "vectorized":
                sim_engine_type = "vectorised"

            # Run simulation
            simulator.run(
                data=data_copy,
                strategy=strategy,
                symbol=symbol,
                volume=0.1,
                verbose=False,
                save_db=False,
                engine_type=sim_engine_type,
            )

            # Get results from simulator
            from apps.simulation.utils import calculate_metrics_from_simulator

            result = calculate_metrics_from_simulator(simulator)

            # Metrics and score
            result_metrics = result.summary()
            score = scoring_func(result)

            # Store result
            opt_result = OptimizationResult(
                parameters=params.copy(),
                result=result,
                metrics=result_metrics,
                score=score,
            )
            all_results.append(opt_result)

            # Track best
            if score > best_score_so_far:
                best_score_so_far = score
                best_params_so_far = params.copy()

            # Progress callback
            if progress_callback:
                progress_callback(
                    completed=completed + 1,
                    total=n_iterations,
                    current_params=params,
                    best_score=best_score_so_far,
                    best_params=best_params_so_far,
                )

            completed += 1

            # Return negative score (for minimization)
            return -score

        except Exception as e:
            logger.error(f"Failed for params {params}: {e}")
            completed += 1
            # Return a bad score so optimizer avoids this region
            return 1e10

    # Run Bayesian optimization
    if verbose:
        logger.info("Running Gaussian Process optimization...")

    _ = gp_minimize(
        objective,
        dimensions,
        n_calls=n_iterations,
        n_initial_points=n_initial_points,
        random_state=random_state,
        verbose=False,  # We handle our own logging
        n_jobs=1,  # Single-threaded (GP fitting is parallelized internally)
    )

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
        total_combinations=n_iterations,
        completed=completed,
        failed=n_iterations - completed,
        duration_seconds=duration,
    )

    if verbose:
        logger.success(f"Bayesian optimization complete in {duration:.2f}s")
        logger.info(f"Best params: {summary.best_params}")
        logger.info(f"Best score: {summary.best_score:.4f}")
        logger.info(f"Completed: {completed}/{n_iterations}")

    return summary

