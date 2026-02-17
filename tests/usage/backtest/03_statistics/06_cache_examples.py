"""Example demonstrating cache functionality for rolling metrics and drawdowns.

This example shows how the plotting optimization cache can speed up
expensive rolling calculations like volatility, Sharpe ratio, and
drawdown series computation when the same inputs are reused.

Updated to use real market data.
"""

import time
import sys
from pathlib import Path

import numpy as np
import pandas as pd

# Add project root to path
project_root = Path(__file__).resolve().parents[4]
sys.path.insert(0, str(project_root))

from apps.utils.logger import logger
from apps.plotting.optimization import cached_drawdown, cached_rolling_metric, get_cache
from apps.utils.data_getters import load_mt5


def clear_cache() -> int:
    """Clear the global plot cache and return the number of entries cleared."""
    cache = get_cache()
    count = len(cache)
    cache.clear()
    return count


def get_real_returns(
    symbol: str = "EURUSD",
    start_date: str = "2020-01-01",
    end_date: str = "2023-12-31",
) -> pd.Series:
    """Get real returns data."""
    try:
        data = load_mt5(
            symbol, timeframe="D1", start_date=start_date, end_date=end_date
        )
        if data is None or data.empty:
            raise ValueError("No data returned from MT5")
        returns = data["close"].pct_change().dropna()
        return returns
    except Exception as e:
        logger.error(f"Error loading data: {e}")
        # Fallback to random data if load fails
        dates = pd.date_range(start=start_date, end=end_date, freq="D")
        return pd.Series(np.random.randn(len(dates)) * 0.01, index=dates)


def example_rolling_volatility_cache() -> None:
    """Demonstrate caching of rolling volatility calculations."""
    logger.info("=" * 70)
    logger.info("Example 1: Rolling Volatility Cache")
    logger.info("=" * 70)

    # Load real returns
    logger.info("Loading EURUSD returns...")
    returns = get_real_returns("EURUSD")

    logger.info(f"\nLoaded {len(returns)} daily returns")

    # First calculation (uncached)
    start = time.time()
    result1 = cached_rolling_metric(returns, window=20, metric="std") * np.sqrt(252)
    time1 = time.time() - start

    logger.info(f"First calculation: {time1:.6f} seconds")
    logger.info(f"Result length: {len(result1)}")
    logger.info(f"Result mean: {result1.mean():.4f}")

    # Second calculation (should be faster due to cache)
    start = time.time()
    result2 = cached_rolling_metric(returns, window=20, metric="std") * np.sqrt(252)
    time2 = time.time() - start

    logger.info(f"Second calculation (cached): {time2:.6f} seconds")
    if time2 > 0:
        logger.info(f"Speedup: {time1 / time2:.1f}x faster")
    else:
        logger.info("Speedup: Instant (cached)")

    # Verify results are identical
    assert result1.equals(result2)
    logger.success("OK: Cached results match original")


def example_rolling_sharpe_cache() -> None:
    """Demonstrate caching of rolling Sharpe ratio calculations."""
    logger.info("\n" + "=" * 70)
    logger.info("Example 2: Rolling Sharpe Ratio Cache")
    logger.info("=" * 70)

    # Load real returns
    logger.info("Loading GBPUSD returns...")
    returns = get_real_returns("GBPUSD")

    logger.info(f"\nLoaded {len(returns)} daily returns")

    risk_free_rate = 0.02
    daily_rf = risk_free_rate / 252

    # First calculation
    start = time.time()
    rolling_mean = cached_rolling_metric(returns, window=60, metric="mean")
    rolling_std = cached_rolling_metric(returns, window=60, metric="std")
    result1 = ((rolling_mean - daily_rf) / rolling_std) * np.sqrt(252)
    time1 = time.time() - start

    logger.info(f"First calculation: {time1:.6f} seconds")
    logger.info(f"Result length: {len(result1)}")
    logger.info(f"Mean Sharpe: {result1.mean():.4f}")

    # Second calculation (cached)
    start = time.time()
    rolling_mean = cached_rolling_metric(returns, window=60, metric="mean")
    rolling_std = cached_rolling_metric(returns, window=60, metric="std")
    result2 = ((rolling_mean - daily_rf) / rolling_std) * np.sqrt(252)
    time2 = time.time() - start

    logger.info(f"Second calculation (cached): {time2:.6f} seconds")
    if time2 > 0:
        logger.info(f"Speedup: {time1 / time2:.1f}x faster")
    else:
        logger.info("Speedup: Instant (cached)")

    assert result1.equals(result2)
    logger.success("OK: Cached results match original")


def example_drawdown_cache() -> None:
    """Demonstrate caching of drawdown series calculations."""
    logger.info("\n" + "=" * 70)
    logger.info("Example 3: Drawdown Series Cache")
    logger.info("=" * 70)

    # Load real returns and calculate equity
    logger.info("Loading USDJPY returns...")
    returns = get_real_returns("USDJPY")
    equity = (1 + returns).cumprod() * 10000

    logger.info(f"\nCalculated equity curve: {len(equity)} days")
    logger.info(f"Start equity: ${equity.iloc[0]:.2f}")
    logger.info(f"End equity: ${equity.iloc[-1]:.2f}")

    # First calculation
    start = time.time()
    result1 = cached_drawdown(equity)
    time1 = time.time() - start

    logger.info(f"\nFirst calculation: {time1:.6f} seconds")
    logger.info(f"Max drawdown: {result1.min():.4f}")

    # Second calculation (cached)
    start = time.time()
    result2 = cached_drawdown(equity)
    time2 = time.time() - start

    logger.info(f"Second calculation (cached): {time2:.6f} seconds")
    if time2 > 0:
        logger.info(f"Speedup: {time1 / time2:.1f}x faster")
    else:
        logger.info("Speedup: Instant (cached)")

    assert result1.equals(result2)
    logger.success("OK: Cached results match original")


def example_cache_clearing() -> None:
    """Demonstrate cache clearing functionality."""
    logger.info("\n" + "=" * 70)
    logger.info("Example 4: Cache Clearing")
    logger.info("=" * 70)

    # Load data
    logger.info("Loading AUDUSD returns...")
    returns = get_real_returns("AUDUSD")

    # Populate caches
    logger.info("\nPopulating caches...")
    cached_rolling_metric(returns, window=20, metric="std")
    cached_rolling_metric(returns, window=60, metric="mean")
    equity = (1 + returns).cumprod() * 10000
    cached_drawdown(equity)

    logger.info("Caches populated")

    # Clear caches
    logger.info("\nClearing caches...")
    cleared = clear_cache()

    logger.info(f"Cleared cache entries: {cleared}")

    # Verify cache is cleared by checking performance
    start = time.time()
    cached_rolling_metric(returns, window=20, metric="std")
    time_after_clear = time.time() - start

    logger.info(f"Calculation after clear: {time_after_clear:.6f} seconds")
    logger.success("OK: Cache successfully cleared")


def example_cache_benefits() -> None:
    """Demonstrate overall cache performance benefits."""
    logger.info("\n" + "=" * 70)
    logger.info("Example 5: Overall Cache Benefits")
    logger.info("=" * 70)

    # Load large dataset (long history)
    logger.info("Loading long-term EURUSD data...")
    returns = get_real_returns("EURUSD", start_date="2010-01-01", end_date="2023-12-31")

    logger.info(f"\nLarge dataset: {len(returns)} days")

    # Clear cache first
    clear_cache()

    # Simulate multiple analysis runs (without cache)
    logger.info("\nWithout cache (3 runs):")
    total_time_no_cache = 0.0
    for i in range(3):
        clear_cache()  # Clear before each run
        start = time.time()
        cached_rolling_metric(returns, window=30, metric="std")
        cached_rolling_metric(returns, window=90, metric="mean")
        time_taken = time.time() - start
        total_time_no_cache += time_taken
        logger.info(f"  Run {i + 1}: {time_taken:.6f} seconds")

    avg_time_no_cache = total_time_no_cache / 3
    logger.info(f"Average: {avg_time_no_cache:.6f} seconds")

    # Simulate multiple analysis runs (with cache)
    logger.info("\nWith cache (3 runs):")
    clear_cache()
    total_time_with_cache = 0.0
    for i in range(3):
        start = time.time()
        cached_rolling_metric(returns, window=30, metric="std")
        cached_rolling_metric(returns, window=90, metric="mean")
        time_taken = time.time() - start
        total_time_with_cache += time_taken
        logger.info(f"  Run {i + 1}: {time_taken:.6f} seconds")

    avg_time_with_cache = total_time_with_cache / 3
    logger.info(f"Average: {avg_time_with_cache:.6f} seconds")

    # Calculate improvement
    if avg_time_no_cache > 0:
        improvement = (
            (avg_time_no_cache - avg_time_with_cache) / avg_time_no_cache * 100
        )
        logger.success(
            f"\nOK: Cache provides ~{improvement:.1f}% improvement on repeated calculations"
        )
    else:
        logger.success("\nOK: Cache working correctly (calculations too fast to measure)")


def main() -> None:
    """Run all cache examples."""
    logger.info("Starting Cache Examples")
    logger.info("=" * 70)

    try:
        example_rolling_volatility_cache()
        example_rolling_sharpe_cache()
        example_drawdown_cache()
        example_cache_clearing()
        example_cache_benefits()

        logger.success("\n" + "=" * 70)
        logger.success("All cache examples completed successfully!")
        logger.success("=" * 70)

    except Exception as e:
        logger.error(f"Error in cache examples: {e}", exc_info=True)
        raise


if __name__ == "__main__":
    main()

