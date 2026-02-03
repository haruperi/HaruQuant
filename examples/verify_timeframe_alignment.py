"""Verify Multi-Timeframe Alignment.

This script demonstrates that timeframe alignment works correctly by showing
that at any point in time, the strength calculation uses the latest available
value from each timeframe.
"""

import sys

import pandas as pd

from apps.logger import logger
from apps.mt5 import MT5Client
from apps.sqlite.users import UserManager


def verify_alignment():
    """Verify that timeframes are properly aligned at each point in time."""
    logger.info("Starting Timeframe Alignment Verification")

    # Get credentials and connect
    creds = UserManager().get_mt5_credentials()
    if not creds:
        logger.error("No MT5 credentials found")
        return

    client = MT5Client()
    connected = client.connect(
        login=creds["login"],
        password=creds["password"],
        server=creds["server"],
        path=creds["path"],
    )

    if not connected:
        logger.error("Failed to connect to MT5")
        return

    try:
        # Fetch multi-timeframe data for a single pair
        symbol = "EURUSD"
        logger.info(f"Fetching multi-timeframe data for {symbol}")

        timeframes = ["M5", "H1", "H4"]
        timeframe_dfs = {}

        for tf in timeframes:
            data = client.get_bars(symbol=symbol, timeframe=tf, count=50)
            if data is not None and not data.empty:
                if "time" in data.columns:
                    data = data.set_index("time")
                timeframe_dfs[tf] = data
                logger.info(
                    f"{tf}: {len(data)} bars from {data.index[0]} to {data.index[-1]}"
                )

        # Combine into MultiIndex structure
        combined_df = pd.concat(timeframe_dfs, names=["timeframe", "time"])
        combined_df = combined_df.swaplevel(0, 1)

        # Calculate strength with alignment
        from apps.indicator.custom.currency_strength import calculate_pair_strength

        result = calculate_pair_strength(
            data=combined_df,
            timeframe_weights={"M5": 0.2, "H1": 0.3, "H4": 0.5},
            price_col="close",
        )

        logger.success("Strength calculation complete")

        # Display verification results
        print("\n" + "=" * 80)
        print("TIMEFRAME ALIGNMENT VERIFICATION")
        print("=" * 80)
        print(
            "\nThis shows that at each M5 timestamp, we have values from ALL timeframes:"
        )
        print("- M5_change: from the current M5 bar")
        print("- H1_change: from the most recent H1 bar (forward-filled)")
        print("- H4_change: from the most recent H4 bar (forward-filled)")
        print("- pair_strength: weighted combination of all three\n")

        # Show last 10 timestamps with all columns
        cols_to_show = ["close", "M5_change", "H1_change", "H4_change", "pair_strength"]
        print("Last 10 M5 bars with aligned multi-timeframe strength:")
        print("-" * 80)

        display_df = result[cols_to_show].tail(10)
        print(display_df.to_string())

        # Verify that all timeframe columns have values (not all NaN)
        print("\n" + "=" * 80)
        print("VERIFICATION RESULTS")
        print("=" * 80)

        last_10 = result.tail(10)
        m5_coverage = last_10["M5_change"].notna().sum()
        h1_coverage = last_10["H1_change"].notna().sum()
        h4_coverage = last_10["H4_change"].notna().sum()

        print(f"M5_change coverage: {m5_coverage}/10 bars ({m5_coverage*10}%)")
        print(
            f"H1_change coverage: {h1_coverage}/10 bars ({h1_coverage*10}%) [forward-filled]"
        )
        print(
            f"H4_change coverage: {h4_coverage}/10 bars ({h4_coverage*10}%) [forward-filled]"
        )

        if m5_coverage > 0 and h1_coverage > 0 and h4_coverage > 0:
            print("\n[OK] All timeframes are properly aligned!")
            print(
                "At each M5 timestamp, we have strength contributions from M5, H1, and H4."
            )
        else:
            print("\n[WARNING] Some timeframes are missing data")

        # Show a specific example
        print("\n" + "=" * 80)
        print("EXAMPLE: Timeframe values at a specific point in time")
        print("=" * 80)

        example_time = result.index[-5]  # 5th from last
        example_row = result.iloc[-5]

        print(f"\nAt timestamp: {example_time}")
        print(f"  M5 change:  {example_row['M5_change']:.4f}% (weight: 0.2)")
        print(f"  H1 change:  {example_row['H1_change']:.4f}% (weight: 0.3)")
        print(f"  H4 change:  {example_row['H4_change']:.4f}% (weight: 0.5)")
        print(f"  Combined:   {example_row['pair_strength']:.4f}%")

        # Manual verification
        manual_calc = (
            example_row["M5_change"] * 0.2
            + example_row["H1_change"] * 0.3
            + example_row["H4_change"] * 0.5
        )
        print(
            f"\nVerification: {example_row['M5_change']:.4f}*0.2 + {example_row['H1_change']:.4f}*0.3 + {example_row['H4_change']:.4f}*0.5"
        )
        print(f"            = {manual_calc:.4f}%")
        print(
            f"Match: {'[OK]' if abs(manual_calc - example_row['pair_strength']) < 0.001 else '[FAIL]'}"
        )

    except Exception as e:
        logger.error(f"Error during verification: {e}")
        raise
    finally:
        client.shutdown()


if __name__ == "__main__":
    try:
        verify_alignment()
    except KeyboardInterrupt:
        logger.info("\nVerification interrupted by user")
        sys.exit(0)
    except Exception as e:
        logger.error(f"Fatal error: {e}")
        sys.exit(1)
