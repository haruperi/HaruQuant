"""Edge Lab null models and statistical tests.

This module provides tools to establish what "no edge" looks like:
- Random entry baselines
- Block bootstrap for autocorrelation-aware confidence intervals
- Permutation tests
- Multiple hypothesis correction
"""

from __future__ import annotations

from typing import Callable, Dict, List, Optional, Tuple, cast

import numpy as np
import pandas as pd

from backend.common.logger import logger

# =============================================================================
# BLOCK BOOTSTRAP
# =============================================================================


def block_bootstrap_ci(
    sample: np.ndarray,
    statistic: Callable[[np.ndarray], float],
    n_boot: int = 2000,
    block_size: int = 20,
    ci_level: float = 0.95,
    seed: Optional[int] = 7,
) -> Tuple[float, float]:
    """Block bootstrap confidence interval.

    Uses overlapping block bootstrap to account for autocorrelation
    in trade returns. IID bootstrap would overstate confidence.

    Args:
        sample: Array of observations (e.g., R-multiples)
        statistic: Function to compute statistic of interest
        n_boot: Number of bootstrap resamples
        block_size: Size of blocks (larger for more autocorrelation)
        ci_level: Confidence level (e.g., 0.95 for 95%)
        seed: Random seed for reproducibility

    Returns:
        Tuple of (lower_bound, upper_bound)
    """
    rng = np.random.default_rng(seed)
    x = np.asarray(sample, dtype=float)
    n = len(x)

    if n == 0:
        return (float("nan"), float("nan"))
    if n == 1:
        v = float(statistic(x))
        return (v, v)

    # Ensure block_size doesn't exceed sample size
    effective_block_size = min(block_size, n)
    k = max(1, int(np.ceil(n / effective_block_size)))

    stats = []
    for _ in range(n_boot):
        # Sample block starting positions
        starts = rng.integers(0, n - effective_block_size + 1, size=k)
        blocks = [x[s : s + effective_block_size] for s in starts]
        xb = np.concatenate(blocks)[:n]
        stats.append(float(statistic(xb)))

    stats = np.sort(np.asarray(stats))
    alpha = 1.0 - ci_level
    lo = np.quantile(stats, alpha / 2.0)
    hi = np.quantile(stats, 1.0 - alpha / 2.0)

    logger.debug(f"Bootstrap CI ({ci_level*100:.0f}%): [{lo:.4f}, {hi:.4f}]")
    return float(lo), float(hi)


def block_bootstrap_distribution(
    sample: np.ndarray,
    statistic: Callable[[np.ndarray], float],
    n_boot: int = 2000,
    block_size: int = 20,
    seed: Optional[int] = 7,
) -> np.ndarray:
    """Generate bootstrap distribution of a statistic.

    Args:
        sample: Array of observations
        statistic: Function to compute statistic
        n_boot: Number of bootstrap resamples
        block_size: Size of blocks
        seed: Random seed

    Returns:
        Array of bootstrapped statistics
    """
    rng = np.random.default_rng(seed)
    x = np.asarray(sample, dtype=float)
    n = len(x)

    if n == 0:
        return np.array([])

    effective_block_size = min(block_size, n)
    k = max(1, int(np.ceil(n / effective_block_size)))

    stats = []
    for _ in range(n_boot):
        starts = rng.integers(0, n - effective_block_size + 1, size=k)
        blocks = [x[s : s + effective_block_size] for s in starts]
        xb = np.concatenate(blocks)[:n]
        stats.append(float(statistic(xb)))

    return np.asarray(stats, dtype=float)


# =============================================================================
# PERMUTATION TESTS
# =============================================================================


def permutation_test(observed: float, null_samples: np.ndarray) -> float:
    """Compute p-value from permutation test.

    One-sided test: P(null >= observed)

    Args:
        observed: Observed statistic value
        null_samples: Array of null distribution samples

    Returns:
        P-value (lower is more significant)
    """
    null_samples = np.asarray(null_samples, dtype=float)
    if len(null_samples) == 0:
        return float("nan")

    # Add 1 to numerator and denominator for conservative estimate
    p_value = float((np.sum(null_samples >= observed) + 1) / (len(null_samples) + 1))

    logger.debug(f"Permutation p-value: {p_value:.4f} (observed={observed:.4f})")
    return p_value


def random_entry_null(
    log_returns: np.ndarray,
    n_trades: int,
    hold_bars: int,
    side: str = "BUY",
    n_perm: int = 2000,
    seed: Optional[int] = 11,
) -> np.ndarray:
    """Generate null distribution via random entries (log-return space).

    Simulates what random entry timing would produce.

    Args:
        log_returns: Array of log returns
        n_trades: Number of trades to simulate per permutation
        hold_bars: Holding period in bars
        side: "BUY" or "SELL"
        n_perm: Number of permutations
        seed: Random seed

    Returns:
        Array of mean expectancies under null
    """
    rng = np.random.default_rng(seed)
    r = np.asarray(log_returns, dtype=float)
    n = len(r)

    if n < hold_bars + 5 or n_trades <= 0:
        return np.array([], dtype=float)

    out = []
    max_i = n - hold_bars - 1

    for _ in range(n_perm):
        idx = rng.integers(1, max_i, size=n_trades)
        vals = np.asarray([np.sum(r[i : i + hold_bars]) for i in idx], dtype=float)
        if side.upper() == "SELL":
            vals = -vals
        out.append(float(np.mean(vals)))

    return np.asarray(out, dtype=float)


def r_space_null(
    df: pd.DataFrame,
    n_trades: int,
    hold_bars: int,
    side: str,
    k_stop_atr: float,
    atr_series: pd.Series,
    n_perm: int = 2000,
    seed: Optional[int] = 11,
    close_col: str = "Close",
    high_col: str = "High",
    low_col: str = "Low",
) -> np.ndarray:
    """Generate null distribution in R-multiple space.

    Randomizes entry times while preserving ATR-based stop distance.
    More accurate than log-return null for R-multiple strategies.

    Args:
        df: OHLC DataFrame
        n_trades: Number of trades per permutation
        hold_bars: Maximum holding period
        side: "BUY" or "SELL"
        k_stop_atr: Stop distance multiplier
        atr_series: ATR values aligned with df
        n_perm: Number of permutations
        seed: Random seed
        close_col: Close column name
        high_col: High column name
        low_col: Low column name

    Returns:
        Array of mean R-multiples under null
    """
    rng = np.random.default_rng(seed)
    n = len(df)

    if n < hold_bars + 50 or n_trades <= 0:
        logger.warning("Insufficient data for R-space null distribution")
        return np.array([], dtype=float)

    close = df[close_col].values
    atr_vals = atr_series.values

    # Valid entry range
    valid_start = max(20, int(len(atr_vals) * 0.1))  # Skip warmup
    valid_end = n - hold_bars - 1

    if valid_end <= valid_start:
        return np.array([], dtype=float)

    out = []

    for _ in range(n_perm):
        idx = rng.integers(valid_start, valid_end, size=n_trades)
        r_multiples = []

        for i in idx:
            entry_price = close[i]
            atr_i = atr_vals[i]

            if not np.isfinite(atr_i) or atr_i <= 0:
                continue

            stop_dist = k_stop_atr * atr_i
            exit_price = close[min(i + hold_bars, n - 1)]

            if side.upper() == "BUY":
                pnl = exit_price - entry_price
            else:
                pnl = entry_price - exit_price

            r_mult = pnl / stop_dist
            r_multiples.append(r_mult)

        if len(r_multiples) > 0:
            out.append(float(np.mean(r_multiples)))

    return np.asarray(out, dtype=float)


def session_randomized_null(  # noqa: C901
    df: pd.DataFrame,
    entry_indices: np.ndarray,
    hold_bars: int,
    side: str,
    k_stop_atr: float,
    atr_series: pd.Series,
    n_perm: int = 2000,
    seed: Optional[int] = 11,
    close_col: str = "Close",
) -> np.ndarray:
    """Generate null by shuffling entries within same session.

    Preserves time-of-day distribution while randomizing exact bars.

    Args:
        df: OHLC DataFrame with 'session' column
        entry_indices: Original entry bar indices
        hold_bars: Maximum holding period
        side: "BUY" or "SELL"
        k_stop_atr: Stop distance multiplier
        atr_series: ATR values
        n_perm: Number of permutations
        seed: Random seed
        close_col: Close column name

    Returns:
        Array of mean R-multiples under null
    """
    rng = np.random.default_rng(seed)

    if "session" not in df.columns:
        logger.warning("DataFrame missing 'session' column for session-randomized null")
        return np.array([], dtype=float)

    n = len(df)
    close = df[close_col].values
    atr_vals = atr_series.values
    sessions = df["session"].values

    # Group indices by session
    session_indices: Dict[str, List[int]] = {}
    for i in range(n - hold_bars - 1):
        sess = str(sessions[i])
        if sess not in session_indices:
            session_indices[sess] = []
        session_indices[sess].append(i)

    out = []

    for _ in range(n_perm):
        r_multiples = []

        for orig_idx in entry_indices:
            if orig_idx >= n:
                continue

            sess = str(sessions[orig_idx])
            candidates = session_indices.get(sess, [])

            if len(candidates) == 0:
                continue

            # Random index from same session
            new_idx = rng.choice(candidates)
            entry_price = close[new_idx]
            atr_i = atr_vals[new_idx]

            if not np.isfinite(atr_i) or atr_i <= 0:
                continue

            stop_dist = k_stop_atr * atr_i
            exit_price = close[min(new_idx + hold_bars, n - 1)]

            if side.upper() == "BUY":
                pnl = exit_price - entry_price
            else:
                pnl = entry_price - exit_price

            r_mult = pnl / stop_dist
            r_multiples.append(r_mult)

        if len(r_multiples) > 0:
            out.append(float(np.mean(r_multiples)))

    return np.asarray(out, dtype=float)


def shuffle_returns_null(
    log_returns: np.ndarray,
    entry_indices: np.ndarray,
    hold_bars: int,
    side: str = "BUY",
    n_perm: int = 2000,
    seed: Optional[int] = 11,
) -> np.ndarray:
    """Generate null by shuffling return blocks.

    Preserves return distribution but breaks temporal structure.

    Args:
        log_returns: Array of log returns
        entry_indices: Original entry bar indices
        hold_bars: Holding period
        side: "BUY" or "SELL"
        n_perm: Number of permutations
        seed: Random seed

    Returns:
        Array of mean expectancies under null
    """
    rng = np.random.default_rng(seed)
    r = np.asarray(log_returns, dtype=float)
    n = len(r)

    if n < hold_bars + 5 or len(entry_indices) == 0:
        return np.array([], dtype=float)

    out = []

    for _ in range(n_perm):
        # Shuffle returns while preserving structure
        shuffled = r.copy()
        rng.shuffle(shuffled)

        vals = []
        for i in entry_indices:
            if i + hold_bars < n:
                val = np.sum(shuffled[i : i + hold_bars])
                if side.upper() == "SELL":
                    val = -val
                vals.append(val)

        if len(vals) > 0:
            out.append(float(np.mean(vals)))

    return np.asarray(out, dtype=float)


# =============================================================================
# MULTIPLE HYPOTHESIS CORRECTION
# =============================================================================


def benjamini_hochberg(p_values: np.ndarray, q: float = 0.10) -> np.ndarray:
    """Benjamini-Hochberg FDR correction.

    Controls false discovery rate when testing multiple hypotheses.

    Args:
        p_values: Array of p-values
        q: FDR threshold (e.g., 0.10 for 10%)

    Returns:
        Boolean array indicating which hypotheses are significant
    """
    p = np.asarray(p_values, dtype=float)
    m = len(p)

    if m == 0:
        return np.array([], dtype=bool)

    # Sort p-values and get indices
    order = np.argsort(p)
    ranked = p[order]

    # BH threshold: p[i] <= q * i / m
    thresh = q * (np.arange(1, m + 1) / m)
    passed = ranked <= thresh

    if not np.any(passed):
        logger.debug("No hypotheses passed BH correction")
        return np.zeros(m, dtype=bool)

    # Find largest k where p[k] <= threshold
    k = int(np.max(np.where(passed)[0]))
    cutoff = ranked[k]

    significant = p <= cutoff
    logger.debug(
        f"BH correction: {np.sum(significant)}/{m} hypotheses significant at q={q}"
    )

    return significant


def holm_bonferroni(p_values: np.ndarray, alpha: float = 0.05) -> np.ndarray:
    """Holm-Bonferroni correction (more conservative than BH).

    Controls family-wise error rate.

    Args:
        p_values: Array of p-values
        alpha: Significance level

    Returns:
        Boolean array indicating which hypotheses are significant
    """
    p = np.asarray(p_values, dtype=float)
    m = len(p)

    if m == 0:
        return np.array([], dtype=bool)

    order = np.argsort(p)
    ranked = p[order]

    significant = np.zeros(m, dtype=bool)

    for i, p_val in enumerate(ranked):
        if p_val <= alpha / (m - i):
            significant[order[i]] = True
        else:
            break  # Stop at first non-significant

    logger.debug(
        f"Holm-Bonferroni: {np.sum(significant)}/{m} hypotheses significant at alpha={alpha}"
    )
    return significant


# =============================================================================
# NULL DISTRIBUTION ANALYSIS
# =============================================================================


def compute_null_percentile(observed: float, null_samples: np.ndarray) -> float:
    """Compute percentile of observed value in null distribution.

    Args:
        observed: Observed statistic
        null_samples: Null distribution samples

    Returns:
        Percentile (0-100)
    """
    null_samples = np.asarray(null_samples, dtype=float)
    if len(null_samples) == 0:
        return float("nan")

    return float(np.sum(null_samples <= observed) / len(null_samples) * 100)


def null_distribution_stats(null_samples: np.ndarray) -> dict:
    """Compute summary statistics of null distribution.

    Args:
        null_samples: Null distribution samples

    Returns:
        Dictionary of statistics
    """
    null_samples = np.asarray(null_samples, dtype=float)

    if len(null_samples) == 0:
        return {
            "mean": float("nan"),
            "std": float("nan"),
            "median": float("nan"),
            "p5": float("nan"),
            "p95": float("nan"),
        }

    return {
        "mean": float(np.mean(null_samples)),
        "std": float(np.std(null_samples)),
        "median": float(np.median(null_samples)),
        "p5": float(np.percentile(null_samples, 5)),
        "p95": float(np.percentile(null_samples, 95)),
    }


def exceeds_null_threshold(
    observed: float,
    null_samples: np.ndarray,
    percentile: float = 95.0,
) -> bool:
    """Check if observed value exceeds null distribution threshold.

    Args:
        observed: Observed statistic
        null_samples: Null distribution samples
        percentile: Threshold percentile (e.g., 95)

    Returns:
        True if observed exceeds the threshold
    """
    null_samples = np.asarray(null_samples, dtype=float)
    if len(null_samples) == 0:
        return False

    threshold = np.percentile(null_samples, percentile)
    exceeds = cast(bool, observed > threshold)

    logger.debug(
        f"Null check: observed={observed:.4f}, threshold (p{percentile:.0f})={threshold:.4f}, exceeds={exceeds}"
    )
    return exceeds

