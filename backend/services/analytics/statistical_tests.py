"""
Statistical Validation Module.

Statistical tests to validate strategy robustness and detect overfitting.
Includes White's Reality Check, permutation tests, bootstrap confidence intervals,
deflated Sharpe ratio, and walk-forward stability analysis.

Summary of Methods:
------------------
Data Models:
    - BootstrapResult: Container for point estimates and confidence intervals.
    - PermutationTestResult: Container for p-values and significance from random reshuffling.
    - WhitesRealityCheckResult: Container for data snooping bias test results.

Core Validation Tests:
    - whites_reality_check: Corrects for data snooping when selecting the best of many strategies.
    - permutation_test: Tests if observed performance is significantly different from random.
    - bootstrap_confidence_intervals: Non-parametric resampling to estimate metric uncertainty.
    - deflated_sharpe_ratio (DSR): Adjusts Sharpe ratio for multiple trials and non-normality.
    - stability_score: Measures consistency of performance across walk-forward windows.

Reporting Utilities:
    - print_statistical_validation_report: Formats and prints all validation results.
"""

from dataclasses import dataclass
from typing import TYPE_CHECKING, Any, Callable, Dict, List, Optional, Tuple

import numpy as np
from scipy import stats

if TYPE_CHECKING:
    from backend.services.execution.core import TradeRecord

from backend.common.logger import logger


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
def _whites_reality_check_kernel(
    strategy_returns_aligned, benchmark_returns_aligned, n_bootstrap, min_length
):
    n_strategies = len(strategy_returns_aligned)
    bootstrap_max_outperformances = np.zeros(n_bootstrap)

    for b in range(n_bootstrap):
        indices = np.random.choice(min_length, size=min_length, replace=True)
        max_outperf = -1e18
        
        boot_bench = benchmark_returns_aligned[indices]
        bench_mean = np.mean(boot_bench)
        bench_std = np.std(boot_bench)
        bench_sharpe = (bench_mean * 252) / (bench_std * 15.8745) if bench_std > 0 else 0.0

        for s in range(n_strategies):
            strat_returns = strategy_returns_aligned[s]
            boot_strat = strat_returns[indices]
            strat_mean = np.mean(boot_strat)
            strat_std = np.std(boot_strat)
            strat_sharpe = (strat_mean * 252) / (strat_std * 15.8745) if strat_std > 0 else 0.0
            
            outperf = strat_sharpe - bench_sharpe
            if outperf > max_outperf:
                max_outperf = outperf
        
        bootstrap_max_outperformances[b] = max_outperf
    
    return bootstrap_max_outperformances


@njit(cache=True)
def _permutation_test_sharpe_kernel(returns, n_permutations):
    null_distribution = np.zeros(n_permutations)
    n = len(returns)
    for i in range(n_permutations):
        permuted = np.random.permutation(returns)
        mean, std = np.mean(permuted), np.std(permuted)
        null_distribution[i] = (mean * 252) / (std * 15.8745) if std > 0 else 0.0
    return null_distribution


@njit(cache=True)
def _bootstrap_standard_metrics_kernel(returns, n_bootstrap):
    n_samples = len(returns)
    sharpe_vals = np.zeros(n_bootstrap)
    total_ret_vals = np.zeros(n_bootstrap)
    vol_vals = np.zeros(n_bootstrap)
    
    for b in range(n_bootstrap):
        indices = np.random.choice(n_samples, size=n_samples, replace=True)
        boot_returns = returns[indices]
        mean, std = np.mean(boot_returns), np.std(boot_returns)
        
        sharpe_vals[b] = (mean * 252) / (std * 15.8745) if std > 0 else 0.0
        prod = 1.0
        for r in boot_returns: prod *= (1.0 + r)
        total_ret_vals[b] = (prod - 1.0) * 100.0
        vol_vals[b] = std * 15.8745 * 100.0
        
    return sharpe_vals, total_ret_vals, vol_vals


# =========================================================================
# Core Validation Tests
# =========================================================================


def whites_reality_check(
    strategy_results: List["BacktestResult"],
    benchmark_result: "BacktestResult",
    metric_func: Optional[Callable[["BacktestResult"], float]] = None,
    n_bootstrap: int = 1000,
    significance_level: float = 0.05,
    seed: Optional[int] = None,
) -> WhitesRealityCheckResult:
    """White's Reality Check for data snooping bias across multiple strategies."""
    logger.info(f"Running White's Reality Check with {len(strategy_results)} strategies")

    if metric_func is None:
        metric_func = lambda r: float(r.sharpe_ratio or 0.0)

    if seed is not None: np.random.seed(seed)

    strat_perfs = [metric_func(r) for r in strategy_results]
    bench_perf = metric_func(benchmark_result)
    best_idx = np.argmax(strat_perfs)
    best_perf = strat_perfs[best_idx]
    best_name = strategy_results[best_idx].strategy_name
    best_outperf = best_perf - bench_perf

    strat_rets_list = []
    for r in strategy_results:
        eq = r.get_equity_df()
        strat_rets_list.append(eq["equity"].pct_change().dropna().values.astype(float) if len(eq) > 0 else np.array([], dtype=float))

    bench_eq = benchmark_result.get_equity_df()
    bench_rets = bench_eq["equity"].pct_change().dropna().values.astype(float) if len(bench_eq) > 0 else np.array([], dtype=float)

    lengths = [len(r) for r in strat_rets_list if len(r) > 0]
    if len(bench_rets) > 0: lengths.append(len(bench_rets))
    min_len = min(lengths) if lengths else 0

    if min_len < 2:
        return WhitesRealityCheckResult(best_name, best_perf, 1.0, False, significance_level, len(strategy_results), n_bootstrap)

    strat_rets_aligned = np.stack([r[:min_len] for r in strat_rets_list if len(r) >= min_len])
    bench_rets_aligned = bench_rets[:min_len]

    boot_max_outperfs = _whites_reality_check_kernel(strat_rets_aligned, bench_rets_aligned, int(n_bootstrap), int(min_len))
    p_val = np.mean(boot_max_outperfs >= best_outperf)

    logger.success(f"White's Reality Check complete: p={p_val:.4f}")
    return WhitesRealityCheckResult(best_name, best_perf, float(p_val), p_val < significance_level, significance_level, len(strategy_results), n_bootstrap)


def permutation_test(
    strategy_result: "BacktestResult",
    metric_func: Optional[Callable[[np.ndarray], float]] = None,
    n_permutations: int = 1000,
    significance_level: float = 0.05,
    seed: Optional[int] = None,
) -> PermutationTestResult:
    """Test if observed performance is significantly different from random returns."""
    logger.info(f"Running permutation test for {strategy_result.strategy_name}")

    if metric_func is None:
        metric_func = lambda r: float((r.mean() * 252) / (r.std() * np.sqrt(252))) if r.std() > 0 else 0.0
        metric_name = "Sharpe Ratio"
        use_opt = True
    else:
        metric_name = metric_func.__name__
        use_opt = False

    if seed is not None: np.random.seed(seed)
    eq = strategy_result.get_equity_df()
    if len(eq) < 2:
        return PermutationTestResult(metric_name, 0.0, 1.0, False, significance_level, n_permutations, 0.0, 0.0)

    rets = eq["equity"].pct_change().dropna().values.astype(float)
    observed = metric_func(rets)

    if use_opt:
        null_dist = _permutation_test_sharpe_kernel(rets, int(n_permutations))
    else:
        null_dist = np.array([metric_func(np.random.permutation(rets)) for _ in range(n_permutations)])

    p_val = np.mean(np.abs(null_dist) >= np.abs(observed))
    logger.success(f"Permutation test complete: p={p_val:.4f}")
    return PermutationTestResult(metric_name, float(observed), float(p_val), p_val < significance_level, significance_level, n_permutations, float(null_dist.mean()), float(null_dist.std()))


def bootstrap_confidence_intervals(
    strategy_result: "BacktestResult",
    metrics_dict: Optional[Dict[str, Callable[[np.ndarray], float]]] = None,
    n_bootstrap: int = 1000,
    confidence_level: float = 0.95,
    seed: Optional[int] = None,
) -> List[BootstrapResult]:
    """Estimate uncertainty in performance metrics using non-parametric bootstrap."""
    logger.info(f"Calculating bootstrap CIs for {strategy_result.strategy_name}")
    use_opt = metrics_dict is None
    if metrics_dict is None:
        metrics_dict = {
            "Sharpe Ratio": lambda r: (r.mean() * 252) / (r.std() * np.sqrt(252)) if r.std() > 0 else 0,
            "Total Return %": lambda r: ((1 + r).prod() - 1) * 100,
            "Volatility %": lambda r: r.std() * np.sqrt(252) * 100,
        }

    if seed is not None: np.random.seed(seed)
    eq = strategy_result.get_equity_df()
    if len(eq) < 2: return []
    rets = eq["equity"].pct_change().dropna().values.astype(float)
    n_samples = len(rets)

    results = []
    if use_opt:
        s_dist, r_dist, v_dist = _bootstrap_standard_metrics_kernel(rets, int(n_bootstrap))
        dists = {"Sharpe Ratio": s_dist, "Total Return %": r_dist, "Volatility %": v_dist}

    for name, func in metrics_dict.items():
        point = func(rets)
        if use_opt and name in dists:
            boot_vals = dists[name]
        else:
            boot_vals = np.array([func(rets[np.random.choice(n_samples, n_samples, True)]) for _ in range(n_bootstrap)])

        alpha = 1 - confidence_level
        results.append(BootstrapResult(
            name, float(point), float(boot_vals.mean()), float(np.median(boot_vals)),
            float(boot_vals.std()), float(np.percentile(boot_vals, alpha/2*100)),
            float(np.percentile(boot_vals, (1-alpha/2)*100)), float(confidence_level), int(n_bootstrap)
        ))

    logger.success(f"Bootstrap CIs calculated for {len(metrics_dict)} metrics")
    return results


def deflated_sharpe_ratio(
    observed_sharpe: float,
    n_trials: int,
    n_observations: int,
    expected_sharpe: float = 0.0,
    skew: float = 0.0,
    kurt: float = 3.0,
) -> Tuple[float, float]:
    """Adjust Sharpe ratio for multiple testing and non-normality (DSR)."""
    logger.info(f"Calculating Deflated Sharpe Ratio (trials={n_trials}, n={n_observations})")
    if n_trials < 1 or n_observations < 2: return 0.0, 1.0

    var_sr = (1.0 + 0.5 * observed_sharpe**2 - skew * observed_sharpe + ((kurt - 1) / 4) * observed_sharpe**2) / n_observations
    std_sr = np.sqrt(var_sr)
    
    if n_trials > 1:
        z_max = stats.norm.ppf(1 - 1 / n_trials)
        expected_max_sr = expected_sharpe + std_sr * (1 - 0.5772156649) * z_max
    else:
        expected_max_sr = expected_sharpe

    deflated_sr = (observed_sharpe - expected_max_sr) / std_sr if std_sr > 0 else 0.0
    p_val = 1 - stats.norm.cdf(deflated_sr)
    logger.success(f"DSR = {deflated_sr:.4f}, p-value = {p_val:.4f}")
    return float(deflated_sr), float(p_val)


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
    logger.success(f"Stability: mean={mu:.4f}, degradation={stability['degradation']:.2%}")
    return stability


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
