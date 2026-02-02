"""
Parallel Backtest Execution Example.

Demonstrates the use of ParallelBacktester for:
1. Parameter sweep optimization
2. Multi-symbol portfolio backtesting
3. Performance comparison (serial vs parallel)

Phase 4.1: Parallel Backtesting Support
"""

import sys
from pathlib import Path

# Add project root to Python path
project_root = Path(__file__).parent.parent.parent.parent
sys.path.insert(0, str(project_root))

import time
from pathlib import Path
from datetime import datetime, timedelta

import pandas as pd

from apps.backtest.cache import ResultCache, compute_data_hash
from apps.backtest.data_loader import MemoryMappedDataLoader
from apps.backtest.parallel import BacktestTask, ParallelBacktester
from apps.mt5.client import MT5Client
from apps.sqlite.users import UserManager
from apps.strategy import BaseStrategy


# ============================================================================
# Helper Functions
# ============================================================================


def get_mt5_client():
    """Get a connected MT5 client with credentials."""
    creds = UserManager().get_mt5_credentials()
    client = MT5Client(
        login=creds["login"],
        password=creds["password"],
        server=creds["server"],
        path=creds["path"]
    )
    return client


def load_mt5_data(symbol: str, timeframe: str, bars: int) -> pd.DataFrame:
    """Load historical data from MT5."""
    date_to = datetime.now()
    # Estimate date_from based on bars (rough approximation)
    if timeframe == "M1":
        date_from = date_to - timedelta(minutes=bars * 2)  # 2x buffer for weekends
    elif timeframe == "H1":
        date_from = date_to - timedelta(hours=bars * 2)
    else:
        date_from = date_to - timedelta(days=bars)
    
    with get_mt5_client() as client:
        if not client.is_connected():
            raise ConnectionError("Failed to connect to MT5")
        
        df = client.get_bars(
            symbol=symbol,
            timeframe=timeframe,
            date_from=date_from,
            date_to=date_to
        )
        
        if df.empty:
            raise ValueError(f"No data retrieved from MT5 for {symbol}")
        
        # Get the last N bars
        return df.tail(bars).copy()


# ============================================================================
# Example Strategy for Testing
# ============================================================================


class MovingAverageCrossover(BaseStrategy):
    """
    Simple MA crossover strategy for testing parallel execution.
    """

    def __init__(self, params: dict = None):
        super().__init__(params=params)
        
        # Extract parameters from params dict
        self.fast_period = self.params.get("fast_period", 10)
        self.slow_period = self.params.get("slow_period", 20)

    def on_init(self):
        """Initialize strategy (required abstract method)."""
        pass

    def on_bar(self, data: pd.DataFrame) -> pd.DataFrame:
        """Calculate indicators and build signal columns."""
        data = self.generate_signals(data)

        data["entry_signal"] = 0
        data.loc[data["entry_long"], "entry_signal"] = 1
        data.loc[data["entry_short"], "entry_signal"] = -1

        data["exit_signal"] = 0
        data.loc[data["exit_long"], "exit_signal"] = 1
        data.loc[data["exit_short"], "exit_signal"] = -1

        data["pending_signal"] = 0
        data["cancel_pending_signal"] = 0
        data["price"] = data["close"]

        return data

    def generate_signals(self, data: pd.DataFrame) -> pd.DataFrame:
        """Generate MA crossover signals."""
        # Calculate MAs
        data["fast_ma"] = data["close"].rolling(window=self.fast_period).mean()
        data["slow_ma"] = data["close"].rolling(window=self.slow_period).mean()

        # Generate signals
        data["entry_long"] = (data["fast_ma"] > data["slow_ma"]) & (
            data["fast_ma"].shift(1) <= data["slow_ma"].shift(1)
        )
        data["entry_short"] = (data["fast_ma"] < data["slow_ma"]) & (
            data["fast_ma"].shift(1) >= data["slow_ma"].shift(1)
        )
        data["exit_long"] = data["entry_short"]
        data["exit_short"] = data["entry_long"]

        return data


# ============================================================================
# Example 1: Parameter Sweep Optimization
# ============================================================================


def example_parameter_sweep():
    """
    Run parameter sweep to find optimal MA periods.
    """
    print("\n" + "=" * 70)
    print("Example 1: Parameter Sweep Optimization")
    print("=" * 70)

    # Load data
    data = load_mt5_data("EURUSD", "H1", bars=5000)

    # Define parameter grid
    parameter_grid = {
        "symbol": ["EURUSD"],
        "fast_period": [5, 10, 15, 20],
        "slow_period": [30, 50, 100, 200],
    }

    # Run parallel parameter sweep
    parallel = ParallelBacktester(max_workers=4)

    print(f"\nRunning parameter sweep with {parallel.max_workers} workers...")
    start_time = time.time()

    results = parallel.run_parameter_sweep(
        strategy_class=MovingAverageCrossover,
        data=data,
        parameter_grid=parameter_grid,
        engine_type="vectorized",  # Use fast vectorized engine
        engine_config={
            "initial_balance": 10000,
            "commission": 0.0,
            "slippage_points": 0.0001,
        },
    )

    elapsed = time.time() - start_time

    # Analyze results
    successful = [r for r in results if r.success]
    print(f"\nCompleted {len(successful)}/{len(results)} backtests in {elapsed:.2f}s")
    print(f"Average time per backtest: {elapsed/len(results):.2f}s")

    # Find best parameters
    best_params = parallel.get_best_parameters(results, metric="total_return_pct")
    print(f"\nBest parameters: {best_params}")

    # Show top 5 results
    print("\nTop 5 Results:")
    print("-" * 70)
    successful.sort(
        key=lambda r: r.result.total_return_pct if r.result else 0, reverse=True
    )

    for i, result in enumerate(successful[:5], 1):
        if result.result:
            print(
                f"{i}. {result.task_id}: "
                f"Return={result.result.total_return_pct:.2f}%, "
                f"Trades={result.result.total_trades}, "
                f"Sharpe={result.result.sharpe_ratio:.2f}"
            )


# ============================================================================
# Example 2: Multi-Symbol Portfolio Backtesting
# ============================================================================


def example_portfolio_backtest():
    """
    Run backtests on multiple symbols in parallel.
    """
    print("\n" + "=" * 70)
    print("Example 2: Multi-Symbol Portfolio Backtesting")
    print("=" * 70)

    # Load data for multiple symbols
    symbols = ["EURUSD", "GBPUSD", "USDJPY"]

    symbol_data = {}
    for symbol in symbols:
        print(f"Loading data for {symbol}...")
        symbol_data[symbol] = load_mt5_data(symbol, "H1", bars=2000)

    # Run portfolio backtest
    parallel = ParallelBacktester(max_workers=3)

    print(f"\nRunning portfolio backtest with {parallel.max_workers} workers...")
    start_time = time.time()

    results = parallel.run_portfolio(
        strategy_class=MovingAverageCrossover,
        symbol_data=symbol_data,
        strategy_params={"fast_period": 10, "slow_period": 50},
        engine_type="event_driven",  # Use accurate event-driven engine
        engine_config={
            "initial_balance": 10000,
            "commission": 0.0,
            "slippage_points": 0.0001,
        },
    )

    elapsed = time.time() - start_time

    # Display results
    print(f"\nCompleted portfolio backtest in {elapsed:.2f}s")
    print("\nResults by Symbol:")
    print("-" * 70)

    total_return = 0
    for symbol, result in results.items():
        if result.success and result.result:
            r = result.result
            print(
                f"{symbol:8} | Return: {r.total_return_pct:7.2f}% | "
                f"Trades: {r.total_trades:3} | Sharpe: {r.sharpe_ratio:5.2f} | "
                f"Win Rate: {r.win_rate:5.1f}%"
            )
            total_return += r.total_return_pct
        else:
            print(f"{symbol:8} | FAILED: {result.error}")

    print("-" * 70)
    print(f"Average Return: {total_return/len(symbols):.2f}%")


# ============================================================================
# Example 3: Result Caching
# ============================================================================


def example_result_caching():
    """
    Demonstrate result caching for fast reload.
    """
    print("\n" + "=" * 70)
    print("Example 3: Result Caching")
    print("=" * 70)

    # Load data
    data = load_mt5_data("EURUSD", "H1", bars=2000)
    data_hash = compute_data_hash(data)

    # Initialize cache
    cache = ResultCache(max_size_mb=100, max_age_days=7)

    # Strategy parameters
    params = {"symbol": "EURUSD", "fast_period": 10, "slow_period": 50}

    # Try to get cached result
    print("\nAttempting to load cached result...")
    cached_result = cache.get(
        strategy_name="MovingAverageCrossover",
        symbol="EURUSD",
        params=params,
        data_hash=data_hash,
    )

    if cached_result:
        print("Cache hit! Loaded result from cache.")
        print(f"  Return: {cached_result.total_return_pct:.2f}%")
        print(f"  Trades: {cached_result.total_trades}")
    else:
        print("Cache miss. Running backtest...")

        # Run backtest
        from apps.backtest.engine.event_driven import EventDrivenEngine

        strategy = MovingAverageCrossover(params=params)
        engine = EventDrivenEngine(
            strategy=strategy, data=data, initial_balance=10000
        )

        start_time = time.time()
        result = engine.run()
        elapsed = time.time() - start_time

        print(f"  Backtest completed in {elapsed:.2f}s")
        print(f"  Return: {result.total_return_pct:.2f}%")
        print(f"  Trades: {result.total_trades}")

        # Cache the result
        cache.put(
            result,
            strategy_name="MovingAverageCrossover",
            symbol="EURUSD",
            params=params,
            data_hash=data_hash,
        )
        print("  Result cached for future use.")

    # Show cache statistics
    stats = cache.get_stats()
    print("\nCache Statistics:")
    print(f"  Entries: {stats['entry_count']}")
    print(f"  Size: {stats['total_size_mb']:.2f} MB / {stats['max_size_mb']:.2f} MB")
    print(f"  Utilization: {stats['utilization_percent']:.1f}%")


# ============================================================================
# Example 4: Memory-Mapped Data Loading
# ============================================================================


def example_memory_mapped_data():
    """
    Demonstrate memory-mapped data loading for large datasets.
    """
    print("\n" + "=" * 70)
    print("Example 4: Memory-Mapped Data Loading")
    print("=" * 70)

    # Initialize data loader
    loader = MemoryMappedDataLoader(cache_dir=".cache/backtest_data")

    # For this example, we'll save data to CSV first
    data = load_mt5_data("EURUSD", "M1", bars=50000)  # Large dataset

    # Save to CSV
    csv_path = Path("temp_data.csv")
    data.to_csv(csv_path, index_label="timestamp")
    print(f"\nSaved {len(data)} bars to {csv_path}")

    # Load with memory mapping
    print("\nLoading data with memory mapping...")
    start_time = time.time()
    mmap_data = loader.load_mmap(
        csv_path,
        columns=["timestamp", "open", "high", "low", "close"]
    )
    elapsed = time.time() - start_time

    print(f"Loaded {len(mmap_data)} bars in {elapsed:.2f}s")
    print(f"Memory usage: {mmap_data.memory_usage(deep=True).sum() / 1024**2:.2f} MB")

    # Show cache info
    cache_count, cache_size = loader.get_cache_size()
    print(f"\nCache: {cache_count} files, {cache_size:.2f} MB")

    # Clean up
    csv_path.unlink()
    print("\nCleaned up temporary file.")


# ============================================================================
# Example 5: Serial vs Parallel Performance Comparison
# ============================================================================


def example_performance_comparison():
    """
    Compare serial vs parallel execution performance.
    """
    print("\n" + "=" * 70)
    print("Example 5: Serial vs Parallel Performance Comparison")
    print("=" * 70)

    # Load data
    data = load_mt5_data("EURUSD", "H1", bars=2000)

    # Create tasks
    tasks = []
    for fast in [5, 10, 15, 20]:
        for slow in [30, 50, 100]:
            task = BacktestTask(
                task_id=f"fast{fast}_slow{slow}",
                strategy_class=MovingAverageCrossover,
                strategy_params={"symbol": "EURUSD", "fast_period": fast, "slow_period": slow},
                data=data,
                engine_type="vectorized",
                engine_config={"initial_balance": 10000},
            )
            tasks.append(task)

    print(f"\nRunning {len(tasks)} backtests...")

    # Serial execution
    print("\n1. Serial Execution:")
    from apps.backtest.engine.vectorized import VectorizedEngine

    start_time = time.time()
    for task in tasks:
        strategy = task.strategy_class(params=task.strategy_params)
        engine = VectorizedEngine(strategy=strategy, data=task.data, **task.engine_config)
        engine.run()
    serial_time = time.time() - start_time

    print(f"   Time: {serial_time:.2f}s")
    print(f"   Rate: {len(tasks)/serial_time:.2f} backtests/sec")

    # Parallel execution (2 workers)
    print("\n2. Parallel Execution (2 workers):")
    parallel2 = ParallelBacktester(max_workers=2)
    start_time = time.time()
    parallel2.run_batch(tasks, show_progress=False)
    parallel2_time = time.time() - start_time

    print(f"   Time: {parallel2_time:.2f}s")
    print(f"   Rate: {len(tasks)/parallel2_time:.2f} backtests/sec")
    print(f"   Speedup: {serial_time/parallel2_time:.2f}x")

    # Parallel execution (4 workers)
    print("\n3. Parallel Execution (4 workers):")
    parallel4 = ParallelBacktester(max_workers=4)
    start_time = time.time()
    parallel4.run_batch(tasks, show_progress=False)
    parallel4_time = time.time() - start_time

    print(f"   Time: {parallel4_time:.2f}s")
    print(f"   Rate: {len(tasks)/parallel4_time:.2f} backtests/sec")
    print(f"   Speedup: {serial_time/parallel4_time:.2f}x")

    # Summary
    print("\n" + "=" * 70)
    print("Performance Summary:")
    print(f"  Serial:      {serial_time:.2f}s (baseline)")
    print(f"  Parallel 2:  {parallel2_time:.2f}s ({serial_time/parallel2_time:.2f}x faster)")
    print(f"  Parallel 4:  {parallel4_time:.2f}s ({serial_time/parallel4_time:.2f}x faster)")
    print("=" * 70)


# ============================================================================
# Main
# ============================================================================


def main():
    """Run all examples."""
    print("\n" + "=" * 70)
    print("Phase 4: Advanced Optimizations - Parallel Backtesting Examples")
    print("=" * 70)

    try:
        # Run examples
        example_parameter_sweep()
        example_portfolio_backtest()
        example_result_caching()
        example_memory_mapped_data()
        example_performance_comparison()

        print("\n" + "=" * 70)
        print("All examples completed successfully!")
        print("=" * 70)

    except Exception as e:
        print(f"\nError: {e}")
        import traceback

        traceback.print_exc()


if __name__ == "__main__":
    main()
