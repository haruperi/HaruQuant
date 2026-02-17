"""
Multitasking Usage Examples

Purpose:
- Demonstrate concurrent task execution using threads and processes
- Show task pools and execution control
- Illustrate parallel backtesting and optimization
- Examples for async trading operations

Key Concepts:
- @task decorator for async functions
- Thread vs process execution engines
- Task pools with configurable limits
- Wait for tasks completion
- Active task monitoring

Usage:
    python tests/usage/utils/usage_multitasking.py
"""

import sys
from pathlib import Path
import time

# Add project root to path
project_root = Path(__file__).parent.parent.parent.parent
sys.path.insert(0, str(project_root))

from apps.utils.multitasking import (
    task,
    createPool,
    set_max_threads,
    set_engine,
    wait_for_tasks,
    get_active_tasks,
    get_list_of_tasks,
    getPool,
)
from apps.utils.logger import logger


def example_01_basic_task():
    """Example 1: Basic async task execution."""
    logger.info("=" * 70)
    logger.info("EXAMPLE 1: Basic Async Task")
    logger.info("=" * 70)

    @task
    def slow_calculation(name, duration):
        """Simulate a slow calculation."""
        logger.info(f"Task '{name}' starting...")
        time.sleep(duration)
        result = duration * 2
        logger.info(f"Task '{name}' completed with result: {result}")
        return result

    logger.info("Starting async task...")
    task_handle = slow_calculation("Task1", 2)

    logger.info(f"Task started, handle: {task_handle}")
    logger.info("Main thread continues immediately...")

    # Wait for completion
    wait_for_tasks()
    logger.info("All tasks completed")


def example_02_multiple_tasks():
    """Example 2: Running multiple tasks concurrently."""
    logger.info("\n" + "=" * 70)
    logger.info("EXAMPLE 2: Multiple Concurrent Tasks")
    logger.info("=" * 70)

    @task
    def process_symbol(symbol, duration):
        """Simulate processing a trading symbol."""
        logger.info(f"Processing {symbol}...")
        time.sleep(duration)
        logger.info(f"Finished processing {symbol}")
        return f"{symbol}_processed"

    symbols = ["EURUSD", "GBPUSD", "USDJPY", "AUDUSD", "USDCAD"]

    logger.info(f"Starting to process {len(symbols)} symbols concurrently...")
    start_time = time.time()

    # Launch all tasks
    for symbol in symbols:
        process_symbol(symbol, 1)

    logger.info("All tasks launched")

    # Wait for all to complete
    wait_for_tasks()

    duration = time.time() - start_time
    logger.info(f"\nAll symbols processed in {duration:.2f} seconds")
    logger.info(f"Sequential would take ~{len(symbols)} seconds")


def example_03_thread_pool():
    """Example 3: Using thread pools with limits."""
    logger.info("\n" + "=" * 70)
    logger.info("EXAMPLE 3: Thread Pool with Limits")
    logger.info("=" * 70)

    # Create pool with max 3 concurrent threads
    createPool(name="LimitedPool", threads=3, engine="thread")

    @task
    def limited_task(task_id):
        """Task running in limited pool."""
        logger.info(f"Task {task_id} started")
        time.sleep(1)
        logger.info(f"Task {task_id} finished")
        return task_id

    logger.info("Starting 10 tasks with max 3 concurrent...")
    start_time = time.time()

    # Launch 10 tasks (only 3 will run at a time)
    for i in range(10):
        limited_task(i)

    wait_for_tasks()

    duration = time.time() - start_time
    logger.info(f"\n10 tasks completed in {duration:.2f} seconds")
    logger.info("Tasks ran in batches of 3")


def example_04_process_engine():
    """Example 4: Using process engine for CPU-bound tasks."""
    logger.info("\n" + "=" * 70)
    logger.info("EXAMPLE 4: Process Engine (CPU-bound)")
    logger.info("=" * 70)

    set_engine("process")
    createPool(name="ProcessPool", threads=4, engine="process")

    @task
    def cpu_intensive(n):
        """Simulate CPU-intensive calculation."""
        result = sum(i * i for i in range(n))
        return result

    logger.info("Running CPU-intensive tasks in separate processes...")
    start_time = time.time()

    # Launch tasks
    for i in range(4):
        cpu_intensive(1000000)

    wait_for_tasks()

    duration = time.time() - start_time
    logger.info(f"Completed in {duration:.2f} seconds using processes")

    # Reset to threads
    set_engine("thread")


def example_05_task_monitoring():
    """Example 5: Monitor active tasks."""
    logger.info("\n" + "=" * 70)
    logger.info("EXAMPLE 5: Task Monitoring")
    logger.info("=" * 70)

    createPool(name="MonitorPool", threads=5)

    @task
    def monitored_task(task_id, duration):
        """Task that can be monitored."""
        logger.info(f"Task {task_id} working for {duration}s...")
        time.sleep(duration)
        return task_id

    # Launch tasks with different durations
    logger.info("Launching tasks with varying durations...")
    for i in range(5):
        monitored_task(i, i + 1)  # 1s, 2s, 3s, 4s, 5s

    # Monitor while running
    time.sleep(0.5)  # Let tasks start
    for _ in range(10):
        active = get_active_tasks()
        total = get_list_of_tasks()
        logger.info(f"Active: {len(active)}, Total created: {len(total)}")
        time.sleep(1)
        if len(active) == 0:
            break

    wait_for_tasks()
    logger.info("All tasks completed")


def example_06_parallel_backtest():
    """Example 6: Parallel backtest simulation."""
    logger.info("\n" + "=" * 70)
    logger.info("EXAMPLE 6: Parallel Backtest Simulation")
    logger.info("=" * 70)

    createPool(name="BacktestPool", threads=4)

    @task
    def run_backtest(strategy_name, params):
        """Simulate running a backtest."""
        logger.info(f"Backtesting {strategy_name} with params: {params}")
        time.sleep(2)  # Simulate backtest time

        # Simulate results
        profit = params.get('fast_ma', 10) * params.get('slow_ma', 20) * 0.1

        logger.info(f"{strategy_name} completed - Profit: ${profit:.2f}")
        return {
            'strategy': strategy_name,
            'params': params,
            'profit': profit
        }

    # Test different parameter combinations
    param_sets = [
        {'fast_ma': 10, 'slow_ma': 20},
        {'fast_ma': 15, 'slow_ma': 30},
        {'fast_ma': 20, 'slow_ma': 40},
        {'fast_ma': 25, 'slow_ma': 50},
    ]

    logger.info(f"Running {len(param_sets)} backtests in parallel...")
    start_time = time.time()

    for i, params in enumerate(param_sets):
        run_backtest(f"MA_Strategy_{i}", params)

    wait_for_tasks()

    duration = time.time() - start_time
    logger.info(f"\nAll backtests completed in {duration:.2f} seconds")


def example_07_optimization_grid():
    """Example 7: Parallel parameter optimization."""
    logger.info("\n" + "=" * 70)
    logger.info("EXAMPLE 7: Parallel Parameter Optimization")
    logger.info("=" * 70)

    set_max_threads(8)
    createPool(name="OptimizationPool", threads=8)

    @task
    def optimize_params(param_set):
        """Test a parameter combination."""
        fast, slow = param_set
        # Simulate optimization
        score = (fast + slow) * 0.1
        return {'fast': fast, 'slow': slow, 'score': score}

    # Create parameter grid
    fast_values = [10, 15, 20, 25]
    slow_values = [30, 40, 50, 60]
    param_grid = [(f, s) for f in fast_values for s in slow_values]

    logger.info(f"Testing {len(param_grid)} parameter combinations...")
    start_time = time.time()

    for params in param_grid:
        optimize_params(params)

    wait_for_tasks()

    duration = time.time() - start_time
    logger.info(f"Optimization completed in {duration:.2f} seconds")
    logger.info(f"Tested {len(param_grid)} combinations with 8 parallel workers")


def example_08_pool_configuration():
    """Example 8: Different pool configurations."""
    logger.info("\n" + "=" * 70)
    logger.info("EXAMPLE 8: Pool Configuration")
    logger.info("=" * 70)

    # Create different pools for different task types
    createPool(name="FastTasks", threads=10, engine="thread")
    logger.info(f"FastTasks pool: {getPool('FastTasks')}")

    createPool(name="SlowTasks", threads=2, engine="thread")
    logger.info(f"SlowTasks pool: {getPool('SlowTasks')}")

    createPool(name="CPUTasks", threads=4, engine="process")
    logger.info(f"CPUTasks pool: {getPool('CPUTasks')}")

    logger.info("\nPools configured for different workload types")


def example_09_data_loading():
    """Example 9: Parallel data loading."""
    logger.info("\n" + "=" * 70)
    logger.info("EXAMPLE 9: Parallel Data Loading")
    logger.info("=" * 70)

    createPool(name="DataLoader", threads=5)

    @task
    def load_symbol_data(symbol):
        """Simulate loading symbol data."""
        logger.info(f"Loading data for {symbol}...")
        time.sleep(1)  # Simulate data load
        logger.info(f"Loaded {symbol}")
        return f"{symbol}_data"

    symbols = ["EURUSD", "GBPUSD", "USDJPY", "AUDUSD", "NZDUSD",
               "USDCAD", "USDCHF", "EURGBP", "EURJPY", "GBPJPY"]

    logger.info(f"Loading data for {len(symbols)} symbols in parallel...")
    start_time = time.time()

    for symbol in symbols:
        load_symbol_data(symbol)

    wait_for_tasks()

    duration = time.time() - start_time
    logger.info(f"All data loaded in {duration:.2f} seconds")


def example_10_error_handling():
    """Example 10: Error handling in tasks."""
    logger.info("\n" + "=" * 70)
    logger.info("EXAMPLE 10: Error Handling in Tasks")
    logger.info("=" * 70)

    createPool(name="ErrorPool", threads=3)

    @task
    def potentially_failing_task(task_id):
        """Task that might fail."""
        logger.info(f"Task {task_id} starting...")
        time.sleep(0.5)

        if task_id == 3:
            logger.error(f"Task {task_id} encountered an error!")
            raise ValueError(f"Task {task_id} failed intentionally")

        logger.info(f"Task {task_id} completed successfully")
        return task_id

    logger.info("Starting tasks (one will fail)...")

    for i in range(5):
        potentially_failing_task(i)

    wait_for_tasks()

    logger.info("\nNote: Failed tasks are logged but don't stop other tasks")
    logger.info("Implement proper error handling within task functions")


def main():
    """Run all multitasking examples."""
    logger.info("\n" + "=" * 80)
    logger.info("MULTITASKING - COMPREHENSIVE USAGE EXAMPLES")
    logger.info("=" * 80)

    example_01_basic_task()
    example_02_multiple_tasks()
    example_03_thread_pool()
    example_04_process_engine()
    example_05_task_monitoring()
    example_06_parallel_backtest()
    example_07_optimization_grid()
    example_08_pool_configuration()
    example_09_data_loading()
    example_10_error_handling()

    logger.info("\n" + "=" * 80)
    logger.info("ALL EXAMPLES COMPLETED")
    logger.info("=" * 80)

    logger.info("\nKEY TAKEAWAYS:")
    logger.info("1. Use @task decorator to make functions run asynchronously")
    logger.info("2. createPool() to configure thread/process pools")
    logger.info("3. wait_for_tasks() to wait for all tasks to complete")
    logger.info("4. Threads for I/O-bound tasks (API calls, data loading)")
    logger.info("5. Processes for CPU-bound tasks (backtesting, optimization)")
    logger.info("6. Pool limits prevent resource exhaustion")
    logger.info("7. Monitor active tasks with get_active_tasks()")


if __name__ == "__main__":
    main()

