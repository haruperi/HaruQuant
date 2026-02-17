"""Example 02: Loading Data from MetaTrader 5

This example demonstrates how to load real-time and historical data from MT5.

Topics covered:
- MT5 connection setup
- Loading different timeframes
- Date range vs count-based loading
- Error handling and fallback
- Comparing MT5 vs Dukascopy data
- Best practices for live data

Requirements:
- MT5 terminal installed and running
- Valid credentials in settings/config.ini
- Section: [MT5-Pepperstone-demo]

Author: HaruQuant Development Team
Created: 2025-12-03
"""

import sys
from pathlib import Path

# Add project root to path
project_root = Path(__file__).resolve().parents[4]
sys.path.insert(0, str(project_root))

from datetime import datetime  # noqa: E402

from apps.utils.logger import logger  # noqa: E402
from apps.utils.data_getters import load_dukascopy, load_mt5  # noqa: E402


def example1_basic_mt5():
    """Load basic data from MT5."""
    print("\n" + "=" * 70)
    print("Example 1: Basic MT5 Data Loading")
    print("=" * 70)

    print("\nAttempting to connect to MT5...")
    print("(Make sure MT5 terminal is running)")

    try:
        # Load last 1000 H1 bars
        data = load_mt5("EURUSD", timeframe="H1", count=1000)

        print(f"\nSuccessfully loaded {len(data):,} H1 bars from MT5")
        print(f"Date range: {data.index[0]} to {data.index[-1]}")

        print("\nFirst 5 bars:")
        print(data.head())

        print("\nLast 5 bars (most recent):")
        print(data.tail())

        print("\nData columns:")
        print(data.columns.tolist())

    except Exception as e:
        print(f"\nMT5 connection failed: {e}")
        print("The function automatically fell back to Dukascopy data")


def example2_different_timeframes():
    """Load data from different timeframes."""
    print("\n" + "=" * 70)
    print("Example 2: Different Timeframes")
    print("=" * 70)

    timeframes = ["M5", "M15", "H1", "H4", "D1"]

    for tf in timeframes:
        try:
            print(f"\nLoading {tf} data...")
            data = load_mt5("EURUSD", timeframe=tf, count=100)

            print(f"  Loaded {len(data):,} bars")
            print(f"  Date range: {data.index[0]} to {data.index[-1]}")

            # Calculate timeframe duration
            duration = data.index[-1] - data.index[0]
            print(f"  Duration: {duration.days} days, {duration.seconds // 3600} hours")

        except Exception as e:
            print(f"  Error: {e}")


def example3_date_range_loading():
    """Load data for specific date range."""
    print("\n" + "=" * 70)
    print("Example 3: Date Range Loading")
    print("=" * 70)

    # Load November 2025 data
    start = datetime(2025, 11, 3)
    end = datetime(2025, 11, 30)

    print(f"\nLoading data from {start.date()} to {end.date()}...")

    try:
        data = load_mt5("EURUSD", timeframe="H1", start_date=start, end_date=end)

        print(f"\nLoaded {len(data):,} H1 bars")
        print(f"Actual date range: {data.index[0]} to {data.index[-1]}")

        # Calculate statistics
        total_return = (data["close"].iloc[-1] / data["close"].iloc[0] - 1) * 100
        print(f"\nNovember 2025 Performance:")
        print(f"  Total return: {total_return:+.2f}%")
        print(f"  High: {data['high'].max():.5f}")
        print(f"  Low: {data['low'].min():.5f}")
        print(f"  Avg volume: {data['volume'].mean():.0f}")

    except Exception as e:
        print(f"\nError: {e}")


def example4_fallback_mechanism():
    """Demonstrate automatic fallback to Dukascopy."""
    print("\n" + "=" * 70)
    print("Example 4: Automatic Fallback Mechanism")
    print("=" * 70)

    print("\nThe load_mt5() function automatically falls back to Dukascopy")
    print("if MT5 connection fails. Let's test this...")

    try:
        # This will try MT5 first, then fall back to Dukascopy if needed
        data = load_mt5("EURUSD", timeframe="H1", count=500)

        print(f"\nSuccessfully loaded {len(data):,} bars")
        print(f"Date range: {data.index[0]} to {data.index[-1]}")

        print("\nNote: If MT5 was unavailable, this data came from Dukascopy")
        print("Check the log messages above to see which source was used")

    except Exception as e:
        print(f"\nBoth MT5 and Dukascopy failed: {e}")


def example5_compare_sources():
    """Compare data from MT5 and Dukascopy."""
    print("\n" + "=" * 70)
    print("Example 5: Comparing MT5 vs Dukascopy Data")
    print("=" * 70)

    # Load same period from both sources
    start_date = "2025-11-01"
    end_date = "2025-11-30"

    print(f"\nLoading {start_date} to {end_date} from both sources...")

    try:
        # Load from Dukascopy
        print("\n1. Loading from Dukascopy...")
        duka_data = load_dukascopy("EURUSD", start_date=start_date, end_date=end_date)
        print(f"   Dukascopy: {len(duka_data):,} bars")

        # Load from MT5 (will fallback to Dukascopy if MT5 unavailable)
        print("\n2. Loading from MT5...")
        start_dt = datetime.strptime(start_date, "%Y-%m-%d")
        end_dt = datetime.strptime(end_date, "%Y-%m-%d")
        mt5_data = load_mt5("EURUSD", timeframe="M1", start_date=start_dt, end_date=end_dt)
        print(f"   MT5: {len(mt5_data):,} bars")

        # Compare
        print("\n3. Comparison:")
        print(f"   Bar count difference: {abs(len(duka_data) - len(mt5_data)):,}")

        if len(duka_data) > 0 and len(mt5_data) > 0:
            # Compare first common timestamp
            common_start = max(duka_data.index[0], mt5_data.index[0])
            common_end = min(duka_data.index[-1], mt5_data.index[-1])

            duka_subset = duka_data.loc[common_start:common_end]
            mt5_subset = mt5_data.loc[common_start:common_end]

            print(f"   Common period: {common_start} to {common_end}")
            print(f"   Dukascopy bars: {len(duka_subset):,}")
            print(f"   MT5 bars: {len(mt5_subset):,}")

    except Exception as e:
        print(f"\nError: {e}")


def example6_best_practices():
    """Demonstrate best practices for MT5 data loading."""
    print("\n" + "=" * 70)
    print("Example 6: Best Practices")
    print("=" * 70)

    print("\nBest Practices for MT5 Data Loading:")

    print("\n1. Always handle connection errors:")
    print("   try:")
    print("       data = load_mt5('EURUSD', timeframe='H1', count=1000)")
    print("   except Exception as e:")
    print("       logger.error(f'Failed to load data: {e}')")

    print("\n2. Use appropriate timeframes:")
    print("   - M1/M5: For scalping strategies (large data)")
    print("   - H1/H4: For intraday/swing strategies (moderate data)")
    print("   - D1: For position trading (small data)")

    print("\n3. Limit data size:")
    print("   - Use count parameter to limit bars")
    print("   - Or use start_date/end_date for specific periods")
    print("   - Avoid loading years of M1 data (memory intensive)")

    print("\n4. Leverage automatic fallback:")
    print("   - load_mt5() automatically falls back to Dukascopy")
    print("   - No need for manual fallback logic")
    print("   - Check logs to see which source was used")

    print("\n5. Validate data before backtesting:")
    print("   - Check for missing values: data.isnull().sum()")
    print("   - Verify date range: data.index[0], data.index[-1]")
    print("   - Confirm bar count: len(data)")

    # Demonstrate validation
    print("\n6. Example validation:")
    try:
        data = load_mt5("EURUSD", timeframe="H1", count=100)

        print(f"   Loaded: {len(data)} bars")
        print(f"   Date range: {data.index[0]} to {data.index[-1]}")
        print(f"   Missing values: {data.isnull().sum().sum()}")
        print(f"   Columns: {list(data.columns)}")

        if len(data) > 0 and data.isnull().sum().sum() == 0:
            print("   Status: READY FOR BACKTESTING")
        else:
            print("   Status: NEEDS ATTENTION")

    except Exception as e:
        print(f"   Error: {e}")


def main():
    """Run all examples."""
    print("\n" + "=" * 70)
    print("MT5 DATA LOADING EXAMPLES")
    print("=" * 70)

    print("\nPrerequisites:")
    print("1. MT5 terminal installed and running")
    print("2. Valid credentials in settings/config.ini")
    print("3. Section: [MT5-Pepperstone-demo]")
    print("\nIf MT5 is not available, examples will use Dukascopy fallback")

    try:
        example1_basic_mt5()
        example2_different_timeframes()
        example3_date_range_loading()
        example4_fallback_mechanism()
        example5_compare_sources()
        example6_best_practices()

        print("\n" + "=" * 70)
        print("ALL EXAMPLES COMPLETED")
        print("=" * 70)

        print("\nKey Takeaways:")
        print("1. load_mt5() connects to MT5 for real-time/historical data")
        print("2. Supports multiple timeframes (M1, M5, H1, H4, D1, etc.)")
        print("3. Can load by count or date range")
        print("4. Automatically falls back to Dukascopy if MT5 unavailable")
        print("5. Always validate data before backtesting")

        print("\nNext Steps:")
        print("- Try 03_data_preprocessing.py for data cleaning")
        print("- Explore 04_multi_timeframe.py for multi-TF strategies")
        print("- Learn custom data sources in 05_custom_data_source.py")

    except Exception as e:
        logger.error(f"Error running examples: {e}")
        import traceback

        traceback.print_exc()


if __name__ == "__main__":
    main()

