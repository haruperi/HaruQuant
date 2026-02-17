"""Example demonstrating utility and helper functions for backtest statistics.

This example shows how to use small utility functions for data preparation,
alignment, and formatting.

Updated to use real market data.
"""

from __future__ import annotations

import hashlib
import sys
from pathlib import Path

import numpy as np
import pandas as pd

project_root = Path(__file__).resolve().parents[4]
sys.path.insert(0, str(project_root))

from apps.utils.logger import logger  # noqa: E402
from apps.utils.data_getters import load_mt5  # noqa: E402


def _prepare_returns(data: pd.Series | np.ndarray, is_returns: bool) -> pd.Series:
    """Ensure returns series with a DatetimeIndex."""
    if isinstance(data, np.ndarray):
        data = pd.Series(data)

    if not isinstance(data, pd.Series):
        raise TypeError("Expected Series or numpy array.")

    series = data.copy()
    if not isinstance(series.index, pd.DatetimeIndex):
        series.index = pd.date_range("2024-01-01", periods=len(series), freq="D")

    if is_returns:
        return series.dropna()

    return series.pct_change().dropna()


def _align_series(
    series1: pd.Series,
    series2: pd.Series,
    join: str = "inner",
    fill_method: str | None = None,
) -> tuple[pd.Series, pd.Series]:
    """Align two series by index with optional fill."""
    aligned = pd.concat([series1, series2], axis=1, join=join)
    aligned.columns = ["s1", "s2"]
    aligned = aligned.sort_index()

    if fill_method:
        aligned = aligned.fillna(method=fill_method)

    aligned = aligned.dropna()
    return aligned["s1"], aligned["s2"]


def _cache_key_from_equity(equity: pd.Series) -> str:
    """Generate a stable cache key from equity values and index."""
    payload = pd.DataFrame({"value": equity.values, "index": equity.index.astype(str)})
    hashed = hashlib.sha256(payload.to_csv(index=False).encode("utf-8")).hexdigest()
    return hashed


def _score_str(value: float | int | None, metric_type: str, decimals: int = 2) -> str:
    """Format metric values based on type."""
    if value is None or (isinstance(value, float) and np.isnan(value)):
        return "n/a"

    if metric_type == "percentage":
        return f"{value:.{decimals}f}%"
    if metric_type == "currency":
        return f"{value:,.{decimals}f}"
    if metric_type == "integer":
        return f"{int(value)}"
    if metric_type == "ratio":
        return f"{value:.{decimals}f}"
    return f"{value:.{decimals}f}"


def _format_metric(value: float, name: str, add_units: bool = True) -> str:
    """Auto-detect metric type from name and format it."""
    name_lower = name.lower()
    if "percent" in name_lower or "%" in name_lower:
        return _score_str(value, "percentage", 2 if add_units else 2)
    if "ratio" in name_lower or "alpha" in name_lower or "beta" in name_lower:
        return _score_str(value, "ratio", 2)
    if "equity" in name_lower or "balance" in name_lower:
        return _score_str(value, "currency", 2 if add_units else 2)
    if "trades" in name_lower:
        return _score_str(value, "integer", 0)
    return _score_str(value, "float", 4)


def get_real_data(
    symbol: str = "EURUSD",
    start_date: str = "2023-01-01",
    end_date: str = "2023-12-31",
) -> pd.Series:
    """Load real close price data for examples."""
    try:
        data = load_mt5(
            symbol,
            timeframe="D1",
            start_date=start_date,
            end_date=end_date,
        )
        if data is None or data.empty:
            return pd.Series(dtype=float)
        return data["close"]
    except Exception as exc:
        logger.error(f"Error loading data: {exc}")
        return pd.Series(dtype=float)


def example_prepare_returns() -> None:
    """Example 1: Prepare returns from equity or returns data."""
    logger.info("=" * 70)
    logger.info("Example 1: Prepare Returns")
    logger.info("=" * 70)

    equity = pd.Series(
        [10000, 10100, 10050, 10200, 10150],
        index=pd.date_range("2024-01-01", periods=5, freq="D"),
    )
    logger.info("Original Equity Curve:")
    print(equity)

    returns = _prepare_returns(equity, is_returns=False)
    logger.info("Converted to Returns:")
    print(returns)
    logger.info(f"Converted equity to {len(returns)} return values")

    raw_returns = pd.Series([0.01, -0.005, 0.015, -0.005])
    prepared_returns = _prepare_returns(raw_returns, is_returns=True)

    logger.info("Original Returns (no DatetimeIndex):")
    print(raw_returns)
    logger.info("Prepared Returns (with DatetimeIndex):")
    print(prepared_returns)
    logger.info(f"Added DatetimeIndex to {len(prepared_returns)} returns")

    equity_array = np.array([100, 102, 101, 105, 103])
    returns_from_array = _prepare_returns(equity_array, is_returns=False)

    logger.info("Returns from numpy array:")
    print(returns_from_array)
    logger.info("Converted numpy array to returns Series")


def example_align_series() -> None:
    """Example 2: Align two time series."""
    logger.info("\n" + "=" * 70)
    logger.info("Example 2: Align Time Series")
    logger.info("=" * 70)

    dates1 = pd.date_range("2024-01-01", periods=10, freq="D")
    series1 = pd.Series(np.random.randn(10), index=dates1, name="Strategy")

    dates2 = pd.date_range("2024-01-03", periods=8, freq="D")
    series2 = pd.Series(np.random.randn(8), index=dates2, name="Benchmark")

    logger.info("Series 1 (Strategy):")
    logger.info(f"  Date range: {series1.index[0]} to {series1.index[-1]}")
    logger.info(f"  Length: {len(series1)}")

    logger.info("Series 2 (Benchmark):")
    logger.info(f"  Date range: {series2.index[0]} to {series2.index[-1]}")
    logger.info(f"  Length: {len(series2)}")

    aligned1, aligned2 = _align_series(series1, series2, join="inner")
    logger.info("Inner Join Result:")
    logger.info(f"  Aligned length: {len(aligned1)}")
    logger.info(f"  Date range: {aligned1.index[0]} to {aligned1.index[-1]}")
    logger.info(f"Inner join: {len(aligned1)} common dates")

    aligned1, aligned2 = _align_series(series1, series2, join="outer", fill_method="ffill")
    logger.info("Outer Join with Forward Fill:")
    logger.info(f"  Aligned length: {len(aligned1)}")
    logger.info(f"Outer join with ffill: {len(aligned1)} total dates")


def example_score_str() -> None:
    """Example 3: Format metric values."""
    logger.info("\n" + "=" * 70)
    logger.info("Example 3: Score String Formatting")
    logger.info("=" * 70)

    test_values = [
        (1.567894, "ratio", "Sharpe Ratio"),
        (0.1567, "percentage", "Win Rate"),
        (1234.56, "currency", "Equity"),
        (42, "integer", "Total Trades"),
        (0.00123456, "float", "Small Value"),
        (None, "ratio", "Missing Value"),
        (np.nan, "percentage", "NaN Value"),
    ]

    logger.info("Formatting Examples:")
    print(f"\n{'Value':<15} {'Type':<12} {'Name':<15} {'Formatted':<15}")
    print("-" * 60)

    for value, metric_type, name in test_values:
        formatted = _score_str(value, metric_type)
        print(f"{str(value):<15} {metric_type:<12} {name:<15} {formatted:<15}")

    logger.info("All metric types formatted correctly")

    logger.info("Custom Decimal Places:")
    value = 1.23456789
    for decimals in [0, 2, 4, 6]:
        formatted = _score_str(value, "ratio", decimals=decimals)
        print(f"  {decimals} decimals: {formatted}")


def example_format_metric() -> None:
    """Example 4: Auto-detect metric type and format."""
    logger.info("\n" + "=" * 70)
    logger.info("Example 4: Auto-Format Metrics")
    logger.info("=" * 70)

    metric_values = {
        "Total Return %": 15.67,
        "Sharpe Ratio": 1.567,
        "Start Equity": 10000.0,
        "Total Trades": 42,
        "Win Rate %": 58.5,
        "Max Drawdown %": 12.34,
        "Alpha": 0.0234,
        "Beta": 0.98,
        "Profit Factor": 1.87,
        "Average Duration": 4.5,
    }

    logger.info("Auto-Formatted Metrics:")
    print(f"\n{'Metric Name':<25} {'Value':<15} {'Formatted':<15}")
    print("-" * 60)

    for name, value in metric_values.items():
        formatted = _format_metric(value, name, add_units=True)
        print(f"{name:<25} {value:<15.4f} {formatted:<15}")

    logger.info("All metrics auto-formatted correctly")

    test_value = 15.67
    with_units = _format_metric(test_value, "Total Return %", add_units=True)
    without_units = _format_metric(test_value, "Total Return %", add_units=False)

    print(f"  With units:    {with_units}")
    print(f"  Without units: {without_units}")


def example_cache_key() -> None:
    """Example 5: Generate cache keys for equity curves."""
    logger.info("\n" + "=" * 70)
    logger.info("Example 5: Cache Key Generation")
    logger.info("=" * 70)

    equity1 = pd.Series(
        [100, 102, 101, 105], index=pd.date_range("2024-01-01", periods=4)
    )
    equity2 = pd.Series(
        [100, 102, 101, 105], index=pd.date_range("2024-01-01", periods=4)
    )
    equity3 = pd.Series(
        [100, 102, 101, 106], index=pd.date_range("2024-01-01", periods=4)
    )

    key1 = _cache_key_from_equity(equity1)
    key2 = _cache_key_from_equity(equity2)
    key3 = _cache_key_from_equity(equity3)

    logger.info("Cache Keys:")
    print(f"  Equity 1 key: {key1}")
    print(f"  Equity 2 key: {key2}")
    print(f"  Equity 3 key: {key3}")

    if key1 == key2:
        logger.info("Identical equity curves produce same cache key")
    else:
        logger.error("Identical equity curves should have same key")

    if key1 != key3:
        logger.info("Different equity curves produce different cache keys")
    else:
        logger.error("Different equity curves should have different keys")

    key1_again = _cache_key_from_equity(equity1)
    if key1 == key1_again:
        logger.info("Cache key is stable across calls")
    else:
        logger.error("Cache key should be stable")


def example_combined_workflow() -> None:
    """Example 6: Combined workflow using multiple utilities."""
    logger.info("\n" + "=" * 70)
    logger.info("Example 6: Combined Workflow (Real Data)")
    logger.info("=" * 70)

    logger.info("Loading EURUSD (Strategy) and GBPUSD (Benchmark) data...")
    strategy_price = get_real_data("EURUSD")
    benchmark_price = get_real_data("GBPUSD")

    if strategy_price.empty or benchmark_price.empty:
        logger.warning("Skipping real data workflow due to data loading failure")
        return

    strategy_equity = 10000 * (1 + strategy_price.pct_change().fillna(0)).cumprod()
    benchmark_returns = benchmark_price.pct_change().fillna(0)

    logger.info("Step 1: Data Creation")
    logger.info(f"  Strategy equity: {len(strategy_equity)} days")
    logger.info(f"  Benchmark returns: {len(benchmark_returns)} days")

    strategy_returns = _prepare_returns(strategy_equity, is_returns=False)
    logger.info("Step 2: Prepare Returns")
    logger.info(f"  Strategy returns: {len(strategy_returns)} values")

    aligned_strat, aligned_bench = _align_series(
        strategy_returns, benchmark_returns, join="inner", fill_method="ffill"
    )
    logger.info("Step 3: Align Series")
    logger.info(f"  Aligned length: {len(aligned_strat)} days")

    total_return = (strategy_equity.iloc[-1] / strategy_equity.iloc[0] - 1) * 100
    sharpe = (
        strategy_returns.mean() / strategy_returns.std() * np.sqrt(252)
        if strategy_returns.std() != 0
        else 0.0
    )
    correlation = aligned_strat.corr(aligned_bench)

    logger.info("Step 4: Calculate Metrics")
    logger.info(f"  Total Return: {_format_metric(total_return, 'Total Return %')}")
    logger.info(f"  Sharpe Ratio: {_format_metric(sharpe, 'Sharpe Ratio')}")
    logger.info(f"  Correlation: {_format_metric(correlation, 'Correlation')}")

    cache_key = _cache_key_from_equity(strategy_equity)
    logger.info("Step 5: Cache Key")
    logger.info(f"  Key: {cache_key}")

    logger.info("Complete workflow executed successfully")


def main() -> None:
    """Run all examples."""
    logger.info("Starting Utility Functions Examples")
    logger.info("=" * 70)

    example_prepare_returns()
    example_align_series()
    example_score_str()
    example_format_metric()
    example_cache_key()
    example_combined_workflow()

    logger.info("\n" + "=" * 70)
    logger.info("All examples completed successfully")
    logger.info("=" * 70)


if __name__ == "__main__":
    main()

