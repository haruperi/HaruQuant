"""
Data Validator Usage Examples

Purpose:
- Demonstrate comprehensive data quality validation for market data
- Show price sanity checks (OHLC relationships)
- Illustrate gap detection, spike detection, and anomaly marking
- Examples for missing timestamp detection and data cleaning
- Generate quality reports and visualizations

Key Concepts:
- Price sanity validation (High >= Low, Close within range)
- Gap detection in time series
- Spike/anomaly detection using statistical methods
- Missing timestamps and duplicate detection
- Data quality reporting and scoring
- Automated data cleaning

Usage:
    python tests/usage/utils/usage_data_validator.py
"""

import sys
from pathlib import Path
from datetime import datetime, timedelta

# Add project root to path
project_root = Path(__file__).parent.parent.parent.parent
sys.path.insert(0, str(project_root))

from apps.utils.data_validator import DataValidator, DataQualityReport
from apps.utils.data_getters import load_dukascopy
from apps.logger import logger
import pandas as pd
import numpy as np


def example_01_basic_price_sanity():
    """Example 1: Basic price sanity validation."""
    logger.info("=" * 70)
    logger.info("EXAMPLE 1: Basic Price Sanity Validation")
    logger.info("=" * 70)

    # Create sample data with some invalid prices
    dates = pd.date_range('2025-01-01', periods=10, freq='1h')
    data = pd.DataFrame({
        'open': [1.1000, 1.1010, 1.1020, 1.1015, 1.1030, 1.1025, 1.1040, 1.1035, 1.1050, 1.1045],
        'high': [1.1020, 1.1030, 1.1040, 1.1035, 1.1050, 1.1045, 1.1060, 1.1055, 1.1070, 1.1065],
        'low': [1.0990, 1.1000, 1.1010, 1.1005, 1.1020, 1.1015, 1.1030, 1.1025, 1.1040, 1.1035],
        'close': [1.1010, 1.1020, 1.1030, 1.1025, 1.1040, 1.1035, 1.1050, 1.1045, 1.1060, 1.1055],
        'volume': [100, 120, 110, 130, 125, 115, 140, 135, 150, 145],
        'spread': [0.0002, 0.0002, 0.0002, 0.0002, 0.0002, 0.0002, 0.0002, 0.0002, 0.0002, 0.0002],
    }, index=dates)

    # Introduce an invalid price (high < low)
    data.loc[dates[5], 'high'] = 1.1000  # Lower than low price

    validator = DataValidator()
    is_valid, df_marked, issues = validator.validate_price_sanity(data, mark_invalid=True)

    logger.info(f"Validation result: {'VALID' if is_valid else 'INVALID'}")
    logger.info(f"Issues found: {len(issues)}")

    for issue in issues:
        logger.info(f"\nIssue type: {issue['type']}")
        logger.info(f"Check: {issue['check']}")
        logger.info(f"Count: {issue['count']}")


def example_02_detect_gaps():
    """Example 2: Gap detection in time series."""
    logger.info("\n" + "=" * 70)
    logger.info("EXAMPLE 2: Gap Detection")
    logger.info("=" * 70)

    # Create data with gaps
    dates = []
    for i in range(20):
        if i in [5, 6, 7, 15]:  # Skip these indices to create gaps
            continue
        dates.append(datetime(2025, 1, 1) + timedelta(hours=i))

    data = pd.DataFrame({
        'open': np.random.uniform(1.10, 1.11, len(dates)),
        'high': np.random.uniform(1.11, 1.12, len(dates)),
        'low': np.random.uniform(1.09, 1.10, len(dates)),
        'close': np.random.uniform(1.10, 1.11, len(dates)),
        'volume': np.random.randint(100, 200, len(dates)),
        'spread': [0.0002] * len(dates),
    }, index=pd.DatetimeIndex(dates))

    validator = DataValidator()
    gaps_df, gap_info = validator.detect_gaps(
        data,
        expected_frequency='1h',
        tolerance=1.5
    )

    logger.info(f"Gaps detected: {len(gap_info)}")

    for i, gap in enumerate(gap_info, 1):
        logger.info(f"\nGap {i}:")
        logger.info(f"  Start: {gap['gap_start']}")
        logger.info(f"  End: {gap['gap_end']}")
        logger.info(f"  Duration: {gap['duration']}")
        logger.info(f"  Expected periods: {gap['expected_periods']}")


def example_03_spike_detection():
    """Example 3: Spike and anomaly detection."""
    logger.info("\n" + "=" * 70)
    logger.info("EXAMPLE 3: Spike and Anomaly Detection")
    logger.info("=" * 70)

    # Create data with artificial spikes
    dates = pd.date_range('2025-01-01', periods=100, freq='1h')
    close_prices = np.random.normal(1.1000, 0.0020, 100)

    # Add spikes
    close_prices[20] = 1.1500  # Huge spike
    close_prices[50] = 1.0500  # Huge drop

    data = pd.DataFrame({
        'open': close_prices,
        'high': close_prices + 0.0010,
        'low': close_prices - 0.0010,
        'close': close_prices,
        'volume': np.random.randint(100, 200, 100),
        'spread': [0.0002] * 100,
    }, index=dates)

    validator = DataValidator(z_score_threshold=3.0, iqr_multiplier=1.5)

    # Detect using Z-score method
    df_marked, anomalies = validator.detect_spikes(
        data,
        columns=['close'],
        method='zscore',
        mark_anomalies=True
    )

    logger.info(f"Anomalies detected: {len(anomalies)}")

    for anomaly in anomalies:
        logger.info(f"\nAnomaly type: {anomaly['type']}")
        logger.info(f"Method: {anomaly['method']}")
        logger.info(f"Column: {anomaly['column']}")
        logger.info(f"Count: {anomaly['count']}")
        logger.info(f"Anomaly rows: {anomaly['rows'][:5]}")  # Show first 5


def example_04_missing_timestamps():
    """Example 4: Check for missing timestamps."""
    logger.info("\n" + "=" * 70)
    logger.info("EXAMPLE 4: Missing Timestamp Detection")
    logger.info("=" * 70)

    # Create incomplete dataset
    all_dates = pd.date_range('2025-01-01', '2025-01-02', freq='1h')
    # Remove some timestamps
    dates = all_dates.delete([5, 6, 12, 13, 14, 20])

    data = pd.DataFrame({
        'open': np.random.uniform(1.10, 1.11, len(dates)),
        'high': np.random.uniform(1.11, 1.12, len(dates)),
        'low': np.random.uniform(1.09, 1.10, len(dates)),
        'close': np.random.uniform(1.10, 1.11, len(dates)),
        'volume': np.random.randint(100, 200, len(dates)),
        'spread': [0.0002] * len(dates),
    }, index=dates)

    validator = DataValidator()
    missing_df, missing_info = validator.check_missing_timestamps(
        data,
        expected_frequency='1h'
    )

    logger.info(f"Missing timestamps: {len(missing_df) if not missing_df.empty else 0}")

    if missing_info:
        info = missing_info[0]
        logger.info(f"Expected total: {info['expected_total']}")
        logger.info(f"Actual total: {info['actual_total']}")
        logger.info(f"Coverage: {info['coverage'] * 100:.2f}%")
        logger.info(f"\nFirst few missing timestamps:")
        for ts in info['missing_timestamps'][:5]:
            logger.info(f"  {ts}")


def example_05_comprehensive_validation():
    """Example 5: Comprehensive data validation."""
    logger.info("\n" + "=" * 70)
    logger.info("EXAMPLE 5: Comprehensive Validation")
    logger.info("=" * 70)

    logger.info("Loading real market data...")

    try:
        data = load_dukascopy(
            symbol="EURUSD",
            timeframe="H1",
            count=200,
            cache=True
        )

        logger.info(f"Data loaded: {len(data)} bars")

        validator = DataValidator()

        # Run all validation checks
        results = validator.validate(
            data,
            checks=[
                'price_sanity',
                'gaps',
                'spikes',
                'missing_timestamps',
                'zero_volume',
                'duplicates',
                'spread'
            ],
            expected_frequency='1h'
        )

        logger.info(f"\nValidation Results:")
        logger.info(f"  Quality Score: {results['summary']['quality_score']:.2f}%")
        logger.info(f"  Total Issues: {results['summary']['total_issues']}")
        logger.info(f"  Valid: {results['summary']['is_valid']}")

        logger.info(f"\nChecks performed: {', '.join(results['checks_performed'])}")

        # Show summary for each check
        for check in results['checks_performed']:
            if check in results['summary']:
                logger.info(f"\n{check.upper()}:")
                check_summary = results['summary'][check]
                for key, value in check_summary.items():
                    if key not in ['gaps', 'anomalies']:  # Skip detailed lists
                        logger.info(f"  {key}: {value}")

    except Exception as e:
        logger.error(f"Failed: {e}")


def example_06_data_quality_report():
    """Example 6: Generate data quality report."""
    logger.info("\n" + "=" * 70)
    logger.info("EXAMPLE 6: Data Quality Report")
    logger.info("=" * 70)

    logger.info("Loading market data...")

    try:
        data = load_dukascopy(
            symbol="GBPUSD",
            timeframe="H1",
            count=300,
            cache=True
        )

        validator = DataValidator()

        # Get report object
        report = validator.validate(
            data,
            return_report=True,
            expected_frequency='1h'
        )

        if isinstance(report, DataQualityReport):
            logger.info(f"\n{report}")
            logger.info(f"\nTimestamp: {report.timestamp}")
            logger.info(f"Total Rows: {report.total_rows}")
            logger.info(f"Quality Score: {report.quality_score:.2f}%")
            logger.info(f"Is Valid: {report.is_valid}")

            logger.info(f"\nDetailed Metrics:")
            logger.info(f"  Price Sanity Valid: {report.price_sanity_valid}")
            logger.info(f"  Gaps Count: {report.gaps_count}")
            logger.info(f"  Anomalies Count: {report.anomalies_count}")
            logger.info(f"  Missing Timestamps: {report.missing_timestamps_count}")
            logger.info(f"  Zero Volume Count: {report.zero_volume_count}")
            logger.info(f"  Duplicates Count: {report.duplicates_count}")

            if report.spread_stats:
                logger.info(f"\nSpread Statistics:")
                logger.info(f"  Mean: {report.spread_stats.get('mean', 0):.5f}")
                logger.info(f"  Median: {report.spread_stats.get('median', 0):.5f}")
                logger.info(f"  Min: {report.spread_stats.get('min', 0):.5f}")
                logger.info(f"  Max: {report.spread_stats.get('max', 0):.5f}")

    except Exception as e:
        logger.error(f"Failed: {e}")


def example_07_data_cleaning():
    """Example 7: Clean data based on validation issues."""
    logger.info("\n" + "=" * 70)
    logger.info("EXAMPLE 7: Data Cleaning")
    logger.info("=" * 70)

    # Create dirty data
    dates = pd.date_range('2025-01-01', periods=100, freq='1h')
    data = pd.DataFrame({
        'open': np.random.uniform(1.10, 1.11, 100),
        'high': np.random.uniform(1.11, 1.12, 100),
        'low': np.random.uniform(1.09, 1.10, 100),
        'close': np.random.uniform(1.10, 1.11, 100),
        'volume': np.random.randint(100, 200, 100),
        'spread': np.random.uniform(0.0001, 0.0003, 100),
    }, index=dates)

    # Add some issues
    data.loc[dates[10], 'volume'] = 0  # Zero volume
    data.loc[dates[20], 'high'] = 1.0000  # Invalid price
    data = pd.concat([data, data.iloc[[5]]])  # Add duplicate

    logger.info(f"Original data: {len(data)} rows")

    validator = DataValidator()

    # Clean data
    cleaned, stats = validator.clean_data(
        data,
        remove_duplicates=True,
        remove_invalid_prices=True,
        remove_anomalies=False,
        remove_zero_volume=True,
        fill_gaps=False
    )

    logger.info(f"\nCleaning results:")
    logger.info(f"  Original rows: {stats['original_rows']}")
    logger.info(f"  Final rows: {stats['final_rows']}")
    logger.info(f"  Total removed: {stats['total_removed']}")
    logger.info(f"\nBreakdown:")
    logger.info(f"  Duplicates removed: {stats['duplicates_removed']}")
    logger.info(f"  Invalid prices removed: {stats['invalid_prices_removed']}")
    logger.info(f"  Anomalies removed: {stats['anomalies_removed']}")
    logger.info(f"  Zero volume removed: {stats['zero_volume_removed']}")


def example_08_zero_volume_detection():
    """Example 8: Detect zero or low volume bars."""
    logger.info("\n" + "=" * 70)
    logger.info("EXAMPLE 8: Zero Volume Detection")
    logger.info("=" * 70)

    # Create data with zero volumes
    dates = pd.date_range('2025-01-01', periods=50, freq='1h')
    data = pd.DataFrame({
        'open': np.random.uniform(1.10, 1.11, 50),
        'high': np.random.uniform(1.11, 1.12, 50),
        'low': np.random.uniform(1.09, 1.10, 50),
        'close': np.random.uniform(1.10, 1.11, 50),
        'volume': np.random.randint(100, 200, 50),
        'spread': [0.0002] * 50,
    }, index=dates)

    # Set some volumes to zero
    data.loc[dates[[5, 10, 15, 20]], 'volume'] = 0

    validator = DataValidator()
    zero_vol_df, issues = validator.detect_zero_volume(data, threshold=0.0)

    logger.info(f"Zero volume bars found: {len(zero_vol_df)}")

    if issues:
        logger.info(f"Issue count: {issues[0]['count']}")
        logger.info(f"Threshold: {issues[0]['threshold']}")


def example_09_duplicate_detection():
    """Example 9: Detect duplicate timestamps."""
    logger.info("\n" + "=" * 70)
    logger.info("EXAMPLE 9: Duplicate Timestamp Detection")
    logger.info("=" * 70)

    # Create data with duplicates
    dates = pd.date_range('2025-01-01', periods=30, freq='1h')
    data = pd.DataFrame({
        'open': np.random.uniform(1.10, 1.11, 30),
        'high': np.random.uniform(1.11, 1.12, 30),
        'low': np.random.uniform(1.09, 1.10, 30),
        'close': np.random.uniform(1.10, 1.11, 30),
        'volume': np.random.randint(100, 200, 30),
        'spread': [0.0002] * 30,
    }, index=dates)

    # Add duplicates
    duplicated_rows = data.iloc[[5, 10, 15]]
    data = pd.concat([data, duplicated_rows])

    validator = DataValidator()
    dup_df, issues = validator.detect_duplicates(data)

    logger.info(f"Duplicate rows found: {len(dup_df)}")

    if issues:
        logger.info(f"Total duplicates: {issues[0]['count']}")
        logger.info(f"Unique duplicate timestamps: {issues[0]['unique_timestamps']}")


def example_10_spread_analysis():
    """Example 10: Analyze spread statistics."""
    logger.info("\n" + "=" * 70)
    logger.info("EXAMPLE 10: Spread Analysis")
    logger.info("=" * 70)

    logger.info("Loading market data...")

    try:
        data = load_dukascopy(
            symbol="EURUSD",
            timeframe="H1",
            count=500,
            cache=True
        )

        validator = DataValidator()
        spread_stats, spread_issues = validator.analyze_spread(data)

        logger.info(f"\nSpread Statistics:")
        logger.info(f"  Mean: {spread_stats['mean']:.5f}")
        logger.info(f"  Median: {spread_stats['median']:.5f}")
        logger.info(f"  Std Dev: {spread_stats['std']:.5f}")
        logger.info(f"  Min: {spread_stats['min']:.5f}")
        logger.info(f"  Max: {spread_stats['max']:.5f}")
        logger.info(f"  Q25: {spread_stats['q25']:.5f}")
        logger.info(f"  Q75: {spread_stats['q75']:.5f}")

        if spread_issues:
            logger.info(f"\nSpread issues found: {len(spread_issues)}")
            for issue in spread_issues:
                logger.info(f"  Type: {issue['issue']}")
                logger.info(f"  Count: {issue['count']}")

    except Exception as e:
        logger.error(f"Failed: {e}")


def main():
    """Run all data validator examples."""
    logger.info("\n" + "=" * 80)
    logger.info("DATA VALIDATOR - COMPREHENSIVE USAGE EXAMPLES")
    logger.info("=" * 80)

    example_01_basic_price_sanity()
    example_02_detect_gaps()
    example_03_spike_detection()
    example_04_missing_timestamps()
    example_05_comprehensive_validation()
    example_06_data_quality_report()
    example_07_data_cleaning()
    example_08_zero_volume_detection()
    example_09_duplicate_detection()
    example_10_spread_analysis()

    logger.info("\n" + "=" * 80)
    logger.info("ALL EXAMPLES COMPLETED")
    logger.info("=" * 80)

    logger.info("\nKEY TAKEAWAYS:")
    logger.info("1. Use validate_price_sanity() to check OHLC relationships")
    logger.info("2. Use detect_gaps() to find missing data periods")
    logger.info("3. Use detect_spikes() for anomaly detection (zscore/iqr/mad methods)")
    logger.info("4. Use check_missing_timestamps() to verify data completeness")
    logger.info("5. Use validate() for comprehensive multi-check validation")
    logger.info("6. Use clean_data() to automatically fix common issues")
    logger.info("7. Quality reports provide overall data health metrics")


if __name__ == "__main__":
    main()
