"""
Parallel Backtesting Module.

Provides parallel execution capabilities for running multiple backtests
simultaneously across CPU cores. Ideal for parameter sweeps, portfolio
backtesting, and optimization tasks.

Performance: Linear speedup with CPU cores (6-7x on 8 cores expected).
"""

import multiprocessing as mp
from concurrent.futures import ProcessPoolExecutor, as_completed
from dataclasses import dataclass
from typing import Any, Dict, List, Optional, Type

import pandas as pd

try:
    from tqdm import tqdm

    HAS_TQDM = True
except ImportError:
    HAS_TQDM = False

    # Fallback: simple identity function
    def tqdm(iterable, **kwargs):
        """Return the iterable unchanged when tqdm is unavailable."""
        return iterable


from apps.logger import logger
from apps.strategy import BaseStrategy

from .engine.base import BaseEngine
from .engine.event_driven import EventDrivenEngine
from .engine.vectorized import VectorizedEngine
from .result import BacktestResult


@dataclass
class BacktestTask:
    """
    Represents a single backtest task to be executed.

    Attributes:
        task_id: Unique identifier for this task
        strategy_class: Strategy class to instantiate
        strategy_params: Parameters to pass to strategy constructor
        data: OHLCV DataFrame for backtesting
        engine_type: "event_driven" or "vectorized"
        engine_config: Configuration dict for engine
    """

    task_id: str
    strategy_class: Type[BaseStrategy]
    strategy_params: Dict[str, Any]
    data: pd.DataFrame
    engine_type: str = "event_driven"
    engine_config: Optional[Dict[str, Any]] = None


@dataclass
class ParallelResult:
    """
    Result from parallel backtest execution.

    Attributes:
        task_id: Identifier matching the BacktestTask
        result: BacktestResult from the backtest
        success: Whether the backtest completed successfully
        error: Error message if failed
        execution_time: Time taken to execute (seconds)
    """

    task_id: str
    result: Optional[BacktestResult]
    success: bool
    error: Optional[str] = None
    execution_time: float = 0.0


def _run_single_backtest(task: BacktestTask) -> ParallelResult:
    """
    Execute a single backtest task.

    This function is designed to be pickled and sent to worker processes.

    Args:
        task: BacktestTask to execute

    Returns:
        ParallelResult with backtest outcome
    """
    import time

    start_time = time.time()

    try:
        # Instantiate strategy
        # BaseStrategy expects params as a dict, not unpacked kwargs
        strategy = task.strategy_class(params=task.strategy_params)

        # Select engine type
        engine_config = task.engine_config or {}

        engine: BaseEngine
        if task.engine_type == "vectorized":
            engine = VectorizedEngine(
                strategy=strategy, data=task.data, **engine_config
            )
        else:  # event_driven
            engine = EventDrivenEngine(
                strategy=strategy, data=task.data, **engine_config
            )

        # Run backtest
        result = engine.run()

        execution_time = time.time() - start_time

        return ParallelResult(
            task_id=task.task_id,
            result=result,
            success=True,
            execution_time=execution_time,
        )

    except Exception as e:
        execution_time = time.time() - start_time
        logger.error(f"Backtest task {task.task_id} failed: {str(e)}")

        return ParallelResult(
            task_id=task.task_id,
            result=None,
            success=False,
            error=str(e),
            execution_time=execution_time,
        )


class ParallelBacktester:
    """
    Parallel backtest executor using multiprocessing.

    Enables running multiple backtests simultaneously across CPU cores.
    Ideal for parameter optimization, portfolio backtesting, and batch processing.

    Example:
        >>> parallel = ParallelBacktester(max_workers=4)
        >>> tasks = [
        ...     BacktestTask(
        ...         task_id=f"task_{i}",
        ...         strategy_class=MyStrategy,
        ...         strategy_params={"param": value},
        ...         data=data
        ...     )
        ...     for i, value in enumerate(param_values)
        ... ]
        >>> results = parallel.run_batch(tasks)
    """

    def __init__(self, max_workers: Optional[int] = None):
        """
        Initialize parallel backtester.

        Args:
            max_workers: Maximum number of worker processes.
                        If None, uses CPU count.
        """
        self.max_workers = max_workers or mp.cpu_count()
        logger.info(f"ParallelBacktester initialized with {self.max_workers} workers")

    def run_batch(
        self, tasks: List[BacktestTask], show_progress: bool = True
    ) -> List[ParallelResult]:
        """
        Run multiple backtest tasks in parallel.

        Args:
            tasks: List of BacktestTask instances to execute
            show_progress: Whether to show progress bar

        Returns:
            List of ParallelResult instances (same order as tasks)
        """
        if not tasks:
            logger.warning("No tasks provided to run_batch")
            return []

        logger.info(f"Starting batch execution of {len(tasks)} tasks")

        results_dict: Dict[str, ParallelResult] = {}

        with ProcessPoolExecutor(max_workers=self.max_workers) as executor:
            # Submit all tasks
            futures = {
                executor.submit(_run_single_backtest, task): task.task_id
                for task in tasks
            }

            # Collect results with progress bar
            iterator = as_completed(futures)
            if show_progress:
                iterator = tqdm(iterator, total=len(tasks), desc="Running backtests")

            for future in iterator:
                task_id = futures[future]
                try:
                    result = future.result()
                    results_dict[task_id] = result
                except Exception as e:
                    logger.error(f"Task {task_id} raised exception: {str(e)}")
                    results_dict[task_id] = ParallelResult(
                        task_id=task_id, result=None, success=False, error=str(e)
                    )

        # Return results in original task order
        results = [results_dict[task.task_id] for task in tasks]

        # Log summary
        successful = sum(1 for r in results if r.success)
        failed = len(results) - successful
        total_time = sum(r.execution_time for r in results)
        avg_time = total_time / len(results) if results else 0

        logger.info(
            f"Batch complete: {successful} successful, {failed} failed, "
            f"avg time: {avg_time:.2f}s"
        )

        return results

    def run_parameter_sweep(
        self,
        strategy_class: Type[BaseStrategy],
        data: pd.DataFrame,
        parameter_grid: Dict[str, List[Any]],
        engine_type: str = "vectorized",
        engine_config: Optional[Dict[str, Any]] = None,
        show_progress: bool = True,
    ) -> List[ParallelResult]:
        """
        Run parameter sweep optimization.

        Tests all combinations of parameters in the grid.

        Args:
            strategy_class: Strategy class to optimize
            data: OHLCV data for backtesting
            parameter_grid: Dict mapping parameter names to lists of values
            engine_type: "event_driven" or "vectorized"
            engine_config: Configuration for engine
            show_progress: Whether to show progress bar

        Returns:
            List of ParallelResult instances

        Example:
            >>> results = parallel.run_parameter_sweep(
            ...     strategy_class=MovingAverageCrossover,
            ...     data=data,
            ...     parameter_grid={
            ...         "fast_period": [10, 20, 30],
            ...         "slow_period": [50, 100, 200]
            ...     }
            ... )
        """
        from itertools import product

        # Generate all parameter combinations
        param_names = list(parameter_grid.keys())
        param_values = list(parameter_grid.values())
        combinations = list(product(*param_values))

        logger.info(
            f"Parameter sweep: {len(combinations)} combinations of " f"{param_names}"
        )

        # Create tasks
        tasks = []
        for i, combo in enumerate(combinations):
            params = dict(zip(param_names, combo))
            task = BacktestTask(
                task_id=f"sweep_{i}_{'-'.join(f'{k}={v}' for k, v in params.items())}",
                strategy_class=strategy_class,
                strategy_params=params,
                data=data,
                engine_type=engine_type,
                engine_config=engine_config,
            )
            tasks.append(task)

        # Execute in parallel
        return self.run_batch(tasks, show_progress=show_progress)

    def run_portfolio(
        self,
        strategy_class: Type[BaseStrategy],
        symbol_data: Dict[str, pd.DataFrame],
        strategy_params: Optional[Dict[str, Any]] = None,
        engine_type: str = "event_driven",
        engine_config: Optional[Dict[str, Any]] = None,
        show_progress: bool = True,
    ) -> Dict[str, ParallelResult]:
        """
        Run backtests for multiple symbols in parallel.

        Args:
            strategy_class: Strategy class to use
            symbol_data: Dict mapping symbol names to OHLCV DataFrames
            strategy_params: Parameters for strategy (same for all symbols)
            engine_type: "event_driven" or "vectorized"
            engine_config: Configuration for engine
            show_progress: Whether to show progress bar

        Returns:
            Dict mapping symbol names to ParallelResult instances

        Example:
            >>> results = parallel.run_portfolio(
            ...     strategy_class=MyStrategy,
            ...     symbol_data={
            ...         "EURUSD": eurusd_data,
            ...         "GBPUSD": gbpusd_data,
            ...         "USDJPY": usdjpy_data
            ...     }
            ... )
        """
        strategy_params = strategy_params or {}

        logger.info(f"Portfolio backtest: {len(symbol_data)} symbols")

        # Create tasks
        tasks = []
        for symbol, data in symbol_data.items():
            # Add symbol to strategy params
            params = strategy_params.copy()
            params["symbol"] = symbol

            task = BacktestTask(
                task_id=f"portfolio_{symbol}",
                strategy_class=strategy_class,
                strategy_params=params,
                data=data,
                engine_type=engine_type,
                engine_config=engine_config,
            )
            tasks.append(task)

        # Execute in parallel
        results = self.run_batch(tasks, show_progress=show_progress)

        # Return as dict keyed by symbol
        return dict(zip(symbol_data.keys(), results))

    def get_best_parameters(
        self, results: List[ParallelResult], metric: str = "total_return_percent"
    ) -> Optional[Dict[str, Any]]:
        """
        Find best parameters from sweep results.

        Args:
            results: Results from run_parameter_sweep()
            metric: Metric to optimize (e.g., "total_return_percent", "sharpe_ratio")

        Returns:
            Dict of best parameters, or None if no successful results
        """
        successful = [r for r in results if r.success and r.result is not None]

        if not successful:
            logger.warning("No successful results to analyze")
            return None

        # Find best result
        best = max(successful, key=lambda r: getattr(r.result, metric, float("-inf")))

        # Extract parameters from task_id
        # Format: "sweep_0_param1=value1-param2=value2"
        task_id = best.task_id
        param_str = task_id.split("_", 2)[2]  # Remove "sweep_N_"

        params: Dict[str, Any] = {}
        for pair in param_str.split("-"):
            key, value = pair.split("=")
            # Try to convert to appropriate type
            try:
                params[key] = int(value)
            except ValueError:
                try:
                    params[key] = float(value)
                except ValueError:
                    params[key] = value

        logger.info(
            f"Best parameters: {params} ({metric}={getattr(best.result, metric):.2f})"
        )

        return params
