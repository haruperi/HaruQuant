"""Examples demonstrating plotting performance optimization features.

This script shows how to:
- LTTB downsampling for large datasets
- Caching for expensive computations
- Lazy evaluation for conditional rendering
- Memory optimization for DataFrames

Updated to use real market data.
"""

import time
import sys
from pathlib import Path

import numpy as np
import pandas as pd

# Add project root to path
project_root = Path(__file__).resolve().parents[5]
sys.path.insert(0, str(project_root))

from apps.plotting.optimization import (
    auto_downsample,
    cached,
    cached_drawdown,
    cached_rolling_metric,
    chunk_data,
    downsample_lttb,
    get_cache,
    lazy,
    optimize_dataframe_memory,
    should_downsample,
)
from apps.utils.logger import logger
from apps.utils.data_getters import load_mt5


def get_real_data(symbol="EURUSD", start_date="2020-01-01", end_date="2023-12-31", timeframe="D1"):
    """Get real data for examples."""
    try:
        data = load_mt5(symbol, start_date=start_date, end_date=end_date, timeframe=timeframe)
        return data["close"]
    except Exception as e:
        logger.error(f"Error loading data: {e}")
        return pd.Series()


def example_basic_downsampling():
    """Demonstrate basic downsampling with LTTB algorithm."""
    logger.info("=" * 60)
    logger.info("Example 1: Basic Downsampling")
    logger.info("=" * 60)

    # Load large dataset (long history)
    logger.info("Loading long-term EURUSD data...")
    # Using daily data for a long period to simulate large dataset
    # For minute data simulation, we would need much more data, but daily over 10 years is decent
    data = get_real_data("EURUSD", start_date="2010-01-01", end_date="2023-12-31")
    
    if data.empty:
        logger.warning("Skipping example due to data loading failure")
        return

    logger.info(f"Original data size: {len(data):,} points")
    logger.info(f"Memory usage: {data.memory_usage() / 1024**2:.2f} MB")

    # Check if downsampling is recommended
    if should_downsample(data):
        logger.info("Dataset is large - downsampling recommended")

        # Automatic downsampling
        start_time = time.time()
        downsampled = auto_downsample(data)
        duration = time.time() - start_time

        logger.success(f"Downsampled to {len(downsampled):,} points in {duration:.3f}s")
        logger.info(f"Reduction: {100 * (1 - len(downsampled) / len(data)):.1f}%")
        logger.info(
            f"Memory saved: {(data.memory_usage() - downsampled.memory_usage()) / 1024**2:.2f} MB"
        )
    else:
        logger.info("Dataset is not large enough for automatic downsampling recommendation.")
        logger.info("Forcing downsampling for demonstration...")
        
        start_time = time.time()
        downsampled = downsample_lttb(data, threshold=len(data)//2)
        duration = time.time() - start_time
        
        logger.success(f"Downsampled to {len(downsampled):,} points in {duration:.3f}s")

    logger.info("")


def example_manual_downsampling():
    """Demonstrate manual downsampling with custom threshold."""
    logger.info("=" * 60)
    logger.info("Example 2: Manual Downsampling")
    logger.info("=" * 60)

    # Load data
    logger.info("Loading GBPUSD data...")
    data = get_real_data("GBPUSD", start_date="2015-01-01", end_date="2023-12-31")
    if data.empty: return

    logger.info(f"Original: {len(data):,} points")
    logger.info(f"Peak value: {data.max():.4f}")
    logger.info(f"Trough value: {data.min():.4f}")

    # Downsample with custom threshold
    target_points = 1000
    downsampled = downsample_lttb(data, threshold=target_points)

    logger.success(f"Downsampled: {len(downsampled):,} points")
    logger.info(
        f"Peak preserved: {downsampled.max():.4f} (diff: {abs(data.max() - downsampled.max()):.6f})"
    )
    logger.info(
        f"Trough preserved: {downsampled.min():.4f} (diff: {abs(data.min() - downsampled.min()):.6f})"
    )

    logger.info("")


def example_caching():
    """Demonstrate using cache for expensive computations."""
    logger.info("=" * 60)
    logger.info("Example 3: Caching Expensive Computations")
    logger.info("=" * 60)

    # Load data
    logger.info("Loading USDJPY data...")
    data = get_real_data("USDJPY", start_date="2010-01-01", end_date="2023-12-31")
    if data.empty: return

    # First computation - not cached
    logger.info("First computation (not cached)...")
    start_time = time.time()
    result1 = cached_rolling_metric(data, window=200, metric="mean")
    duration1 = time.time() - start_time
    logger.info(f"Duration: {duration1:.3f}s")

    # Second computation - cached
    logger.info("Second computation (cached)...")
    start_time = time.time()
    result2 = cached_rolling_metric(data, window=200, metric="mean")
    duration2 = time.time() - start_time
    
    if duration2 > 0:
        logger.success(
            f"Duration: {duration2:.3f}s (speedup: {duration1 / duration2:.1f}x)"
        )
    else:
        logger.success("Duration: Instant (cached)")

    # Verify results are identical
    assert result1.equals(result2)
    logger.info("Results verified identical")

    # Cache statistics
    cache = get_cache()
    logger.info(f"Cache size: {len(cache)} items")

    # Clean up
    cache.clear()
    logger.info("Cache cleared")

    logger.info("")


def example_custom_cached_function():
    """Demonstrate creating custom cached functions."""
    logger.info("=" * 60)
    logger.info("Example 4: Custom Cached Functions")
    logger.info("=" * 60)

    @cached()
    def compute_sharpe_ratio(returns: pd.Series, window: int = 252) -> float:
        """Compute Sharpe ratio (expensive calculation)."""
        logger.debug(f"Computing Sharpe ratio with window={window}")
        rolling_mean = returns.rolling(window).mean().iloc[-1]
        rolling_std = returns.rolling(window).std().iloc[-1]
        return (rolling_mean / rolling_std) * np.sqrt(252) if rolling_std > 0 else 0

    # Load returns data
    logger.info("Loading AUDUSD returns...")
    prices = get_real_data("AUDUSD", start_date="2010-01-01", end_date="2023-12-31")
    if prices.empty: return
    returns = prices.pct_change().dropna()

    # First call - computed
    logger.info("First call (computed)...")
    start_time = time.time()
    sharpe1 = compute_sharpe_ratio(returns, window=252)
    duration1 = time.time() - start_time
    logger.info(f"Sharpe ratio: {sharpe1:.2f}, Duration: {duration1:.3f}s")

    # Second call - cached
    logger.info("Second call (cached)...")
    start_time = time.time()
    sharpe2 = compute_sharpe_ratio(returns, window=252)
    duration2 = time.time() - start_time
    logger.success(f"Sharpe ratio: {sharpe2:.2f}, Duration: {duration2:.3f}s")
    
    if duration2 > 0:
        logger.info(f"Speedup: {duration1 / duration2:.1f}x")
    else:
        logger.info("Speedup: Instant")

    # Clean up
    get_cache().clear()

    logger.info("")


def example_lazy_evaluation():
    """Demonstrate lazy plot generation."""
    logger.info("=" * 60)
    logger.info("Example 5: Lazy Plot Generation")
    logger.info("=" * 60)

    @lazy
    def generate_expensive_plot(data: pd.Series):
        """Generate an expensive plot (simulated)."""
        logger.info("Generating plot (expensive operation)...")
        time.sleep(0.5)  # Simulate expensive operation
        return f"Plot with {len(data)} points"

    # Create data
    data = pd.Series(range(10000))

    # Create lazy plot - not executed yet
    logger.info("Creating lazy plot...")
    lazy_plot = generate_expensive_plot(data)
    logger.info(f"Lazy plot created, rendered: {lazy_plot.is_rendered}")

    # Conditional rendering
    user_wants_plot = True  # Simulate user preference

    if user_wants_plot:
        logger.info("User requested plot - rendering now...")
        result = lazy_plot.render()
        logger.success(f"Plot rendered: {result}")
        logger.info(f"Is rendered: {lazy_plot.is_rendered}")
    else:
        logger.info("User didn't request plot - skipping expensive operation")

    logger.info("")


def example_memory_optimization():
    """Demonstrate DataFrame memory optimization."""
    logger.info("=" * 60)
    logger.info("Example 6: Memory Optimization")
    logger.info("=" * 60)

    # Create large DataFrame with inefficient types
    logger.info("Creating DataFrame with inefficient types...")
    df = pd.DataFrame(
        {
            "trade_id": np.arange(100000, dtype=np.int64),
            "price": np.random.uniform(100, 200, 100000).astype(np.float64),
            "quantity": np.random.randint(1, 100, 100000).astype(np.int64),
            "profit": np.random.uniform(-10, 10, 100000).astype(np.float64),
        }
    )

    # Check original memory usage
    original_memory = df.memory_usage(deep=True).sum() / 1024**2
    logger.info(f"Original memory usage: {original_memory:.2f} MB")
    logger.info(f"Data types:\n{df.dtypes}")

    # Optimize memory
    logger.info("Optimizing memory...")
    optimized = optimize_dataframe_memory(df, verbose=True)

    # Check optimized memory usage
    optimized_memory = optimized.memory_usage(deep=True).sum() / 1024**2
    logger.info(f"Optimized memory usage: {optimized_memory:.2f} MB")
    logger.info(f"Optimized data types:\n{optimized.dtypes}")

    # Verify data integrity
    assert np.allclose(df["price"].values, optimized["price"].values)
    logger.success("Data integrity verified")

    logger.info("")


def example_data_chunking():
    """Demonstrate processing large data in chunks."""
    logger.info("=" * 60)
    logger.info("Example 7: Data Chunking")
    logger.info("=" * 60)

    # Load large dataset
    logger.info("Loading NZDUSD data...")
    data = get_real_data("NZDUSD", start_date="2010-01-01", end_date="2023-12-31")
    if data.empty: return

    # Process in chunks
    logger.info("Processing in chunks...")
    chunks = chunk_data(data, chunk_size=1000)

    logger.info(f"Total chunks: {len(chunks)}")
    logger.info(f"Chunk sizes: {[len(c) for c in chunks[:5]]}...")

    # Process each chunk
    results = []
    for i, chunk in enumerate(chunks):
        # Simulate processing
        chunk_mean = chunk.mean()
        results.append(chunk_mean)
        if i < 5:
            logger.debug(f"Chunk {i + 1}: mean = {chunk_mean:.4f}")

    logger.success(f"Processed {len(chunks)} chunks successfully")
    logger.info(f"Overall mean: {np.mean(results):.4f}")

    logger.info("")


def example_drawdown_caching():
    """Demonstrate cached drawdown calculation."""
    logger.info("=" * 60)
    logger.info("Example 8: Cached Drawdown Calculation")
    logger.info("=" * 60)

    # Load data and calculate equity
    logger.info("Loading USDCAD data...")
    prices = get_real_data("USDCAD", start_date="2010-01-01", end_date="2023-12-31")
    if prices.empty: return
    
    equity = 10000 * (1 + prices.pct_change().fillna(0)).cumprod()

    # First calculation - not cached
    logger.info("First drawdown calculation (not cached)...")
    start_time = time.time()
    dd1 = cached_drawdown(equity)
    duration1 = time.time() - start_time
    logger.info(f"Duration: {duration1:.3f}s")
    logger.info(f"Max drawdown: {dd1.min() * 100:.2f}%")

    # Second calculation - cached
    logger.info("Second drawdown calculation (cached)...")
    start_time = time.time()
    _dd2 = cached_drawdown(equity)  # noqa: F841 - demonstrating caching
    duration2 = time.time() - start_time
    
    if duration2 > 0:
        logger.success(
            f"Duration: {duration2:.3f}s (speedup: {duration1 / duration2:.1f}x)"
        )
    else:
        logger.success("Duration: Instant (cached)")

    # Clean up
    get_cache().clear()

    logger.info("")


def example_complete_pipeline():
    """Demonstrate complete optimization pipeline."""
    logger.info("=" * 60)
    logger.info("Example 9: Complete Optimization Pipeline")
    logger.info("=" * 60)

    # Step 1: Create large dataset
    logger.info("Step 1: Loading large dataset (EURUSD)...")
    prices = get_real_data("EURUSD", start_date="2010-01-01", end_date="2023-12-31")
    if prices.empty: return
    
    df = pd.DataFrame(
        {
            "close": prices,
            "volume": np.random.randint(1000, 10000, len(prices)), # Mock volume if not available
        },
        index=prices.index,
    )
    logger.info(f"Dataset size: {len(df):,} rows")
    logger.info(f"Memory: {df.memory_usage(deep=True).sum() / 1024**2:.2f} MB")

    # Step 2: Memory optimization
    logger.info("Step 2: Optimizing memory...")
    df = optimize_dataframe_memory(df, verbose=True)

    # Step 3: Downsample if needed
    if should_downsample(df["close"]):
        logger.info("Step 3: Downsampling data...")
        df_down = auto_downsample(df["close"])
        logger.success(f"Downsampled to {len(df_down):,} rows")
    else:
        logger.info("Step 3: Downsampling not needed (dataset size manageable)")

    # Step 4: Compute metrics with caching
    logger.info("Step 4: Computing metrics (cached)...")

    @cached()
    def compute_metrics(prices):
        return {
            "sma_50": prices.rolling(50).mean(),
            "sma_200": prices.rolling(200).mean(),
            "volatility": prices.rolling(50).std(),
        }

    metrics = compute_metrics(df["close"])
    logger.success(f"Computed {len(metrics)} metrics")

    # Step 5: Lazy plot generation
    logger.info("Step 5: Creating lazy plots...")

    @lazy
    def create_price_chart(data):
        return f"Price chart with {len(data)} points"

    @lazy
    def create_volume_chart(data):
        return f"Volume chart with {len(data)} points"

    price_plot = create_price_chart(df["close"])
    _volume_plot = create_volume_chart(df["volume"])  # noqa: F841 - for demonstration

    logger.info("Lazy plots created (not rendered)")

    # Render only if needed
    logger.info("Rendering price plot...")
    price_result = price_plot.render()
    logger.success(price_result)

    # Clean up
    get_cache().clear()

    logger.info("")


def main():
    """Run all examples."""
    logger.info("\n" + "=" * 60)
    logger.info("PLOTTING PERFORMANCE OPTIMIZATION EXAMPLES")
    logger.info("=" * 60 + "\n")

    examples = [
        example_basic_downsampling,
        example_manual_downsampling,
        example_caching,
        example_custom_cached_function,
        example_lazy_evaluation,
        example_memory_optimization,
        example_data_chunking,
        example_drawdown_caching,
        example_complete_pipeline,
    ]

    for example in examples:
        try:
            example()
        except Exception as e:
            logger.error(f"Error in {example.__name__}: {e}", exc_info=True)

    logger.info("=" * 60)
    logger.info("ALL EXAMPLES COMPLETED")
    logger.info("=" * 60)


if __name__ == "__main__":
    main()

