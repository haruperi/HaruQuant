"""Example 01: Loading Data from Dukascopy

This example demonstrates how to load historical data from Dukascopy parquet files.

Topics covered:
- Basic data loading
- Date range filtering
- Memory caching
- Loading multiple symbols
- Data validation
- Error handling

Author: HaruQuant Development Team
Created: 2025-12-03
"""

import sys
from pathlib import Path

# Add project root to path
project_root = Path(__file__).resolve().parents[4]
sys.path.insert(0, str(project_root))

from apps.utils.logger import logger  # noqa: E402
from apps.utils.data_getters import (  # noqa: E402
    clear_data_cache,
    get_data_dir,
    load_dukascopy,
)


def example1_basic_loading():
    """Load basic data without filters."""
    print("\n" + "=" * 70)
    print("Example 1: Basic Data Loading")
    print("=" * 70)

    # Load all available EURUSD data
    data = load_dukascopy("EURUSD")

    print(f"\nLoaded {len(data):,} bars")
    print(f"Date range: {data.index[0]} to {data.index[-1]}")
    print(f"Duration: {(data.index[-1] - data.index[0]).days} days")

    print("\nFirst 5 bars:")
    print(data.head())

    print("\nLast 5 bars:")
    print(data.tail())

    print("\nColumn info:")
    print(data.info())


def example2_date_filtering():
    """Load data for specific date range."""
    print("\n" + "=" * 70)
    print("Example 2: Date Range Filtering")
    print("=" * 70)

    # Load only November 2025 data
    data = load_dukascopy(
        "EURUSD", start_date="2025-11-03", end_date="2025-11-30"
    )

    print(f"\nLoaded {len(data):,} bars for November 2025")
    print(f"Date range: {data.index[0]} to {data.index[-1]}")

    # Calculate some statistics
    returns = data["close"].pct_change()
    print(f"\nNovember 2025 Statistics:")
    print(f"  Total return: {(data['close'].iloc[-1] / data['close'].iloc[0] - 1) * 100:.2f}%")
    print(f"  Volatility (daily): {returns.std() * 100:.4f}%")
    print(f"  Max price: {data['high'].max():.5f}")
    print(f"  Min price: {data['low'].min():.5f}")


def example3_caching():
    """Demonstrate memory caching for performance."""
    print("\n" + "=" * 70)
    print("Example 3: Memory Caching")
    print("=" * 70)

    import time

    # Clear cache first
    clear_data_cache()

    # First load - reads from disk
    print("\nFirst load (from disk)...")
    start = time.time()
    data1 = load_dukascopy("EURUSD", start_date="2025-01-01", end_date="2025-11-30", cache=True)
    time1 = time.time() - start
    print(f"Time: {time1:.3f} seconds")
    print(f"Loaded {len(data1):,} bars")

    # Second load - uses memory cache
    print("\nSecond load (from cache)...")
    start = time.time()
    data2 = load_dukascopy("EURUSD", start_date="2025-01-01", end_date="2025-11-30", cache=True)
    time2 = time.time() - start
    print(f"Time: {time2:.3f} seconds")
    print(f"Loaded {len(data2):,} bars")

    print(f"\nSpeed improvement: {time1 / time2:.1f}x faster")
    print(f"Data identical: {data1.equals(data2)}")


def example4_multiple_symbols():
    """Load data for multiple symbols."""
    print("\n" + "=" * 70)
    print("Example 4: Loading Multiple Symbols")
    print("=" * 70)

    symbols = ["EURUSD", "GBPUSD", "USDJPY"]
    date_range = ("2025-11-03", "2025-11-30")

    datasets = {}

    for symbol in symbols:
        try:
            data = load_dukascopy(
                symbol, start_date=date_range[0], end_date=date_range[1]
            )
            datasets[symbol] = data
            print(f"\n{symbol}:")
            print(f"  Bars: {len(data):,}")
            print(f"  Date range: {data.index[0]} to {data.index[-1]}")

            # Calculate return
            total_return = (data["close"].iloc[-1] / data["close"].iloc[0] - 1) * 100
            print(f"  Return: {total_return:+.2f}%")

        except FileNotFoundError as e:
            print(f"\n{symbol}: NOT AVAILABLE")
            print(f"  Error: {e}")

    print(f"\nSuccessfully loaded {len(datasets)} symbols")


def example5_data_validation():
    """Validate data quality."""
    print("\n" + "=" * 70)
    print("Example 5: Data Validation")
    print("=" * 70)

    data = load_dukascopy("EURUSD", start_date="2025-11-03", end_date="2025-11-30")

    print("\nData Quality Checks:")

    # Check for missing values
    missing = data.isnull().sum()
    print(f"\n1. Missing values:")
    for col in data.columns:
        print(f"   {col}: {missing[col]}")

    # Check for duplicates
    duplicates = data.index.duplicated().sum()
    print(f"\n2. Duplicate timestamps: {duplicates}")

    # Check for gaps
    expected_bars = len(data)
    time_diff = data.index.to_series().diff()
    mode_diff = time_diff.mode()[0]
    gaps = (time_diff > mode_diff * 1.5).sum()
    print(f"\n3. Time gaps detected: {gaps}")
    print(f"   Expected interval: {mode_diff}")

    # Check data ranges
    print(f"\n4. Price ranges:")
    print(f"   Open: {data['open'].min():.5f} to {data['open'].max():.5f}")
    print(f"   High: {data['high'].min():.5f} to {data['high'].max():.5f}")
    print(f"   Low: {data['low'].min():.5f} to {data['low'].max():.5f}")
    print(f"   Close: {data['close'].min():.5f} to {data['close'].max():.5f}")

    # Check OHLC consistency
    invalid_bars = (
        (data["high"] < data["low"])
        | (data["high"] < data["open"])
        | (data["high"] < data["close"])
        | (data["low"] > data["open"])
        | (data["low"] > data["close"])
    ).sum()
    print(f"\n5. Invalid OHLC bars: {invalid_bars}")

    # Overall assessment
    print("\n" + "-" * 70)
    if missing.sum() == 0 and duplicates == 0 and invalid_bars == 0:
        print("DATA QUALITY: EXCELLENT - Ready for backtesting")
    elif missing.sum() < 10 and duplicates < 5 and invalid_bars == 0:
        print("DATA QUALITY: GOOD - Minor issues, safe to use")
    else:
        print("DATA QUALITY: NEEDS ATTENTION - Consider preprocessing")


def example6_error_handling():
    """Demonstrate proper error handling."""
    print("\n" + "=" * 70)
    print("Example 6: Error Handling")
    print("=" * 70)

    # Try to load non-existent symbol
    print("\nAttempting to load non-existent symbol...")
    try:
        data = load_dukascopy("INVALID_SYMBOL")
        print(f"Loaded {len(data)} bars")
    except FileNotFoundError as e:
        print(f"ERROR: {e}")
        print("\nThis is expected - the symbol doesn't exist")

    # Show available files
    data_dir = get_data_dir() / "dukascopy"
    if data_dir.exists():
        available = list(data_dir.glob("*.parquet"))
        print(f"\nAvailable data files ({len(available)}):")
        for f in available[:10]:  # Show first 10
            print(f"  - {f.name}")
        if len(available) > 10:
            print(f"  ... and {len(available) - 10} more")
    else:
        print(f"\nData directory not found: {data_dir}")


def main():
    """Run all examples."""
    print("\n" + "=" * 70)
    print("DUKASCOPY DATA LOADING EXAMPLES")
    print("=" * 70)

    try:
        example1_basic_loading()
        example2_date_filtering()
        example3_caching()
        example4_multiple_symbols()
        example5_data_validation()
        example6_error_handling()

        print("\n" + "=" * 70)
        print("ALL EXAMPLES COMPLETED SUCCESSFULLY")
        print("=" * 70)

        print("\nKey Takeaways:")
        print("1. Use load_dukascopy() to load historical data from parquet files")
        print("2. Filter date ranges to load only what you need")
        print("3. Enable caching for better performance with repeated loads")
        print("4. Always validate data quality before backtesting")
        print("5. Handle FileNotFoundError for missing symbols")

        print("\nNext Steps:")
        print("- Try 02_load_mt5_realtime.py to load data from MT5")
        print("- Explore 03_data_preprocessing.py for data cleaning")
        print("- Learn multi-timeframe strategies in 04_multi_timeframe.py")

    except Exception as e:
        logger.error(f"Error running examples: {e}")
        import traceback

        traceback.print_exc()


if __name__ == "__main__":
    main()

