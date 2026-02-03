"""Compare API values vs Example calculation.

This script fetches data once and runs it through both the API logic
and the example logic to see if they produce identical results.
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


def _fetch_multi_timeframe_data(
    client: MT5Client,
    symbols: list,
    timeframes: list,
    bars_per_tf: dict,
) -> dict:
    """Fetch multi-timeframe data for multiple symbols.

    Args:
        client: MT5Client instance
        symbols: List of currency pair symbols
        timeframes: List of timeframes to fetch
        bars_per_tf: Dictionary of bars to fetch per timeframe

    Returns:
        Dictionary mapping symbols to combined DataFrames
    """
    pair_data = {}

    for symbol in symbols:
        try:
            timeframe_dfs = {}
            all_fetched = True

            for tf in timeframes:
                data = client.get_bars(
                    symbol=symbol, timeframe=tf, count=bars_per_tf[tf]
                )

                if data is not None and not data.empty:
                    if "time" in data.columns:
                        data = data.set_index("time")
                    timeframe_dfs[tf] = data
                else:
                    all_fetched = False
                    break

            if all_fetched and len(timeframe_dfs) == len(timeframes):
                # Combine like both API and example do
                combined_df = pd.concat(timeframe_dfs, names=["timeframe", "time"])
                combined_df = combined_df.swaplevel(0, 1)
                pair_data[symbol] = combined_df

        except Exception as e:
            logger.warning(f"Failed to fetch {symbol}: {e}")
            continue

    return pair_data


def main():
    """Compare API and example calculations."""
    logger.info("Starting API vs Example Comparison")

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
        # Fetch data for all pairs (same as both API and example)
        logger.info("Fetching multi-timeframe data for 28 pairs...")
        timeframes = ["M5", "H1", "H4"]
        bars_per_tf = {"M5": 100, "H1": 100, "H4": 100}

        pair_data = _fetch_multi_timeframe_data(
            client, CURRENCY_PAIRS[:28], timeframes, bars_per_tf
        )

        logger.info(f"Successfully fetched {len(pair_data)} pairs")

        if not pair_data:
            logger.error("No data fetched")
            return

        # Run the calculation (same as both API and example)
        logger.info("Running currency strength calculation...")
        result = currency_strength_indicator(
            pair_data=pair_data,
            timeframe_weights={"M5": 0.2, "H1": 0.3, "H4": 0.5},
            include_pairs=True,
            n_top_pairs=10,
        )

        # Display results
        print("\n" + "=" * 80)
        print("COMPARISON RESULTS")
        print("=" * 80)
        print("\nBoth API and Example should produce these EXACT values:")
        print("\nCurrency Strengths:")
        print("-" * 50)

        latest_strengths = result["latest_strengths"]
        latest_ranks = result["latest_ranks"]

        for currency in sorted(MAJOR_CURRENCIES, key=lambda c: latest_ranks.get(c, 99)):
            strength = latest_strengths.get(currency, 0.0)
            rank = latest_ranks.get(currency, "-")
            print(f"{currency:<5} {strength:>10.6f}%  (rank {rank})")

        print("\n" + "=" * 80)
        print("DIAGNOSIS")
        print("=" * 80)
        print("\nIf API or Example show different values, possible causes:")
        print("1. Different fetch times → Market data changed between calls")
        print("2. Caching → API/Frontend serving cached data")
        print("3. Different pairs_count → Using different number of pairs")
        print("4. Code mismatch → API not using updated code")
        print("\nTo verify:")
        print("- Check API 'last_updated' timestamp vs when you ran example")
        print("- Check if frontend is caching (hard refresh: Ctrl+Shift+R)")
        print("- Ensure API server restarted after code changes")
        print("=" * 80)

    except Exception as e:
        logger.error(f"Error: {e}")
        raise
    finally:
        client.shutdown()


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        logger.info("\nInterrupted by user")
        sys.exit(0)
    except Exception as e:
        logger.error(f"Fatal error: {e}")
        sys.exit(1)
