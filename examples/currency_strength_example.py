"""Example usage of Currency Strength Indicator with Real MT5 Data.

This script demonstrates how to:
1. Connect to MT5 using stored credentials
2. Fetch real market data for multiple currency pairs
3. Calculate currency strength across all major currencies
4. Identify top trading opportunities (strong/weak pairs)
5. Display results in a formatted dashboard
"""

import sys

import pandas as pd

from apps.indicator.custom import (
    CURRENCY_PAIRS,
    MAJOR_CURRENCIES,
    currency_strength_indicator,
)
from apps.logger import logger
from apps.mt5 import MT5Client
from apps.sqlite.users import UserManager


def get_mt5_credentials():
    """Get MT5 credentials from the database."""
    creds = UserManager().get_mt5_credentials()
    if not creds:
        logger.error("No default broker credentials found")
        sys.exit(1)
    return creds


def fetch_all_pairs_data(client: MT5Client, pairs: list, bars: int = 100):
    """Fetch multi-timeframe data for all major currency pairs.

    Args:
        client: Connected MT5Client instance
        pairs: List of currency pairs to fetch
        bars: Number of bars to fetch per timeframe

    Returns:
        Dictionary mapping pair symbols to multi-timeframe DataFrames with MultiIndex
    """
    logger.info(f"Fetching multi-timeframe data for {len(pairs)} currency pairs...")

    pair_data = {}
    successful = 0
    failed = 0

    timeframes = ["M5", "H1", "H4"]

    for symbol in pairs:
        try:
            logger.debug(f"Fetching {symbol} across {len(timeframes)} timeframes...")

            # Fetch data for all timeframes
            timeframe_dfs = {}
            all_fetched = True

            for tf in timeframes:
                try:
                    data = client.get_bars(symbol=symbol, timeframe=tf, count=bars)

                    if data is not None and not data.empty:
                        # Ensure 'time' is the index
                        if "time" in data.columns:
                            data = data.set_index("time")

                        timeframe_dfs[tf] = data
                        logger.debug(f"  ✓ {tf}: {len(data)} bars")
                    else:
                        logger.warning(f"  ✗ {tf}: No data available")
                        all_fetched = False
                        break

                except Exception as e:
                    logger.warning(f"  ✗ {tf}: {str(e)}")
                    all_fetched = False
                    break

            # Only include pairs where all timeframes were successfully fetched
            if all_fetched and timeframe_dfs:
                # Combine all timeframes into a single DataFrame with MultiIndex
                # Use concat with keys to create (time, timeframe) MultiIndex
                combined_df = pd.concat(timeframe_dfs, names=["timeframe", "time"])

                # Swap levels so time is first, timeframe is second
                combined_df = combined_df.swaplevel(0, 1)

                pair_data[symbol] = combined_df
                successful += 1
                logger.success(f"✓ {symbol}: {len(timeframe_dfs)} timeframes fetched")
            else:
                failed += 1
                logger.warning(f"✗ {symbol}: Incomplete data")

        except Exception as e:
            failed += 1
            logger.error(f"✗ {symbol}: {str(e)}")
            continue

    logger.info(f"Fetch complete: {successful} successful, {failed} failed")
    return pair_data


def display_currency_strength_dashboard(result: dict):
    """Display currency strength results in a formatted dashboard.

    Args:
        result: Dictionary from currency_strength_indicator()
    """
    print("\n" + "=" * 80)
    print(" " * 15 + "MULTI-TIMEFRAME CURRENCY STRENGTH DASHBOARD")
    print(" " * 15 + "(M5: 20% | H1: 30% | H4: 50% - Short-Term)")
    print("=" * 80)

    # Currency Strength Section
    print("\n" + "-" * 80)
    print("CURRENCY STRENGTH RANKING")
    print("-" * 80)
    print(f"{'Currency':<12} {'Strength':<15} {'Rank':<10} {'Trend':<15}")
    print("-" * 80)

    strengths = result["latest_strengths"]
    ranks = result["latest_ranks"]

    # Sort by rank
    sorted_currencies = sorted(MAJOR_CURRENCIES, key=lambda c: ranks.get(c, 99))

    for currency in sorted_currencies:
        strength = strengths.get(currency, 0.0)
        rank = ranks.get(currency, "-")

        # Determine trend
        if strength > 0.5:
            trend = "++ STRONG BUY"
            strength_color = "+"
        elif strength > 0.2:
            trend = "+  BUY"
            strength_color = "+"
        elif strength < -0.5:
            trend = "-- STRONG SELL"
            strength_color = ""
        elif strength < -0.2:
            trend = "-  SELL"
            strength_color = ""
        else:
            trend = "=  NEUTRAL"
            strength_color = "+" if strength >= 0 else ""

        print(
            f"{currency:<12} {strength_color}{strength:>7.3f}%{'':>6} {rank:<10} {trend:<15}"
        )

    # Strong Pairs Section (LONG opportunities)
    if "strong_pairs" in result and result["strong_pairs"]:
        print("\n" + "-" * 80)
        print("STRONG PAIRS - LONG OPPORTUNITIES")
        print("-" * 80)
        print(f"{'Pair':<10} {'Base':<8} {'Quote':<8} {'Strength':<12} {'Signal':<10}")
        print("-" * 80)

        for pair_info in result["strong_pairs"]:
            print(
                f"{pair_info['pair']:<10} "
                f"{pair_info['base']:<8} "
                f"{pair_info['quote']:<8} "
                f"+{pair_info['strength']:>7.3f}%{'':>2} "
                f"{'[LONG]':<10}"
            )

    # Weak Pairs Section (SHORT opportunities)
    if "weak_pairs" in result and result["weak_pairs"]:
        print("\n" + "-" * 80)
        print("WEAK PAIRS - SHORT OPPORTUNITIES")
        print("-" * 80)
        print(f"{'Pair':<10} {'Base':<8} {'Quote':<8} {'Strength':<12} {'Signal':<10}")
        print("-" * 80)

        for pair_info in result["weak_pairs"]:
            print(
                f"{pair_info['pair']:<10} "
                f"{pair_info['base']:<8} "
                f"{pair_info['quote']:<8} "
                f"{pair_info['strength']:>7.3f}%{'':>2} "
                f"{'[SHORT]':<10}"
            )

    print("\n" + "=" * 80)
    print(
        f"Analysis complete | Total currencies: {len(MAJOR_CURRENCIES)} | "
        f"Pairs analyzed: {len(result.get('strong_pairs', [])) + len(result.get('weak_pairs', []))}"
    )
    print("=" * 80 + "\n")


def main():
    """Execute currency strength analysis example."""
    logger.info("Starting Currency Strength Analysis Example")

    # Step 1: Get MT5 credentials from database
    logger.info("Loading MT5 credentials from database...")
    creds = get_mt5_credentials()

    # Step 2: Initialize and connect to MT5
    logger.info("Connecting to MT5...")
    client = MT5Client()
    connected = client.connect(
        login=creds["login"],
        password=creds["password"],
        server=creds["server"],
        path=creds["path"],
    )

    if not connected:
        logger.error("Failed to connect to MT5. Please ensure MT5 terminal is running.")
        sys.exit(1)

    logger.success(f"Connected to MT5: {creds['server']}")

    try:
        # Step 3: Fetch data for major pairs
        print("\n[*] Fetching market data from MT5...")

        # Use first 15 pairs for faster demo, or all 28 for complete analysis
        # pairs_to_fetch = CURRENCY_PAIRS[:15]
        pairs_to_fetch = CURRENCY_PAIRS  # Uncomment for all pairs

        pair_data = fetch_all_pairs_data(client=client, pairs=pairs_to_fetch, bars=100)

        if not pair_data:
            logger.error("No data fetched. Exiting.")
            return

        logger.info(f"Successfully fetched data for {len(pair_data)} pairs")

        # Verify multi-timeframe structure
        first_pair = list(pair_data.keys())[0]
        first_df = pair_data[first_pair]
        if (
            isinstance(first_df.index, pd.MultiIndex)
            and "timeframe" in first_df.index.names
        ):
            timeframes_found = (
                first_df.index.get_level_values("timeframe").unique().tolist()
            )
            logger.success(f"✓ Multi-timeframe data verified: {timeframes_found}")
            print(
                f"\n[OK] Multi-timeframe analysis enabled: {', '.join(timeframes_found)}"
            )
        else:
            logger.warning("⚠ Single timeframe data detected - weights will be ignored")

        # Step 4: Calculate currency strength
        print("\n[*] Calculating currency strength with weighted analysis...")
        print("   M5 (5-minute): 20% weight - immediate signals")
        print("   H1 (1-hour):   30% weight - intraday trends")
        print("   H4 (4-hour):   50% weight - broader context")
        result = currency_strength_indicator(
            pair_data=pair_data,
            timeframe_weights={
                "M5": 0.2,
                "H1": 0.3,
                "H4": 0.5,
            },  # Short-term trading weights
            include_pairs=True,
            n_top_pairs=10,
        )

        # Step 5: Display dashboard
        display_currency_strength_dashboard(result)

        # Step 6: Show time series data (optional)
        print("\n[*] Latest Currency Strength Values:")
        strength_df = result["currency_strength"]
        strength_cols = [
            f"{c}_strength"
            for c in MAJOR_CURRENCIES
            if f"{c}_strength" in strength_df.columns
        ]

        if strength_cols:
            print(strength_df[strength_cols].tail(5))

        logger.success("Currency Strength Analysis Example Complete")

    except Exception as e:
        logger.error(f"Error during analysis: {str(e)}")
        raise

    finally:
        # Step 7: Cleanup - shutdown MT5 connection
        client.shutdown()
        logger.info("Disconnected from MT5")


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        logger.info("\nAnalysis interrupted by user")
        sys.exit(0)
    except Exception as e:
        logger.error(f"Fatal error: {str(e)}")
        sys.exit(1)
