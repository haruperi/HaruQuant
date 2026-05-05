"""Currency Strength Indicator.

Multi-timeframe currency strength analysis based on Ray Dalio's interconnected market methodology.
Calculates individual currency strength by analyzing multiple currency pairs across different timeframes
to identify the true strength of each currency, rather than just analyzing pairs in isolation.

The indicator uses weighted multi-timeframe analysis optimized for short-term trading:
- M5 (5-minute): 20% weight - captures immediate/very short-term signals
- H1 (1-hour): 30% weight - reflects intraday trends
- H4 (4-hour): 50% weight - provides broader market context

This approach balances immediate signals with broader market context for short-term trading decisions.
"""

from typing import Dict, List, Optional, Tuple

import numpy as np
import pandas as pd

from services.utils.logger import logger
from services.indicator.validation import (
    require_columns,
    require_dataframe,
)

# Major currency pairs to analyze (28 pairs covering 8 major currencies)
CURRENCY_PAIRS = [
    "EURUSD",
    "GBPUSD",
    "USDJPY",
    "USDCHF",
    "AUDUSD",
    "NZDUSD",
    "USDCAD",
    "EURGBP",
    "EURJPY",
    "EURCHF",
    "EURAUD",
    "EURNZD",
    "EURCAD",
    "GBPJPY",
    "GBPCHF",
    "GBPAUD",
    "GBPNZD",
    "GBPCAD",
    "AUDJPY",
    "NZDJPY",
    "CADJPY",
    "CHFJPY",
    "AUDCHF",
    "NZDCHF",
    "CADCHF",
    "AUDNZD",
    "AUDCAD",
    "NZDCAD",
]

# Major currencies tracked
MAJOR_CURRENCIES = ["EUR", "GBP", "USD", "JPY", "AUD", "NZD", "CAD", "CHF"]


def _calculate_timeframe_changes(
    result: pd.DataFrame,
    timeframe_weights: Dict[str, float],
    price_col: str,
) -> tuple[Dict[str, pd.Series], Dict[str, pd.DataFrame]]:
    """Calculate percentage changes for each timeframe independently.

    Args:
        result: DataFrame with multi-timeframe data
        timeframe_weights: Dictionary of timeframe weights
        price_col: Column name for price data

    Returns:
        Tuple of (timeframe_changes dict, timeframe_data dict)
    """
    timeframe_changes = {}
    timeframe_data = {}

    for timeframe in timeframe_weights.keys():
        try:
            tf_data = result.xs(timeframe, level="timeframe")
            pct_change = (
                (tf_data[price_col] - tf_data[price_col].shift(1))
                / tf_data[price_col].shift(1)
                * 100
            )
            timeframe_changes[timeframe] = pct_change
            timeframe_data[timeframe] = tf_data
            logger.debug(f"Calculated changes for {timeframe}: {len(pct_change)} bars")
        except KeyError:
            logger.warning(f"Timeframe {timeframe} not found in data, skipping")
            continue

    if not timeframe_changes:
        raise ValueError("No timeframe data available for calculation")

    return timeframe_changes, timeframe_data


def _determine_target_timeframe(timeframe_data: Dict[str, pd.DataFrame]) -> str:
    """Determine the target timeframe for alignment.

    Args:
        timeframe_data: Dictionary of timeframe DataFrames

    Returns:
        Target timeframe name
    """
    if "H1" in timeframe_data:
        return "H1"
    # Fallback: use the timeframe with most bars (most granular)
    return max(timeframe_data.keys(), key=lambda k: len(timeframe_data[k]))


def _align_timeframe_changes(
    timeframe_changes: Dict[str, pd.Series],
    timeframe_data: Dict[str, pd.DataFrame],
    target_tf: str,
) -> pd.DataFrame:
    """Align all timeframe changes to target timeframe using forward-fill.

    Args:
        timeframe_changes: Dictionary of percentage changes per timeframe
        timeframe_data: Dictionary of OHLCV data per timeframe
        target_tf: Target timeframe for alignment

    Returns:
        Aligned DataFrame with all timeframe changes
    """
    target_index = timeframe_data[target_tf].index
    logger.debug(
        f"Aligning all timeframes to {target_tf} with {len(target_index)} timestamps"
    )

    # Start with the target timeframe's OHLCV data
    aligned_result = timeframe_data[target_tf].copy()

    # Align all timeframe changes to target index using forward-fill
    for tf, changes in timeframe_changes.items():
        col_name = f"{tf}_change"
        if tf == target_tf:
            # Direct assignment for target timeframe
            aligned_result[col_name] = changes
        else:
            # Forward-fill: at time T, use the most recent value from this timeframe
            aligned_result[col_name] = changes.reindex(target_index, method="ffill")
            logger.debug(f"Forward-filled {tf} to {target_tf} timestamps")

    return aligned_result


def _calculate_weighted_strength(
    aligned_result: pd.DataFrame,
    timeframe_weights: Dict[str, float],
) -> pd.DataFrame:
    """Calculate weighted pair strength from aligned timeframe changes.

    Args:
        aligned_result: DataFrame with aligned timeframe changes
        timeframe_weights: Dictionary of timeframe weights

    Returns:
        DataFrame with pair_strength column added
    """
    aligned_result["pair_strength"] = 0.0
    for timeframe, weight in timeframe_weights.items():
        col_name = f"{timeframe}_change"
        if col_name in aligned_result.columns:
            aligned_result["pair_strength"] += (
                aligned_result[col_name].fillna(0) * weight
            )
    return aligned_result


def calculate_pair_strength(
    data: pd.DataFrame,
    timeframe_weights: Optional[Dict[str, float]] = None,
    price_col: str = "close",
) -> pd.DataFrame:
    """Calculate currency pair strength for a single pair across multiple timeframes.

    Analyzes percentage price changes across different timeframes and combines them
    with configurable weights to produce an overall strength metric.

    IMPORTANT - Timeframe Alignment for Backtesting:
    When multi-timeframe data is provided, the function aligns all timeframes to the
    most granular timeframe (typically M5) using forward-fill. This ensures that at
    any point in time T, the strength calculation uses:
    - The M5 bar at time T
    - The most recent H1 bar at or before time T
    - The most recent H4 bar at or before time T

    Example: At 14:35 on Dec 23, 2025:
    - M5_change: uses the 14:35 M5 bar
    - H1_change: uses the 14:00 H1 bar (most recent before 14:35)
    - H4_change: uses the 12:00 H4 bar (most recent before 14:35)
    - pair_strength = M5_change * 0.2 + H1_change * 0.3 + H4_change * 0.5

    This alignment is critical for accurate backtesting and real-time analysis.

    Args:
        data: DataFrame with OHLCV data for a currency pair. Must have a MultiIndex
              with 'timeframe' as one level, or be a flat DataFrame for single timeframe.
        timeframe_weights: Dictionary mapping timeframe names to weights.
                          Default: {"M5": 0.2, "H1": 0.3, "H4": 0.5}
        price_col: Column name for price data (default: "close")

    Returns:
        DataFrame aligned to the most granular timeframe with columns:
        - OHLCV columns from the target timeframe
        - {timeframe}_change: Percentage change for each timeframe (forward-filled)
        - pair_strength: Weighted combination of all timeframe changes at each point

    Raises:
        ValueError: If price_col is missing or timeframe_weights sum != 1.0

    Example:
        >>> data = get_multi_timeframe_data("EURUSD", ["M5", "H1", "H4"])
        >>> result = calculate_pair_strength(data)
        >>> print(result[["M5_change", "H1_change", "H4_change", "pair_strength"]].tail())
    """
    if price_col not in data.columns:
        logger.error(f"Price column '{price_col}' not found in data")
        raise ValueError(f"Price column '{price_col}' is required")

    # Default timeframe weights for short-term trading
    if timeframe_weights is None:
        timeframe_weights = {"M5": 0.2, "H1": 0.3, "H4": 0.5}

    # Validate weights sum to 1.0
    weight_sum = sum(timeframe_weights.values())
    if not np.isclose(weight_sum, 1.0, atol=1e-6):
        logger.error(f"Timeframe weights must sum to 1.0, got {weight_sum}")
        raise ValueError(f"Timeframe weights sum to {weight_sum}, must be 1.0")

    logger.debug(f"Calculating pair strength with weights: {timeframe_weights}")

    result = data.copy()

    # Calculate percentage changes for each timeframe
    if isinstance(result.index, pd.MultiIndex) and "timeframe" in result.index.names:
        # Multi-timeframe data with MultiIndex - align to single timeline
        timeframe_changes, timeframe_data = _calculate_timeframe_changes(
            result, timeframe_weights, price_col
        )

        # Determine target timeframe for alignment
        target_tf = _determine_target_timeframe(timeframe_data)

        # Align all timeframe changes to target timeframe
        aligned_result = _align_timeframe_changes(
            timeframe_changes, timeframe_data, target_tf
        )

        # Calculate weighted pair strength
        aligned_result = _calculate_weighted_strength(aligned_result, timeframe_weights)

        logger.success(
            "Pair strength calculation complete with time-aligned multi-timeframe data"
        )
        return aligned_result
    else:
        # Single timeframe or flat data - calculate simple percentage change
        result["pct_change"] = (
            (result[price_col] - result[price_col].shift(1))
            / result[price_col].shift(1)
            * 100
        )
        result["pair_strength"] = result["pct_change"]

    logger.success("Pair strength calculation complete")
    return result


def _calculate_pair_strengths(
    pair_data: Dict[str, pd.DataFrame],
    timeframe_weights: Dict[str, float],
    price_col: str,
) -> Dict[str, pd.DataFrame]:
    """Calculate strength for each currency pair."""
    pair_strengths = {}
    for pair, data in pair_data.items():
        try:
            pair_strengths[pair] = calculate_pair_strength(
                data, timeframe_weights=timeframe_weights, price_col=price_col
            )
            logger.debug(f"Calculated strength for {pair}")
        except Exception as e:
            logger.warning(f"Failed to calculate strength for {pair}: {str(e)}")
            continue

    if not pair_strengths:
        raise ValueError("Failed to calculate strength for any currency pair")
    return pair_strengths


def _get_common_index(pair_strengths: Dict[str, pd.DataFrame]) -> pd.Index:
    """Get common timestamps across all pair strength DataFrames."""
    common_index = None
    for df in pair_strengths.values():
        if common_index is None:
            common_index = df.index
        else:
            common_index = common_index.intersection(df.index)

    if common_index is None or len(common_index) == 0:
        raise ValueError("Currency pairs have no overlapping timestamps")

    logger.debug(f"Found {len(common_index)} common timestamps")
    return common_index


def _accumulate_currency_strengths(
    pair_strengths: Dict[str, pd.DataFrame],
    common_index: pd.Index,
) -> tuple[Dict[str, pd.Series], Dict[str, int]]:
    """Accumulate strength contributions from each pair for each currency."""
    currency_contributions = {
        curr: pd.Series(0.0, index=common_index) for curr in MAJOR_CURRENCIES
    }
    currency_counts = dict.fromkeys(MAJOR_CURRENCIES, 0)

    for pair, strength_df in pair_strengths.items():
        if len(pair) != 6:
            continue
        base_currency, quote_currency = pair[:3], pair[3:]
        if (
            base_currency not in MAJOR_CURRENCIES
            or quote_currency not in MAJOR_CURRENCIES
        ):
            continue

        pair_strength = strength_df.loc[common_index, "pair_strength"]
        currency_contributions[base_currency] += pair_strength
        currency_contributions[quote_currency] -= pair_strength
        currency_counts[base_currency] += 1
        currency_counts[quote_currency] += 1

    return currency_contributions, currency_counts


def _build_strength_dataframe(
    common_index: pd.Index,
    currency_contributions: Dict[str, pd.Series],
    currency_counts: Dict[str, int],
) -> pd.DataFrame:
    """Build final DataFrame with currency strengths and rankings."""
    result = pd.DataFrame(index=common_index)

    for currency in MAJOR_CURRENCIES:
        if currency_counts[currency] > 0:
            result[f"{currency}_strength"] = (
                currency_contributions[currency] / currency_counts[currency]
            )
        else:
            result[f"{currency}_strength"] = 0.0

    # Add rankings
    for idx in result.index:
        strengths = result.loc[idx, [f"{c}_strength" for c in MAJOR_CURRENCIES]]
        ranks = strengths.rank(ascending=False, method="min")
        for i, currency in enumerate(MAJOR_CURRENCIES):
            result.loc[idx, f"{currency}_rank"] = ranks.iloc[i]

    return result


def calculate_currency_strength(
    pair_data: Dict[str, pd.DataFrame],
    timeframe_weights: Optional[Dict[str, float]] = None,
    price_col: str = "close",
) -> pd.DataFrame:
    """Calculate individual currency strength from multiple currency pairs.

    Implements Ray Dalio's interconnected market methodology by aggregating strength
    across all pairs involving each currency. For example, EUR strength is derived
    from EURUSD, EURGBP, EURJPY, etc.

    The algorithm:
    1. Calculate pair strength for each currency pair
    2. Decompose each pair into base and quote currency contributions
    3. Aggregate all contributions for each currency
    4. Normalize to produce relative strength scores

    Args:
        pair_data: Dictionary mapping pair symbols to their OHLCV DataFrames.
                  Each DataFrame should have data for the same timestamp range.
                  Example: {"EURUSD": df_eurusd, "GBPUSD": df_gbpusd, ...}
        timeframe_weights: Dictionary mapping timeframe names to weights.
                          Default: {"M5": 0.2, "H1": 0.3, "H4": 0.5}
        price_col: Column name for price data (default: "close")

    Returns:
        DataFrame with timestamp index and columns for each currency's strength:
        - {currency}_strength: Normalized strength score for each currency
        - {currency}_rank: Relative ranking (1 = strongest)

        The returned DataFrame has one row per timestamp, making it suitable for
        time-series analysis and charting.

    Raises:
        ValueError: If pair_data is empty or currencies cannot be extracted

    Example:
        >>> pair_data = {
        ...     "EURUSD": get_bars("EURUSD", ...),
        ...     "GBPUSD": get_bars("GBPUSD", ...),
        ...     # ... more pairs
        ... }
        >>> strength = calculate_currency_strength(pair_data)
        >>> print(strength[["EUR_strength", "USD_strength", "GBP_strength"]].tail())

        >>> # Find strongest and weakest currencies
        >>> latest = strength.iloc[-1]
        >>> strongest = latest.nlargest(3).index
        >>> weakest = latest.nsmallest(3).index
    """
    if not pair_data:
        logger.error("pair_data dictionary is empty")
        raise ValueError("pair_data must contain at least one currency pair")

    # Default timeframe weights for short-term trading
    if timeframe_weights is None:
        timeframe_weights = {"M5": 0.2, "H1": 0.3, "H4": 0.5}

    logger.debug(f"Calculating currency strength for {len(pair_data)} pairs")

    # Calculate strength for each pair
    pair_strengths = _calculate_pair_strengths(pair_data, timeframe_weights, price_col)

    # Get common timestamps across all pairs
    common_index = _get_common_index(pair_strengths)

    # Accumulate strength from each pair
    currency_contributions, currency_counts = _accumulate_currency_strengths(
        pair_strengths, common_index
    )

    # Build final DataFrame with strengths and rankings
    result = _build_strength_dataframe(
        common_index, currency_contributions, currency_counts
    )

    logger.success(
        f"Currency strength calculation complete for {len(MAJOR_CURRENCIES)} currencies"
    )
    return result


def get_top_pairs(
    currency_strength: pd.DataFrame, n_pairs: int = 10, min_strength_diff: float = 0.0
) -> Tuple[List[Dict], List[Dict]]:
    """Identify top strong and weak currency pair opportunities.

    Analyzes currency strength to find the best trading opportunities by pairing
    strong currencies against weak ones (for longs) and weak against strong (for shorts).

    Args:
        currency_strength: DataFrame from calculate_currency_strength()
        n_pairs: Number of top pairs to return in each category
        min_strength_diff: Minimum strength difference required between currencies
                          in a pair to be considered (filters out neutral pairs)

    Returns:
        Tuple of (strong_pairs, weak_pairs) where each is a list of dictionaries:
        {
            "pair": str,           # e.g., "EURUSD"
            "base": str,           # e.g., "EUR"
            "quote": str,          # e.g., "USD"
            "strength": float,     # Combined strength score
            "base_strength": float,
            "quote_strength": float,
            "recommendation": str  # "LONG" or "SHORT"
        }

    Example:
        >>> strength = calculate_currency_strength(pair_data)
        >>> strong, weak = get_top_pairs(strength, n_pairs=5)
        >>>
        >>> print("Top LONG opportunities:")
        >>> for pair in strong:
        ...     print(f"{pair['pair']}: {pair['recommendation']} (strength: {pair['strength']:.2f})")
    """
    if currency_strength.empty:
        logger.error("Currency strength DataFrame is empty")
        return [], []

    # Get latest strength values
    latest = currency_strength.iloc[-1]

    # Extract strength values for each currency
    strengths = {
        curr: latest[f"{curr}_strength"]
        for curr in MAJOR_CURRENCIES
        if f"{curr}_strength" in latest.index
    }

    logger.debug(f"Latest currency strengths: {strengths}")

    # Generate all possible pair combinations and calculate combined strength
    pair_opportunities = []

    for pair in CURRENCY_PAIRS:
        if len(pair) != 6:
            continue

        base = pair[:3]
        quote = pair[3:]

        if base not in strengths or quote not in strengths:
            continue

        base_strength = strengths[base]
        quote_strength = strengths[quote]

        # Combined strength: positive = strong base, negative = strong quote
        combined_strength = base_strength - quote_strength

        # Filter by minimum strength difference
        if abs(combined_strength) < min_strength_diff:
            continue

        pair_opportunities.append(
            {
                "pair": pair,
                "base": base,
                "quote": quote,
                "strength": combined_strength,
                "base_strength": base_strength,
                "quote_strength": quote_strength,
                "recommendation": "LONG" if combined_strength > 0 else "SHORT",
            }
        )

    # Sort by absolute strength (strongest divergences first)
    pair_opportunities.sort(key=lambda x: abs(x["strength"]), reverse=True)

    # Separate into long (positive strength) and short (negative strength)
    strong_pairs = [p for p in pair_opportunities if p["strength"] > 0][:n_pairs]
    weak_pairs = [p for p in pair_opportunities if p["strength"] < 0][:n_pairs]

    logger.info(
        f"Found {len(strong_pairs)} strong pairs and {len(weak_pairs)} weak pairs"
    )
    return strong_pairs, weak_pairs


def currency_strength_indicator(
    pair_data: Dict[str, pd.DataFrame],
    timeframe_weights: Optional[Dict[str, float]] = None,
    price_col: str = "close",
    include_pairs: bool = True,
    n_top_pairs: int = 10,
) -> Dict[str, pd.DataFrame]:
    r"""Complete currency strength analysis with pair recommendations.

    Convenience function that combines currency strength calculation with
    pair opportunity identification. Returns all data needed for dashboard display.

    Args:
        pair_data: Dictionary mapping pair symbols to OHLCV DataFrames
        timeframe_weights: Timeframe weights (default: H1=0.2, H4=0.3, D1=0.5)
        price_col: Price column name (default: "close")
        include_pairs: Whether to include top pair opportunities
        n_top_pairs: Number of top pairs to return

    Returns:
        Dictionary containing:
        {
            "currency_strength": DataFrame with individual currency strengths,
            "strong_pairs": List of top long opportunities (if include_pairs=True),
            "weak_pairs": List of top short opportunities (if include_pairs=True),
            "latest_strengths": Dict of latest strength values per currency,
            "latest_ranks": Dict of latest rank values per currency
        }

    Example:
        >>> result = currency_strength_indicator(pair_data)
        >>>
        >>> # Display currency strengths
        >>> print(result["currency_strength"][["EUR_strength", "USD_strength"]].tail())
        >>>
        >>> # Show trading opportunities
        >>> print("\nStrong pairs (LONG):")
        >>> for pair in result["strong_pairs"]:
        ...     print(f"  {pair['pair']}: {pair['strength']:.2f}")
    """
    logger.info("Starting complete currency strength analysis")

    # Calculate currency strengths
    strength_df = calculate_currency_strength(
        pair_data, timeframe_weights=timeframe_weights, price_col=price_col
    )

    # Get latest values
    latest = strength_df.iloc[-1]
    latest_strengths = {
        curr: latest[f"{curr}_strength"]
        for curr in MAJOR_CURRENCIES
        if f"{curr}_strength" in latest.index
    }
    latest_ranks = {
        curr: int(latest[f"{curr}_rank"])
        for curr in MAJOR_CURRENCIES
        if f"{curr}_rank" in latest.index
    }

    result = {
        "currency_strength": strength_df,
        "latest_strengths": latest_strengths,
        "latest_ranks": latest_ranks,
    }

    # Get top pairs if requested
    if include_pairs:
        strong_pairs, weak_pairs = get_top_pairs(strength_df, n_pairs=n_top_pairs)
        result["strong_pairs"] = strong_pairs
        result["weak_pairs"] = weak_pairs

    logger.success(f"Currency strength analysis complete for {len(MAJOR_CURRENCIES)} currencies")
    return result

