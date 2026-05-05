"""
Summary:
-------
HaruQuant Statistical Validation & Anti-Overfitting Layer.
Comprehensive tests to validate strategy robustness and detect selection bias.
This module provides a production-grade suite of tests including White's Reality Check, 
Permutation Tests (Sign-Flip), Deflated Sharpe Ratio, and Probability of Backtest Overfitting (PBO).

Summary of Methods:
------------------
Hypothesis Testing & Resampling:
    - whites_reality_check: Corrects for data snooping across multiple strategies.
    - permutation_test: Sign-flip significance testing for Sharpe-style metrics.
    - bootstrap_confidence_intervals: Non-parametric resampling with block support.
    - bootstrap_probability_above_threshold: Probability of meeting a specific performance target.

Anti-Overfitting & Stability:
    - deflated_sharpe_ratio (DSR): Adjusts Sharpe for multiple trials and non-normality.
    - probability_of_backtest_overfitting (PBO): Measures rank-drift in IS vs OOS data.
    - walk_forward_degradation_score: Quantifies performance decay between Train and Test periods.

Multiple Testing Correction:
    - bonferroni_correction: Strict p-value adjustment.
    - benjamini_hochberg_correction: FDR-based p-value adjustment.
"""

from dataclasses import dataclass
import numpy as np
import pandas as pd
from typing import List, Dict, Optional, Tuple, Callable, Any, Literal, TYPE_CHECKING


try:
    from scipy import stats
    HAS_SCIPY = True
except ImportError:
    HAS_SCIPY = False

if TYPE_CHECKING:
    from services.execution.core import TradeRecord

from services.utils.logger import logger


# =========================================================================
# Shared Helpers & Cleaning
# =========================================================================


def _clean_returns(data: np.ndarray | pd.Series) -> np.ndarray:
    """Normalize input to a finite 1D NumPy float array."""
    arr = np.asarray(data, dtype=float)
    return arr[np.isfinite(arr)]


def _sharpe_ratio(rets: np.ndarray, periods_per_year: int = 252) -> float:
    """Stable Sharpe calculation for internal bootstrap/permutations."""
    if len(rets) < 2: return 0.0
    mean, std = np.mean(rets), np.std(rets)
    if std < 1e-12: return 0.0
    return float((mean / std) * np.sqrt(periods_per_year))


def _validate_probability(value: float, name: str) -> None:
    """Ensure a probability value is within (0, 1)."""
    if not 0.0 < value < 1.0:
        raise ValueError(f"{name} must be between 0 and 1 (exclusive)")


def _safe_block_size(block_size: int) -> int:
    """Ensure block size is at least 1."""
    return max(1, int(block_size))


def _safe_n(n: int, min_val: int = 10) -> int:
    """Ensure n is at least min_val."""
    return max(min_val, int(n))


# =========================================================================
# Data Models
# =========================================================================


@dataclass
class BootstrapResult:
    """Point estimate and confidence intervals for a metric."""
    metric_name: str
    point_estimate: float
    mean: float
    median: float
    std: float
    ci_lower: float
    ci_upper: float
    confidence_level: float
    n_bootstrap: int

    def __repr__(self) -> str:
        return (f"{self.metric_name}: {self.point_estimate:.4f} "
                f"[{self.ci_lower:.4f}, {self.ci_upper:.4f}] "
                f"({self.confidence_level*100:.0f}% CI)")


@dataclass
class PermutationTestResult:
    """Significance from random reshuffling."""
    metric_name: str
    observed_value: float
    p_value: float
    is_significant: bool
    significance_level: float
    n_permutations: int
    null_distribution_mean: float
    null_distribution_std: float

    def __repr__(self) -> str:
        sig = "✓ Significant" if self.is_significant else "✗ Not significant"
        return (f"{self.metric_name}: {self.observed_value:.4f}, "
                f"p={self.p_value:.4f} ({sig} at α={self.significance_level})")


@dataclass
class WhitesRealityCheckResult:
    """Data snooping bias correction results."""
    best_strategy_name: str
    best_performance: float
    p_value: float
    is_significant: bool
    significance_level: float
    n_strategies: int
    n_bootstrap: int

    def __repr__(self) -> str:
        sig = "✓ Significant" if self.is_significant else "✗ Likely overfit"
        return (f"Best: {self.best_strategy_name} ({self.best_performance:.4f}), "
                f"p={self.p_value:.4f} ({sig})")


if TYPE_CHECKING:
    from services.analytics.overview import BacktestResult


try:
    from numba import njit
except ImportError:
    def njit(*args, **kwargs):
        def decorator(f):
            return f
        return decorator


# =========================================================================
# Utility & Kernel Helpers
# =========================================================================


@njit(cache=True)
def _bootstrap_kernel(
    returns: np.ndarray, 
    n_bootstrap: int, 
    block_size: int = 1
):
    """
    General bootstrap kernel supporting IID (block_size=1) and circular block bootstrap.
    """
    n = len(returns)
    bootstrap_samples = np.zeros((n_bootstrap, n))
    
    for i in range(n_bootstrap):
        if block_size <= 1:
            indices = np.random.choice(n, size=n, replace=True)
            bootstrap_samples[i] = returns[indices]
        else:
            # Circular Block Bootstrap
            num_blocks = (n + block_size - 1) // block_size
            boot_idx = np.zeros(n, dtype=np.int32)
            for j in range(num_blocks):
                start = np.random.randint(0, n)
                for k in range(block_size):
                    idx = (j * block_size) + k
                    if idx < n:
                        boot_idx[idx] = (start + k) % n
            bootstrap_samples[i] = returns[boot_idx]
            
    return bootstrap_samples


@njit(cache=True)
def _sign_flip_kernel(returns: np.ndarray, n_permutations: int):
    """Generate sign-flipped return series for order-insensitive metrics."""
    n = len(returns)
    results = np.zeros((n_permutations, n))
    for i in range(n_permutations):
        signs = np.random.choice(np.array([-1.0, 1.0]), size=n)
        results[i] = returns * signs
    return results


# =========================================================================
# Core Validation Tests
# =========================================================================


def whites_reality_check(
    strategy_returns: List[np.ndarray | pd.Series],
    benchmark_returns: np.ndarray | pd.Series,
    metric_func: Optional[Callable[[np.ndarray], float]] = None,
    n_bootstrap: int = 1000,
    block_size: int = 1,
    significance_level: float = 0.05,
    seed: Optional[int] = None,
) -> WhitesRealityCheckResult:
    """
    White's Reality Check for data snooping bias.
    Corrects p-values for the luck involved in picking the best of many strategies.
    
    This version uses centered performance differentials to ensure the null 
    hypothesis is that no strategy outperforms the benchmark.
    """
    _validate_probability(significance_level, "significance_level")
    n_bootstrap = _safe_n(n_bootstrap, min_val=10)
    block_size = _safe_block_size(block_size)
    
    if metric_func is None:
        metric_func = _sharpe_ratio

    _validate_probability(significance_level, "significance_level")
    if seed is not None: np.random.seed(seed)
    
    b_rets = _clean_returns(benchmark_returns)
    s_rets_raw = [_clean_returns(r) for r in strategy_returns]
    
    # Filter empty or insufficient strategies
    s_rets = [r for r in s_rets_raw if len(r) >= 3]
    if not s_rets or len(b_rets) < 3:
        return WhitesRealityCheckResult("None", 0.0, 1.0, False, significance_level, len(strategy_returns), n_bootstrap)

    # Align to minimum length
    min_len = min([len(r) for r in s_rets] + [len(b_rets)])

    b_aligned = b_rets[:min_len]
    s_aligned = np.stack([r[:min_len] for r in s_rets])
    
    # Observed performances
    n_strats = len(s_rets)
    obs_bench = metric_func(b_aligned)
    obs_strats = np.array([metric_func(s) for s in s_aligned])
    
    best_idx = np.argmax(obs_strats)
    best_outperf = obs_strats[best_idx] - obs_bench
    
    # Bootstrap centered differentials
    # V_i = Strategy_i - Benchmark
    # Null hypothesis: E[V_i] <= 0
    boot_samples = _bootstrap_kernel(np.arange(min_len), n_bootstrap, block_size)
    boot_max_outperfs = np.zeros(n_bootstrap)
    
    # Centering: Subtract observed mean performance so null mean is 0
    # For many metrics (like Sharpe), we bootstrap the returns and recalculate, 
    # then subtract the original observed metric.
    for b in range(n_bootstrap):
        idx = boot_samples[b].astype(np.int32)
        boot_bench_rets = b_aligned[idx]
        boot_bench_perf = metric_func(boot_bench_rets)
        
        max_v = -1e18
        for s in range(n_strats):
            boot_strat_rets = s_aligned[s][idx]
            boot_strat_perf = metric_func(boot_strat_rets)
            
            # Centered outperformance
            v_centered = (boot_strat_perf - boot_bench_perf) - (obs_strats[s] - obs_bench)
            if v_centered > max_v:
                max_v = v_centered
        
        boot_max_outperfs[b] = max_v
        
    p_val = np.mean(boot_max_outperfs >= best_outperf)
    
    logger.info(f"White's Reality Check: p={p_val:.4f} ({n_strats} strategies)")
    return WhitesRealityCheckResult(
        f"Strategy {best_idx}", float(obs_strats[best_idx]), 
        float(p_val), p_val < significance_level, 
        significance_level, n_strats, n_bootstrap
    )


def permutation_test(
    returns: np.ndarray | pd.Series,
    metric_func: Optional[Callable[[np.ndarray], float]] = None,
    method: Literal["shuffle", "sign_flip"] = "sign_flip",
    n_permutations: int = 1000,
    significance_level: float = 0.05,
    seed: Optional[int] = None,
) -> PermutationTestResult:
    """
    Significance test using random reshuffling or sign-flipping.
    
    Notes:
    - Use method="shuffle" only for order/path-dependent metrics.
    - Use method="sign_flip" for Sharpe-style (order-insensitive) metrics.
    """
    _validate_probability(significance_level, "significance_level")
    n_permutations = _safe_n(n_permutations, min_val=10)
    if seed is not None: np.random.seed(seed)
    if hasattr(returns, "get_equity_df"):
        rets = _returns_from_backtest_result(returns)
    else:
        rets = _clean_returns(returns)
    
    if metric_func is None:
        metric_func = _sharpe_ratio
        metric_name = "Sharpe Ratio"
    else:
        metric_name = getattr(metric_func, "__name__", "Custom Metric")

    if len(rets) < 2:
        return PermutationTestResult(metric_name, 0.0, 1.0, False, significance_level, n_permutations, 0.0, 0.0)

    observed = metric_func(rets)

    if method == "shuffle":
        null_dist = np.array([metric_func(np.random.permutation(rets)) for _ in range(n_permutations)])
    else:
        # Sign-flip is better for Sharpe and order-insensitive metrics
        sign_flipped_samples = _sign_flip_kernel(rets, n_permutations)
        null_dist = np.array([metric_func(s) for s in sign_flipped_samples])

    p_val = np.mean(np.abs(null_dist) >= np.abs(observed))
    
    logger.info(f"Permutation test ({method}): p={p_val:.4f}")
    return PermutationTestResult(
        metric_name, float(observed), float(p_val), 
        p_val < significance_level, significance_level, 
        n_permutations, float(null_dist.mean()), float(null_dist.std())
    )


def bootstrap_confidence_intervals(
    returns: np.ndarray | pd.Series,
    metrics_dict: Optional[Dict[str, Callable[[np.ndarray], float]]] = None,
    n_bootstrap: int = 1000,
    block_size: int = 1,
    confidence_level: float = 0.95,
    periods_per_year: int = 252,
    seed: Optional[int] = None,
) -> List[BootstrapResult]:
    """
    Estimate metric uncertainty using non-parametric bootstrap.
    Supports block bootstrap for time-series dependency.
    """
    _validate_probability(confidence_level, "confidence_level")
    n_bootstrap = _safe_n(n_bootstrap, min_val=10)
    block_size = _safe_block_size(block_size)
    if seed is not None: np.random.seed(seed)
    rets = _clean_returns(returns)
    if len(rets) < 2: return []
    
    if metrics_dict is None:
        metrics_dict = {
            "Sharpe Ratio": lambda r: _sharpe_ratio(r, periods_per_year),
            "Total Return %": lambda r: (np.prod(1 + r) - 1) * 100,
            "Volatility %": lambda r: np.std(r) * np.sqrt(periods_per_year) * 100,
        }

    boot_samples = _bootstrap_kernel(rets, n_bootstrap, block_size)
    results = []

    for name, func in metrics_dict.items():
        point = func(rets)
        boot_vals = np.array([func(s) for s in boot_samples])
        
        # Guard against NaNs in bootstrap distribution
        boot_vals = boot_vals[np.isfinite(boot_vals)]
        if len(boot_vals) == 0: continue

        alpha = 1 - confidence_level
        results.append(BootstrapResult(
            name, float(point), float(boot_vals.mean()), float(np.median(boot_vals)),
            float(boot_vals.std()), float(np.percentile(boot_vals, alpha/2*100)),
            float(np.percentile(boot_vals, (1-alpha/2)*100)), float(confidence_level), n_bootstrap
        ))

    logger.info(f"Bootstrap CIs complete ({'block' if block_size > 1 else 'iid'})")
    return results


def deflated_sharpe_ratio(
    observed_sharpe: float,
    n_trials: int,
    n_observations: int,
    expected_sharpe: float = 0.0,
    skew: float = 0.0,
    kurt: float = 3.0,
) -> Tuple[float, float]:
    """
    Adjust Sharpe ratio for multiple testing and non-normality.

    Returns:
        Tuple[float, float]: (deflated_sharpe_z_stat, p_value)
    """
    if not HAS_SCIPY:
        return 0.0, 1.0

    if n_trials < 1 or n_observations < 3:
        return 0.0, 1.0

    var_sr = (
        1.0
        + 0.5 * observed_sharpe**2
        - skew * observed_sharpe
        + ((kurt - 1.0) / 4.0) * observed_sharpe**2
    ) / (n_observations - 1)

    std_sr = np.sqrt(max(0.0, var_sr))

    if std_sr <= 1e-12:
        return 0.0, 1.0

    if n_trials > 1:
        gamma = 0.57721566490153286
        z_max = (
            (1.0 - gamma) * stats.norm.ppf(1.0 - 1.0 / n_trials)
            + gamma * stats.norm.ppf(1.0 - 1.0 / (n_trials * np.e))
        )
        expected_max_sr = expected_sharpe + std_sr * z_max
    else:
        expected_max_sr = expected_sharpe

    z_stat = (observed_sharpe - expected_max_sr) / std_sr
    p_val = 1.0 - stats.norm.cdf(z_stat)

    logger.info(f"DSR: obs={observed_sharpe:.2f}, exp_max={expected_max_sr:.2f}, z={z_stat:.4f}, p={p_val:.4f}")
    return float(z_stat), float(p_val)


# =========================================================================
# Advanced Robustness Metrics
# =========================================================================


def probability_of_backtest_overfitting(
    in_sample_scores: np.ndarray,
    out_of_sample_scores: np.ndarray,
) -> Dict[str, float]:
    """
    Estimate Probability of Backtest Overfitting (PBO).
    Inputs: arrays shaped (n_windows, n_strategies).
    
    PBO measures how likely the 'best' in-sample strategy is to underperform 
    in the out-of-sample period due to data snooping.
    """
    if in_sample_scores.shape != out_of_sample_scores.shape:
        raise ValueError("in_sample_scores and out_of_sample_scores must have the same shape")

    n_windows, n_strats = in_sample_scores.shape
    if n_windows < 2 or n_strats < 2:
        return {"pbo": 0.0, "rank_loss": 0.0}

    # Relative ranks in each window
    # For each window, find which strategy was best in-sample
    best_is_indices = np.argmax(in_sample_scores, axis=1)
    
    # Check the rank of these 'best' strategies in the out-of-sample period
    # Rank OOS scores: 1.0 = best, 0.0 = worst
    oos_ranks = np.zeros(n_windows)
    for i in range(n_windows):
        window_oos = out_of_sample_scores[i]
        # Percentile rank of the best IS strategy in OOS
        best_idx = best_is_indices[i]
        oos_ranks[i] = np.mean(window_oos <= window_oos[best_idx])

    # PBO is defined as the probability that the rank is below 0.5
    pbo = np.mean(oos_ranks < 0.5)
    
    return {
        "pbo": float(pbo),
        "mean_oos_rank": float(np.mean(oos_ranks)),
        "median_oos_rank": float(np.median(oos_ranks)),
        "rank_loss": float(1.0 - np.mean(oos_ranks))
    }


def walk_forward_degradation_score(
    train_scores: np.ndarray | pd.Series,
    test_scores: np.ndarray | pd.Series,
) -> Dict[str, float]:
    """
    Measures the performance decay from Train/IS to Test/OOS.
    """
    train = _clean_returns(train_scores)
    test = _clean_returns(test_scores)
    
    if len(train) == 0 or len(test) == 0:
        return {}

    mu_train, mu_test = train.mean(), test.mean()
    abs_degrad = mu_train - mu_test
    rel_degrad = (abs_degrad / abs(mu_train)) if mu_train != 0 else 0.0
    
    return {
        "train_mean": float(mu_train),
        "test_mean": float(mu_test),
        "absolute_degradation": float(abs_degrad),
        "relative_degradation_pct": float(rel_degrad * 100.0),
        "degradation_ratio": float(mu_test / mu_train if mu_train != 0 else 1.0)
    }


def bootstrap_probability_above_threshold(
    returns: np.ndarray | pd.Series,
    metric_func: Callable[[np.ndarray], float],
    threshold: float,
    n_bootstrap: int = 1000,
    block_size: int = 1,
    seed: Optional[int] = None,
) -> float:
    """
    Probability that a bootstrapped metric exceeds a given threshold.
    Example: P(Sharpe > 0.5) or P(CAGR > 0).
    """
    if seed is not None: np.random.seed(seed)
    rets = _clean_returns(returns)
    if len(rets) < 5: return 0.0
    
    n_bootstrap = _safe_n(n_bootstrap)
    block_size = _safe_block_size(block_size)
    
    boot_samples = _bootstrap_kernel(rets, n_bootstrap, block_size)
    boot_metrics = np.array([metric_func(s) for s in boot_samples])
    
    prob = np.mean(boot_metrics > threshold)
    return float(prob)


# =========================================================================
# Multiple Testing Corrections
# =========================================================================


def bonferroni_correction(p_values: np.ndarray | List[float], alpha: float = 0.05) -> Dict[str, Any]:
    """Strict Bonferroni correction for multiple hypothesis testing."""
    _validate_probability(alpha, "alpha")
    p_vals = np.asarray(p_values)
    n = len(p_vals)
    adj_alpha = alpha / n if n > 0 else alpha
    
    return {
        "alpha": alpha,
        "adjusted_alpha": adj_alpha,
        "significant_count": int(np.sum(p_vals < adj_alpha)),
        "is_significant": p_vals < adj_alpha
    }


def benjamini_hochberg_correction(p_values: np.ndarray | List[float], alpha: float = 0.05) -> Dict[str, Any]:
    """Benjamini-Hochberg False Discovery Rate (FDR) control."""
    _validate_probability(alpha, "alpha")
    p_vals = np.asarray(p_values)
    n = len(p_vals)
    if n == 0: return {}
    
    # Sort p-values
    sorted_idx = np.argsort(p_vals)
    sorted_p = p_vals[sorted_idx]
    
    # BH critical values: (i/n) * alpha
    crit_vals = (np.arange(1, n + 1) / n) * alpha
    
    # Find the largest k such that p(k) <= crit_val(k)
    significant = sorted_p <= crit_vals
    if not np.any(significant):
        k = 0
    else:
        k = np.max(np.where(significant)[0]) + 1
        
    # All p-values up to rank k are considered significant
    reject = np.zeros(n, dtype=bool)
    if k > 0:
        reject[sorted_idx[:k]] = True
        
    return {
        "alpha": alpha,
        "k_limit": k,
        "significant_count": k,
        "reject": reject
    }


def sample_size_warning(n_observations: int, min_recommended: int = 100) -> Dict[str, Any]:
    """Audit metric reliability based on sample size."""
    return {
        "n_observations": n_observations,
        "min_recommended": min_recommended,
        "is_sufficient": n_observations >= min_recommended,
        "reliability_score": min(1.0, n_observations / min_recommended)
    }


def stability_score(
    walk_forward_results: List[Dict[str, Any]], metric_key: str = "sharpe_ratio"
) -> Dict[str, float]:
    """Consistency of performance across walk-forward windows."""
    if not walk_forward_results:
        return {"test_mean": 0.0, "test_std": 0.0, "stability_ratio": 0.0, "degradation": 1.0, "consistency": 0.0}

    t_key, v_key = f"train_{metric_key}", f"test_{metric_key}"
    train_m = np.array([w[t_key] for w in walk_forward_results if t_key in w])
    test_m = np.array([w[v_key] for w in walk_forward_results if v_key in w])

    if len(test_m) == 0: return {"test_mean": 0.0, "test_std": 0.0, "stability_ratio": 0.0, "degradation": 1.0, "consistency": 0.0}
    
    mu, sigma = test_m.mean(), test_m.std()
    train_mu = train_m.mean() if len(train_m) > 0 else 0.0
    
    stability = {
        "test_mean": float(mu), "test_std": float(sigma), "test_min": float(test_m.min()),
        "test_max": float(test_m.max()), "stability_ratio": float(mu / sigma if sigma > 0 else 0.0),
        "degradation": float((train_mu - mu) / abs(train_mu) if train_mu != 0 else 0.0),
        "consistency": float(np.mean(test_m > 0) * 100)
    }
    logger.info(f"Stability: mean={mu:.4f}, degradation={stability['degradation']:.2%}")
    return stability


# =========================================================================
# BacktestResult Wrappers
# =========================================================================


def _returns_from_backtest_result(result: "BacktestResult") -> np.ndarray:
    """Extract return array from a BacktestResult object."""
    try:
        eq = result.get_equity_df()
        if eq is None or len(eq) < 2:
            return np.array([], dtype=float)
        return _clean_returns(eq["equity"].pct_change().dropna())
    except Exception:
        return np.array([], dtype=float)


def whites_reality_check_backtests(
    strategy_results: List["BacktestResult"],
    benchmark_result: "BacktestResult",
    metric_func: Optional[Callable[[np.ndarray], float]] = None,
    **kwargs
) -> WhitesRealityCheckResult:
    """Wrapper for White's Reality Check taking BacktestResult objects."""
    valid_data = [
        (r.strategy_name, _returns_from_backtest_result(r))
        for r in strategy_results
    ]
    
    # Filter for sufficient length
    valid_data = [(name, rets) for name, rets in valid_data if len(rets) >= 3]
    
    if not valid_data:
        return WhitesRealityCheckResult(
            "None", 0.0, 1.0, False,
            kwargs.get("significance_level", 0.05),
            len(strategy_results),
            kwargs.get("n_bootstrap", 1000)
        )
        
    names = [x[0] for x in valid_data]
    s_rets = [x[1] for x in valid_data]
    b_rets = _returns_from_backtest_result(benchmark_result)
    
    if metric_func is None:
        metric_func = _sharpe_ratio

    result = whites_reality_check(s_rets, b_rets, metric_func=metric_func, **kwargs)
    
    # Correctly map the relative "Strategy X" name back to the original strategy name
    try:
        best_idx_str = result.best_strategy_name.split()[-1]
        if best_idx_str.isdigit():
            best_idx = int(best_idx_str)
            result.best_strategy_name = names[best_idx]
    except Exception:
        pass
        
    return result


def permutation_test_backtest(
    strategy_result: "BacktestResult",
    **kwargs
) -> PermutationTestResult:
    """Wrapper for permutation test taking a BacktestResult object."""
    rets = _returns_from_backtest_result(strategy_result)
    return permutation_test(rets, **kwargs)


def bootstrap_confidence_intervals_backtest(
    strategy_result: "BacktestResult",
    **kwargs
) -> List[BootstrapResult]:
    """Wrapper for bootstrap CIs taking a BacktestResult object."""
    rets = _returns_from_backtest_result(strategy_result)
    return bootstrap_confidence_intervals(rets, **kwargs)


# =========================================================================
# Reporting Utilities
# =========================================================================


def print_statistical_validation_report(
    permutation_result: Optional[PermutationTestResult] = None,
    bootstrap_results: Optional[List[BootstrapResult]] = None,
    deflated_sharpe_result: Optional[Tuple[float, float]] = None,
    stability_result: Optional[Dict[str, float]] = None,
    whites_result: Optional[WhitesRealityCheckResult] = None,
) -> None:
    """Print comprehensive statistical validation report."""
    print("\n" + "=" * 70 + "\nSTATISTICAL VALIDATION REPORT\n" + "=" * 70)

    if permutation_result:
        print("\n" + "-" * 70 + "\nPERMUTATION TEST\n" + "-" * 70)
        print(f"  Metric: {permutation_result.metric_name}\n  Observed: {permutation_result.observed_value:>10.4f}")
        print(f"  P-value:  {permutation_result.p_value:>10.4f}\n  Result:   {'✓ Significant' if permutation_result.is_significant else '✗ Not Significant'}")

    if bootstrap_results:
        print("\n" + "-" * 70 + "\nBOOTSTRAP CONFIDENCE INTERVALS\n" + "-" * 70)
        for br in bootstrap_results:
            print(f"  {br.metric_name}: {br.point_estimate:.4f} [{br.ci_lower:.4f}, {br.ci_upper:.4f}]")

    if deflated_sharpe_result:
        dsr, p = deflated_sharpe_result
        print("\n" + "-" * 70 + "\nDEFLATED SHARPE RATIO\n" + "-" * 70)
        print(f"  DSR:      {dsr:>10.4f}\n  P-value:  {p:>10.4f}")

    if stability_result:
        print("\n" + "-" * 70 + "\nWALK-FORWARD STABILITY\n" + "-" * 70)
        print(f"  Test Mean: {stability_result['test_mean']:>10.4f}\n  Ratio:     {stability_result['stability_ratio']:>10.4f}")
        print(f"  Degrad:    {stability_result['degradation']:>10.2%}\n  Consist:   {stability_result['consistency']:>10.1f}%")

    if whites_result:
        print("\n" + "-" * 70 + "\nWHITE'S REALITY CHECK\n" + "-" * 70)
        print(f"  Best:     {whites_result.best_strategy_name}\n  P-value:  {whites_result.p_value:>10.4f}")
        print(f"  Result:   {'✓ Significant' if whites_result.is_significant else '✗ Likely Overfit'}")
    print("\n" + "=" * 70 + "\n")
