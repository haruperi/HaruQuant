"""
Data Manipulator Usage Examples

Purpose:
- Demonstrate timeframe resampling (M1 -> M5 -> H1 -> D1)
- Show real-time bar aggregation for live trading
- Illustrate multi-timeframe data management
- Examples for signal mapping across timeframes

Key Concepts:
- TimeframeManager for OHLCV resampling
- BarAggregator for incremental tick aggregation
- Multi-timeframe analysis
- Signal mapping from higher to lower timeframes

Usage:
    python tests/usage/utils/usage_data_manipulator.py
"""

import sys
from pathlib import Path
from datetime import datetime, timedelta

# Add project root to path
project_root = Path(__file__).parent.parent.parent.parent
sys.path.insert(0, str(project_root))

from apps.utils.data_manipulator import TimeframeManager, BarAggregator, create_signal_mapping
from apps.utils.data_getters import load_dukascopy
from apps.utils.logger import logger
import pandas as pd
import numpy as np


def example_01_basic_resampling():
    """Example 1: Basic timeframe resampling."""
    logger.info("=" * 70)
    logger.info("EXAMPLE 1: Basic Timeframe Resampling")
    logger.info("=" * 70)

    logger.info("Loading M1 data...")

    try:
        m1_data = load_dukascopy(
            symbol="EURUSD",
            timeframe="M1",
            count=300,  # 5 hours of M1 data
            cache=True
        )

        logger.info(f"M1 data loaded: {len(m1_data)} bars")

        manager = TimeframeManager()

        # Resample to M5
        m5_data = manager.resample(m1_data, target_timeframe='M5', source_timeframe='M1')

        logger.info(f"\nResampling results:")
        logger.info(f"  M1 bars: {len(m1_data)}")
        logger.info(f"  M5 bars: {len(m5_data)} (expected ~{len(m1_data)//5})")

        logger.info(f"\nM1 first bar: {m1_data.index[0]} - Close: {m1_data['close'].iloc[0]:.5f}")
        logger.info(f"M5 first bar: {m5_data.index[0]} - Close: {m5_data['close'].iloc[0]:.5f}")

    except Exception as e:
        logger.error(f"Failed: {e}")


def example_02_multi_timeframe_resampling():
    """Example 2: Resample to multiple timeframes at once."""
    logger.info("\n" + "=" * 70)
    logger.info("EXAMPLE 2: Multi-Timeframe Resampling")
    logger.info("=" * 70)

    logger.info("Loading M1 data...")

    try:
        m1_data = load_dukascopy(
            symbol="EURUSD",
            timeframe="M1",
            count=1440,  # 1 day of M1 data
            cache=True
        )

        manager = TimeframeManager()

        # Resample to multiple timeframes
        results = manager.resample_multi_timeframe(
            m1_data,
            source_timeframe='M1',
            target_timeframes=['M5', 'M15', 'M30', 'H1', 'H4']
        )

        logger.info(f"\nOriginal M1: {len(m1_data)} bars")

        for tf, df in results.items():
            logger.info(f"{tf}: {len(df)} bars")

        # Compare OHLC across timeframes
        logger.info(f"\nFirst bar comparison:")
        for tf in ['M5', 'M15', 'H1']:
            if tf in results:
                df = results[tf]
                logger.info(f"  {tf} - O:{df['open'].iloc[0]:.5f} H:{df['high'].iloc[0]:.5f} "
                          f"L:{df['low'].iloc[0]:.5f} C:{df['close'].iloc[0]:.5f}")

    except Exception as e:
        logger.error(f"Failed: {e}")


def example_03_timeframe_validation():
    """Example 3: Timeframe validation and conversions."""
    logger.info("\n" + "=" * 70)
    logger.info("EXAMPLE 3: Timeframe Validation")
    logger.info("=" * 70)

    manager = TimeframeManager()

    # Test timeframe validation
    timeframes = ['M1', 'M5', 'H1', 'D1', 'INVALID']

    logger.info("Validating timeframes:")
    for tf in timeframes:
        is_valid = manager.validate_timeframe(tf)
        logger.info(f"  {tf}: {'Valid' if is_valid else 'Invalid'}")

    # Test timeframe to frequency conversion
    logger.info("\nTimeframe to pandas frequency:")
    valid_tfs = ['M1', 'M5', 'M15', 'M30', 'H1', 'H4', 'D1']
    for tf in valid_tfs:
        freq = manager.timeframe_to_frequency(tf)
        logger.info(f"  {tf} -> {freq}")

    # Test resampling possibility
    logger.info("\nCan resample checks:")
    tests = [
        ('M1', 'M5'),
        ('M1', 'H1'),
        ('H1', 'M1'),  # Invalid
        ('M5', 'M15'),
    ]
    for from_tf, to_tf in tests:
        can_resample = manager.can_resample(from_tf, to_tf)
        logger.info(f"  {from_tf} -> {to_tf}: {'Yes' if can_resample else 'No'}")


def example_04_bar_aggregator_ticks():
    """Example 4: Aggregate ticks into bars."""
    logger.info("\n" + "=" * 70)
    logger.info("EXAMPLE 4: Bar Aggregation from Ticks")
    logger.info("=" * 70)

    # Create bar aggregator for M5 bars
    aggregator = BarAggregator(target_timeframe='M5')

    # Simulate ticks
    base_time = datetime(2025, 1, 1, 10, 0, 0)
    logger.info("Simulating tick stream...")

    completed_bars = []

    for minute in range(12):  # 12 minutes = 2 complete M5 bars
        for second in range(0, 60, 10):  # Tick every 10 seconds
            timestamp = base_time + timedelta(minutes=minute, seconds=second)
            price = 1.1000 + (minute * 0.0001) + np.random.normal(0, 0.0001)
            volume = np.random.randint(1, 10)

            # Add tick
            completed_bar = aggregator.add_tick(
                timestamp=timestamp,
                price=price,
                volume=volume
            )

            if completed_bar:
                completed_bars.append(completed_bar)
                logger.info(f"\nCompleted M5 bar:")
                logger.info(f"  Time: {completed_bar['Datetime']}")
                logger.info(f"  O:{completed_bar['Open']:.5f} H:{completed_bar['High']:.5f} "
                          f"L:{completed_bar['Low']:.5f} C:{completed_bar['Close']:.5f}")
                logger.info(f"  Volume: {completed_bar['Volume']:.2f}")

    logger.info(f"\nTotal completed bars: {len(completed_bars)}")

    # Get current incomplete bar
    current_bar = aggregator.get_current_bar()
    if current_bar:
        logger.info(f"\nCurrent incomplete bar:")
        logger.info(f"  Time: {current_bar['Datetime']}")
        logger.info(f"  Close: {current_bar['Close']:.5f}")


def example_05_bar_aggregator_from_bars():
    """Example 5: Aggregate smaller bars into larger bars."""
    logger.info("\n" + "=" * 70)
    logger.info("EXAMPLE 5: Aggregate M1 to M5 Bars")
    logger.info("=" * 70)

    logger.info("Loading M1 data...")

    try:
        m1_data = load_dukascopy(
            symbol="EURUSD",
            timeframe="M1",
            count=25,
            cache=True
        )

        aggregator = BarAggregator(target_timeframe='M5')

        logger.info(f"Processing {len(m1_data)} M1 bars...")

        completed_m5_bars = []

        for timestamp, row in m1_data.iterrows():
            completed_bar = aggregator.add_bar(
                timestamp=timestamp,
                open_price=row['open'],
                high_price=row['high'],
                low_price=row['low'],
                close_price=row['close'],
                volume=row['volume']
            )

            if completed_bar:
                completed_m5_bars.append(completed_bar)

        logger.info(f"\nCompleted M5 bars: {len(completed_m5_bars)}")

        for i, bar in enumerate(completed_m5_bars, 1):
            logger.info(f"\nM5 Bar {i}:")
            logger.info(f"  Time: {bar['Datetime']}")
            logger.info(f"  OHLC: {bar['Open']:.5f}/{bar['High']:.5f}/{bar['Low']:.5f}/{bar['Close']:.5f}")
            logger.info(f"  Volume: {bar['Volume']:.0f}")

    except Exception as e:
        logger.error(f"Failed: {e}")


def example_06_signal_mapping():
    """Example 6: Map signals from H1 to M1 timeframe."""
    logger.info("\n" + "=" * 70)
    logger.info("EXAMPLE 6: Signal Mapping Across Timeframes")
    logger.info("=" * 70)

    # Create H1 data with signals
    h1_dates = pd.date_range('2025-01-01 00:00:00', periods=10, freq='1h')
    h1_data = pd.DataFrame({
        'open': np.random.uniform(1.10, 1.11, 10),
        'high': np.random.uniform(1.11, 1.12, 10),
        'low': np.random.uniform(1.09, 1.10, 10),
        'close': np.random.uniform(1.10, 1.11, 10),
        'volume': np.random.randint(100, 200, 10),
        'EntrySignal': [0, 0, 1, 0, -1, 0, 0, 1, 0, 0],  # Buy/Sell signals
        'ExitSignal': [0, 0, 0, 0, 0, 1, 0, 0, 0, 1],
        'SL': [0, 0, 1.0950, 0, 1.1150, 0, 0, 1.0960, 0, 0],
        'TP': [0, 0, 1.1050, 0, 1.1050, 0, 0, 1.1060, 0, 0],
    }, index=h1_dates)

    # Create corresponding M1 data
    m1_dates = pd.date_range('2025-01-01 00:00:00', periods=600, freq='1min')  # 10 hours
    m1_data = pd.DataFrame({
        'open': np.random.uniform(1.10, 1.11, 600),
        'high': np.random.uniform(1.11, 1.12, 600),
        'low': np.random.uniform(1.09, 1.10, 600),
        'close': np.random.uniform(1.10, 1.11, 600),
        'volume': np.random.randint(100, 200, 600),
    }, index=m1_dates)

    logger.info(f"H1 data: {len(h1_data)} bars with signals")
    logger.info(f"M1 data: {len(m1_data)} bars")

    # Create signal mapping
    signal_map = create_signal_mapping(h1_data, m1_data)

    logger.info(f"\nSignal map created: {len(signal_map)} M1 timestamps")

    # Show some mapped signals
    logger.info("\nSample signal mappings:")
    count = 0
    for timestamp, signals in signal_map.items():
        if signals['EntrySignal'] != 0 and count < 5:
            logger.info(f"\n  M1 Timestamp: {timestamp}")
            logger.info(f"  Entry Signal: {signals['EntrySignal']}")
            logger.info(f"  Exit Signal: {signals['ExitSignal']}")
            logger.info(f"  SL: {signals['SL']:.5f}")
            logger.info(f"  TP: {signals['TP']:.5f}")
            count += 1


def example_07_ohlc_preservation():
    """Example 7: Verify OHLC preservation during resampling."""
    logger.info("\n" + "=" * 70)
    logger.info("EXAMPLE 7: OHLC Preservation Verification")
    logger.info("=" * 70)

    logger.info("Loading M1 data...")

    try:
        m1_data = load_dukascopy(
            symbol="EURUSD",
            timeframe="M1",
            count=60,  # 1 hour
            cache=True
        )

        manager = TimeframeManager()

        # Resample to H1
        h1_data = manager.resample(m1_data, target_timeframe='H1', source_timeframe='M1')

        logger.info(f"\nM1 data: {len(m1_data)} bars")
        logger.info(f"H1 data: {len(h1_data)} bars")

        if len(h1_data) > 0:
            # Verify OHLC relationships
            h1_bar = h1_data.iloc[0]
            m1_subset = m1_data.iloc[:60]

            logger.info(f"\nH1 Bar OHLC:")
            logger.info(f"  Open: {h1_bar['open']:.5f}")
            logger.info(f"  High: {h1_bar['high']:.5f}")
            logger.info(f"  Low: {h1_bar['low']:.5f}")
            logger.info(f"  Close: {h1_bar['close']:.5f}")
            logger.info(f"  Volume: {h1_bar['volume']:.0f}")

            logger.info(f"\nM1 Bars (first 60) OHLC:")
            logger.info(f"  First Open: {m1_subset['open'].iloc[0]:.5f}")
            logger.info(f"  Highest High: {m1_subset['high'].max():.5f}")
            logger.info(f"  Lowest Low: {m1_subset['low'].min():.5f}")
            logger.info(f"  Last Close: {m1_subset['close'].iloc[-1]:.5f}")
            logger.info(f"  Total Volume: {m1_subset['volume'].sum():.0f}")

            # Verify correctness
            logger.info(f"\nVerification:")
            logger.info(f"  Open matches: {abs(h1_bar['open'] - m1_subset['open'].iloc[0]) < 0.00001}")
            logger.info(f"  High matches: {abs(h1_bar['high'] - m1_subset['high'].max()) < 0.00001}")
            logger.info(f"  Low matches: {abs(h1_bar['low'] - m1_subset['low'].min()) < 0.00001}")
            logger.info(f"  Close matches: {abs(h1_bar['close'] - m1_subset['close'].iloc[-1]) < 0.00001}")
            logger.info(f"  Volume matches: {abs(h1_bar['volume'] - m1_subset['volume'].sum()) < 0.01}")

    except Exception as e:
        logger.error(f"Failed: {e}")


def example_08_spread_handling():
    """Example 8: Spread handling during resampling."""
    logger.info("\n" + "=" * 70)
    logger.info("EXAMPLE 8: Spread Handling in Resampling")
    logger.info("=" * 70)

    logger.info("Loading M1 data...")

    try:
        m1_data = load_dukascopy(
            symbol="EURUSD",
            timeframe="M1",
            count=300,
            cache=True
        )

        manager = TimeframeManager()

        # Resample to M5
        m5_data = manager.resample(m1_data, target_timeframe='M5')

        logger.info(f"\nSpread statistics:")
        logger.info(f"M1 spread - Mean: {m1_data['spread'].mean():.5f}, "
                   f"Min: {m1_data['spread'].min():.5f}, Max: {m1_data['spread'].max():.5f}")
        logger.info(f"M5 spread - Mean: {m5_data['spread'].mean():.5f}, "
                   f"Min: {m5_data['spread'].min():.5f}, Max: {m5_data['spread'].max():.5f}")

        logger.info("\nNote: M5 spread uses last value of each 5-minute period")

    except Exception as e:
        logger.error(f"Failed: {e}")


def example_09_live_trading_simulation():
    """Example 9: Simulate live trading with bar aggregation."""
    logger.info("\n" + "=" * 70)
    logger.info("EXAMPLE 9: Live Trading Simulation")
    logger.info("=" * 70)

    # Create aggregators for multiple timeframes
    aggregators = {
        'M5': BarAggregator('M5'),
        'M15': BarAggregator('M15'),
        'H1': BarAggregator('H1'),
    }

    logger.info("Simulating live tick stream with multiple timeframe aggregation...")

    base_time = datetime(2025, 1, 1, 10, 0, 0)

    for minute in range(75):  # 75 minutes
        timestamp = base_time + timedelta(minutes=minute)
        price = 1.1000 + np.random.normal(0, 0.0010)

        for tf_name, aggregator in aggregators.items():
            completed = aggregator.add_tick(timestamp=timestamp, price=price, volume=1.0)

            if completed:
                logger.info(f"\n{tf_name} bar completed at {completed['Datetime']}")
                logger.info(f"  OHLC: {completed['Open']:.5f}/{completed['High']:.5f}/"
                          f"{completed['Low']:.5f}/{completed['Close']:.5f}")

    # Show current bars
    logger.info("\nCurrent incomplete bars:")
    for tf_name, aggregator in aggregators.items():
        current = aggregator.get_current_bar()
        if current:
            logger.info(f"  {tf_name}: Close = {current['Close']:.5f} at {current['Datetime']}")


def example_10_performance_comparison():
    """Example 10: Compare resampling vs bar aggregation performance."""
    logger.info("\n" + "=" * 70)
    logger.info("EXAMPLE 10: Performance Comparison")
    logger.info("=" * 70)

    import time

    logger.info("Loading M1 data...")

    try:
        m1_data = load_dukascopy(
            symbol="EURUSD",
            timeframe="M1",
            count=1000,
            cache=True
        )

        # Method 1: TimeframeManager resampling (vectorized)
        logger.info("\nMethod 1: Vectorized resampling...")
        manager = TimeframeManager()

        start = time.time()
        m5_vectorized = manager.resample(m1_data, 'M5', 'M1')
        vectorized_time = time.time() - start

        logger.info(f"  Time: {vectorized_time:.4f} seconds")
        logger.info(f"  Bars created: {len(m5_vectorized)}")

        # Method 2: BarAggregator (iterative)
        logger.info("\nMethod 2: Iterative bar aggregation...")
        aggregator = BarAggregator('M5')

        start = time.time()
        for timestamp, row in m1_data.iterrows():
            aggregator.add_bar(
                timestamp=timestamp,
                open_price=row['open'],
                high_price=row['high'],
                low_price=row['low'],
                close_price=row['close'],
                volume=row['volume']
            )
        completed = aggregator.get_completed_bars()
        iterative_time = time.time() - start

        logger.info(f"  Time: {iterative_time:.4f} seconds")
        logger.info(f"  Bars created: {len(completed)}")

        logger.info(f"\nSpeed comparison:")
        logger.info(f"  Vectorized: {vectorized_time:.4f}s")
        logger.info(f"  Iterative: {iterative_time:.4f}s")
        logger.info(f"  Speedup: {iterative_time/vectorized_time:.1f}x")

        logger.info("\nRecommendation:")
        logger.info("  - Use TimeframeManager for historical data (faster)")
        logger.info("  - Use BarAggregator for live/streaming data (real-time)")

    except Exception as e:
        logger.error(f"Failed: {e}")


def main():
    """Run all data manipulator examples."""
    logger.info("\n" + "=" * 80)
    logger.info("DATA MANIPULATOR - COMPREHENSIVE USAGE EXAMPLES")
    logger.info("=" * 80)

    example_01_basic_resampling()
    example_02_multi_timeframe_resampling()
    example_03_timeframe_validation()
    example_04_bar_aggregator_ticks()
    example_05_bar_aggregator_from_bars()
    example_06_signal_mapping()
    example_07_ohlc_preservation()
    example_08_spread_handling()
    example_09_live_trading_simulation()
    example_10_performance_comparison()

    logger.info("\n" + "=" * 80)
    logger.info("ALL EXAMPLES COMPLETED")
    logger.info("=" * 80)

    logger.info("\nKEY TAKEAWAYS:")
    logger.info("1. Use TimeframeManager.resample() for historical data conversion")
    logger.info("2. Use BarAggregator for live tick/bar aggregation")
    logger.info("3. Resampling preserves OHLC relationships correctly")
    logger.info("4. Can resample only to larger timeframes (M1->H1, not H1->M1)")
    logger.info("5. Signal mapping allows multi-timeframe strategies")
    logger.info("6. Vectorized resampling is much faster than iterative")


if __name__ == "__main__":
    main()

