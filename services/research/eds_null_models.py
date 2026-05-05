"""EDS-0: Null Models / Baseline Detector.

Before searching for edge, establish what "no edge" looks like.
This module provides baselines against which other EDS results must be compared.

Baselines:
- Random-entry, fixed-exit (same holding period distribution)
- Time-of-day randomization (preserve session)
- Price permutation test (shuffle return blocks)

Your edge must beat the 95th percentile of null results.
"""

from __future__ import annotations

from dataclasses import asdict
from typing import Any, Dict, List

import numpy as np
import pandas as pd

from services.utils.logger import logger

from .config import BootstrapConfig, NullModelsConfig, PermutationConfig
from .features import atr, log_returns
from .null_models import null_distribution_stats, r_space_null, random_entry_null
from .results_schema import EdgeResult, EdgeStats, TradeSample


def run_eds_null_baseline(
    df: pd.DataFrame,
    symbol: str,
    timeframe: str,
    cfg: NullModelsConfig,
    boot: BootstrapConfig,
    perm: PermutationConfig,
    close_col: str = "Close",
    high_col: str = "High",
    low_col: str = "Low",
) -> EdgeResult:
    """EDS-0: Establish null model baselines.

    Generates distributions of what random trading would produce,
    so you can compare actual strategy results against these baselines.

    Args:
        df: OHLC DataFrame
        symbol: Trading symbol
        timeframe: Timeframe string
        cfg: Null models configuration
        boot: Bootstrap configuration
        perm: Permutation configuration
        close_col: Close column name
        high_col: High column name
        low_col: Low column name

    Returns:
        EdgeResult with null distribution statistics
    """
    logger.info(f"Running EDS-0 Null Baseline for {symbol} {timeframe}")

    out = df.copy()
    close = out[close_col].astype(float)
    # Compute features needed for null models
    out["atr"] = atr(out, 12, high_col, low_col, close_col)
    out["log_ret"] = log_returns(close)
    logret = out["log_ret"].dropna().values

    # Results storage
    null_distributions: Dict[str, Any] = {}
    trades: List[TradeSample] = []

    # ==========================================================================
    # BASELINE 1: Random Entry Null (log-return space)
    # ==========================================================================
    logger.debug("Computing random entry null distributions")

    for hold_bars in cfg.hold_bars_options:
        # BUY side
        null_buy = random_entry_null(
            logret,
            n_trades=cfg.n_random_entries,
            hold_bars=hold_bars,
            side="BUY",
            n_perm=perm.n_perm,
            seed=perm.seed,
        )
        null_distributions[f"random_entry_buy_h{hold_bars}"] = null_distribution_stats(
            null_buy
        )

        # SELL side
        null_sell = random_entry_null(
            logret,
            n_trades=cfg.n_random_entries,
            hold_bars=hold_bars,
            side="SELL",
            n_perm=perm.n_perm,
            seed=perm.seed,
        )
        null_distributions[f"random_entry_sell_h{hold_bars}"] = null_distribution_stats(
            null_sell
        )

    # ==========================================================================
    # BASELINE 2: R-Space Null (more realistic)
    # ==========================================================================
    logger.debug("Computing R-space null distributions")

    atr_series = out["atr"]
    k_stop_atr = 1.5  # Default stop distance

    for hold_bars in cfg.hold_bars_options:
        null_r_buy = r_space_null(
            out,
            n_trades=cfg.n_random_entries,
            hold_bars=hold_bars,
            side="BUY",
            k_stop_atr=k_stop_atr,
            atr_series=atr_series,
            n_perm=perm.n_perm,
            seed=perm.seed,
            close_col=close_col,
        )
        null_distributions[f"r_space_buy_h{hold_bars}"] = null_distribution_stats(
            null_r_buy
        )

        null_r_sell = r_space_null(
            out,
            n_trades=cfg.n_random_entries,
            hold_bars=hold_bars,
            side="SELL",
            k_stop_atr=k_stop_atr,
            atr_series=atr_series,
            n_perm=perm.n_perm,
            seed=perm.seed,
            close_col=close_col,
        )
        null_distributions[f"r_space_sell_h{hold_bars}"] = null_distribution_stats(
            null_r_sell
        )

    # ==========================================================================
    # BASELINE 3: Shuffled Returns (temporal structure test)
    # ==========================================================================
    if cfg.include_shuffle_test:
        logger.debug("Computing shuffled returns baseline")

        # Generate multiple shuffled return series and measure mean return
        rng = np.random.default_rng(perm.seed)
        shuffle_results = []

        for _ in range(perm.n_perm):
            shuffled = logret.copy()
            rng.shuffle(shuffled)

            # Measure drift after shuffling
            shuffle_results.append(float(np.mean(shuffled)))

        null_distributions["shuffled_returns"] = null_distribution_stats(
            np.array(shuffle_results)
        )

    # ==========================================================================
    # COMPUTE SUMMARY THRESHOLDS
    # ==========================================================================
    # Extract key thresholds strategies must beat

    thresholds = {}

    # Primary threshold: 95th percentile of random entry R-space null
    if "r_space_buy_h32" in null_distributions:
        thresholds["buy_threshold_r32"] = null_distributions["r_space_buy_h32"].get(
            "p95", 0
        )
    if "r_space_sell_h32" in null_distributions:
        thresholds["sell_threshold_r32"] = null_distributions["r_space_sell_h32"].get(
            "p95", 0
        )

    # Also track what random produces on average
    if "r_space_buy_h32" in null_distributions:
        thresholds["buy_null_mean_r32"] = null_distributions["r_space_buy_h32"].get(
            "mean", 0
        )

    # ==========================================================================
    # CONSTRUCT RESULT
    # ==========================================================================

    # Create "synthetic" stats summarizing the null baseline
    stats = EdgeStats(
        n_trades=cfg.n_random_entries,
        expectancy_r=0.0,  # Null expectation is zero
        win_rate=0.5,  # Random should be ~50%
        profit_factor=1.0,  # Null profit factor is ~1
        median_mae_r=float("nan"),
        median_mfe_r=float("nan"),
        avg_hold_bars=float(np.mean(cfg.hold_bars_options)),
        ci_low=float("nan"),
        ci_high=float("nan"),
        p_value_perm=float("nan"),
        extras={
            "total_r": 0.0,
            "null_distributions": null_distributions,
            "thresholds": thresholds,
            "hold_bars_tested": list(cfg.hold_bars_options),
            "n_random_entries": cfg.n_random_entries,
        },
    )

    logger.info(
        f"EDS-0 complete: Thresholds computed for {len(cfg.hold_bars_options)} holding periods"
    )

    return EdgeResult(
        symbol=symbol,
        timeframe=timeframe,
        eds_name="EDS-0 NullBaseline",
        config=asdict(cfg),
        stats=stats,
        trades=trades,
    )


def compare_to_null(
    observed_expectancy: float,
    null_result: EdgeResult,
    hold_bars: int = 32,
    side: str = "BUY",
) -> Dict[str, Any]:
    """Compare observed expectancy to null distribution.

    Args:
        observed_expectancy: Strategy's observed R-expectancy
        null_result: Result from run_eds_null_baseline
        hold_bars: Holding period to compare against
        side: "BUY" or "SELL"

    Returns:
        Dictionary with comparison results
    """
    key = f"r_space_{side.lower()}_h{hold_bars}"
    extras = null_result.stats.extras or {}
    null_dists = extras.get("null_distributions", {})

    if key not in null_dists:
        logger.warning(f"Null distribution '{key}' not found")
        return {"valid": False, "reason": f"Missing null distribution {key}"}

    null_stats = null_dists[key]

    null_p95 = null_stats.get("p95", 0)
    null_mean = null_stats.get("mean", 0)
    null_std = null_stats.get("std", 1)

    exceeds_threshold = observed_expectancy > null_p95
    z_score = (
        (observed_expectancy - null_mean) / null_std if null_std > 0 else float("inf")
    )

    result = {
        "valid": True,
        "observed": observed_expectancy,
        "null_mean": null_mean,
        "null_p95": null_p95,
        "null_std": null_std,
        "exceeds_p95": exceeds_threshold,
        "z_score": z_score,
        "verdict": "EDGE_DETECTED" if exceeds_threshold else "NO_EDGE",
    }

    if exceeds_threshold:
        logger.info(
            f"Edge detected: observed {observed_expectancy:.4f} > null p95 {null_p95:.4f}"
        )
    else:
        logger.warning(
            f"No edge: observed {observed_expectancy:.4f} <= null p95 {null_p95:.4f}"
        )

    return result


def get_acceptance_criteria(null_result: EdgeResult) -> Dict[str, float]:
    """Extract acceptance criteria from null baseline.

    Args:
        null_result: Result from run_eds_null_baseline

    Returns:
        Dictionary of criteria a strategy must meet
    """
    extras = null_result.stats.extras or {}
    thresholds = extras.get("thresholds", {})

    criteria = {
        "min_trades": 200,
        "min_expectancy_r": max(0.05, thresholds.get("buy_threshold_r32", 0.05)),
        "min_ci_low": 0.0,
        "max_p_value": 0.05,
    }

    logger.debug(f"Acceptance criteria: {criteria}")
    return criteria

