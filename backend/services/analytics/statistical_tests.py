"""
Statistical Validation Module.

Statistical tests to validate strategy robustness and detect overfitting.
Includes White's Reality Check, permutation tests, bootstrap confidence intervals,
deflated Sharpe ratio, and walk-forward stability analysis.
"""

from dataclasses import dataclass
from typing import TYPE_CHECKING, Any, Callable, Dict, List, Optional, Tuple

import numpy as np
from scipy import stats

if TYPE_CHECKING:
    from backend.services.execution.core import TradeRecord

from backend.common.logger import logger

# ============================================================================
# DATA MODELS
# ============================================================================


@dataclass
class BootstrapResult:
    """
    Bootstrap confidence interval result.

    Contains point estimate and confidence intervals for a metric.
    """

    metric_name: str
    point_estimate: float
    mean: float
    median: float
    std: float
    ci_lower: float  # Lower bound of confidence interval
    ci_upper: float  # Upper bound of confidence interval
    confidence_level: float  # e.g., 0.95 for 95%
    n_bootstrap: int

    def __repr__(self) -> str:
        """Return string representation."""
        return (
            f"{self.metric_name}: {self.point_estimate:.4f} "
            f"[{self.ci_lower:.4f}, {self.ci_upper:.4f}] "
            f"({self.confidence_level*100:.0f}% CI)"
        )


@dataclass
class PermutationTestResult:
    """
    Permutation test result.

    Tests if observed metric is significantly different from random.
    """

    metric_name: str
    observed_value: float
    p_value: float
    is_significant: bool
    significance_level: float
    n_permutations: int
    null_distribution_mean: float
    null_distribution_std: float

    def __repr__(self) -> str:
        """Return string representation."""
        sig = "✓ Significant" if self.is_significant else "✗ Not significant"
        return (
            f"{self.metric_name}: {self.observed_value:.4f}, "
            f"p={self.p_value:.4f} ({sig} at α={self.significance_level})"
        )


@dataclass
class WhitesRealityCheckResult:
    """
    White's Reality Check result.

    Tests if the best strategy from multiple strategies is significantly better
    than a benchmark, accounting for data snooping bias.
    """

    best_strategy_name: str
    best_performance: float
    p_value: float
    is_significant: bool
    significance_level: float
    n_strategies: int
    n_bootstrap: int

    def __repr__(self) -> str:
        """Return string representation."""
        sig = (
            "✓ Significant"
            if self.is_significant
            else "✗ Not significant (likely overfit)"
        )
        return (
            f"Best: {self.best_strategy_name} ({self.best_performance:.4f}), "
            f"p={self.p_value:.4f} ({sig})"
        )


# ============================================================================
# WHITE'S REALITY CHECK
# ============================================================================


def whites_reality_check(
    strategy_results: List["BacktestResult"],
    benchmark_result: "BacktestResult",
    metric_func: Optional[Callable[["BacktestResult"], float]] = None,
    n_bootstrap: int = 1000,
    significance_level: float = 0.05,
    seed: Optional[int] = None,
) -> WhitesRealityCheckResult:
    """
    White's Reality Check for data snooping.

    Tests if the best strategy among multiple strategies is genuinely superior
    to a benchmark, or if it's just lucky (overfit). Accounts for multiple testing.

    Reference: White, Halbert (2000). "A Reality Check for Data Snooping."

    Args:
        strategy_results: List of backtest results to test
        benchmark_result: Benchmark backtest result
        metric_func: Function to calculate performance metric (default: Sharpe ratio)
        n_bootstrap: Number of bootstrap samples
        significance_level: Significance level (e.g., 0.05 for 5%)
        seed: Random seed for reproducibility

    Returns:
        WhitesRealityCheckResult with test outcome
    """
    logger.info(
        f"Running White's Reality Check with {len(strategy_results)} strategies"
    )

    if metric_func is None:
        # Default to Sharpe ratio
        def metric_func(result: "BacktestResult") -> float:
            return float(result.sharpe_ratio or 0.0)

    if seed is not None:
        np.random.seed(seed)

    # Calculate performance for all strategies
    strategy_performances = [metric_func(r) for r in strategy_results]
    benchmark_performance = metric_func(benchmark_result)

    # Find best strategy
    best_idx = np.argmax(strategy_performances)
    best_performance = strategy_performances[best_idx]
    best_strategy_name = strategy_results[best_idx].strategy_name

    # Calculate outperformance
    outperformances = [perf - benchmark_performance for perf in strategy_performances]
    best_outperformance = max(outperformances)

    # Bootstrap procedure
    # Generate returns for strategies and benchmark
    strategy_returns_list = []
    for result in strategy_results:
        equity_df = result.get_equity_df()
        if len(equity_df) > 0:
            returns = equity_df["equity"].pct_change().dropna()
            strategy_returns_list.append(returns.values)
        else:
            strategy_returns_list.append(np.array([]))

    benchmark_equity_df = benchmark_result.get_equity_df()
    if len(benchmark_equity_df) > 0:
        benchmark_returns = benchmark_equity_df["equity"].pct_change().dropna().values
    else:
        benchmark_returns = np.array([])

    # Find minimum length for alignment
    min_length = (
        min(
            min(len(r) for r in strategy_returns_list if len(r) > 0),
            len(benchmark_returns),
        )
        if any(len(r) > 0 for r in strategy_returns_list) and len(benchmark_returns) > 0
        else 0
    )

    if min_length < 2:
        logger.warning("Insufficient data for White's Reality Check")
        return WhitesRealityCheckResult(
            best_strategy_name=best_strategy_name,
            best_performance=best_performance,
            p_value=1.0,
            is_significant=False,
            significance_level=significance_level,
            n_strategies=len(strategy_results),
            n_bootstrap=n_bootstrap,
        )

    # Align returns
    strategy_returns_aligned = [r[:min_length] for r in strategy_returns_list]
    benchmark_returns_aligned = benchmark_returns[:min_length]

    # Bootstrap distribution of maximum outperformance
    bootstrap_max_outperformances = []

    for _ in range(n_bootstrap):
        # Resample returns with replacement
        indices = np.random.choice(min_length, size=min_length, replace=True)

        # Calculate metric for each strategy on bootstrap sample
        bootstrap_outperformances = []
        for strat_returns in strategy_returns_aligned:
            boot_strat_returns = strat_returns[indices]
            boot_bench_returns = benchmark_returns_aligned[indices]

            # Calculate Sharpe ratio for bootstrap sample
            strat_sharpe = (
                (boot_strat_returns.mean() * 252)
                / (boot_strat_returns.std() * np.sqrt(252))
                if boot_strat_returns.std() > 0
                else 0
            )
            bench_sharpe = (
                (boot_bench_returns.mean() * 252)
                / (boot_bench_returns.std() * np.sqrt(252))
                if boot_bench_returns.std() > 0
                else 0
            )

            bootstrap_outperformances.append(strat_sharpe - bench_sharpe)

        # Get maximum outperformance for this bootstrap sample
        bootstrap_max_outperformances.append(max(bootstrap_outperformances))

    # Calculate p-value
    # p-value = proportion of bootstrap samples where max outperformance >= observed
    p_value = np.mean(np.array(bootstrap_max_outperformances) >= best_outperformance)

    is_significant = p_value < significance_level

    wr_result: WhitesRealityCheckResult = WhitesRealityCheckResult(
        best_strategy_name=best_strategy_name,
        best_performance=best_performance,
        p_value=p_value,
        is_significant=is_significant,
        significance_level=significance_level,
        n_strategies=len(strategy_results),
        n_bootstrap=n_bootstrap,
    )

    logger.success(
        f"White's Reality Check complete: p={p_value:.4f}, significant={is_significant}"
    )

    return wr_result


# ============================================================================
# PERMUTATION TEST
# ============================================================================


def permutation_test(
    strategy_result: "BacktestResult",
    metric_func: Optional[Callable[[np.ndarray], float]] = None,
    n_permutations: int = 1000,
    significance_level: float = 0.05,
    seed: Optional[int] = None,
) -> PermutationTestResult:
    """
    Permutation test for strategy significance.

    Tests if the observed performance metric is significantly different from
    random (null hypothesis: returns are random).

    Args:
        strategy_result: Backtest result to test
        metric_func: Function to calculate metric (default: Sharpe ratio)
        n_permutations: Number of random permutations
        significance_level: Significance level
        seed: Random seed

    Returns:
        PermutationTestResult
    """
    logger.info(f"Running permutation test for {strategy_result.strategy_name}")

    if metric_func is None:
        # Default to Sharpe ratio
        def metric_func(returns: np.ndarray) -> float:
            if len(returns) < 2 or returns.std() == 0:
                return 0.0
            return float((returns.mean() * 252) / (returns.std() * np.sqrt(252)))

        metric_name = "Sharpe Ratio"
    else:
        metric_name = metric_func.__name__

    if seed is not None:
        np.random.seed(seed)

    # Get returns
    equity_df = strategy_result.get_equity_df()
    if len(equity_df) < 2:
        logger.warning("Insufficient data for permutation test")
        return PermutationTestResult(
            metric_name=metric_name,
            observed_value=0.0,
            p_value=1.0,
            is_significant=False,
            significance_level=significance_level,
            n_permutations=n_permutations,
            null_distribution_mean=0.0,
            null_distribution_std=0.0,
        )

    returns = equity_df["equity"].pct_change().dropna().values

    # Calculate observed metric
    observed_value = metric_func(returns)

    # Generate null distribution by permuting returns
    null_distribution = []

    for _ in range(n_permutations):
        # Randomly permute returns
        permuted_returns = np.random.permutation(returns)
        null_value = metric_func(permuted_returns)
        null_distribution.append(null_value)

    null_distribution_array = np.array(null_distribution)

    # Calculate p-value (two-tailed test)
    p_value = np.mean(np.abs(null_distribution_array) >= np.abs(observed_value))

    is_significant = p_value < significance_level

    result = PermutationTestResult(
        metric_name=metric_name,
        observed_value=observed_value,
        p_value=p_value,
        is_significant=is_significant,
        significance_level=significance_level,
        n_permutations=n_permutations,
        null_distribution_mean=float(np.mean(null_distribution_array)),
        null_distribution_std=float(np.std(null_distribution_array)),
    )

    logger.success(
        f"Permutation test complete: p={p_value:.4f}, significant={is_significant}"
    )

    return result


# ============================================================================
# BOOTSTRAP CONFIDENCE INTERVALS
# ============================================================================


def bootstrap_confidence_intervals(
    strategy_result: "BacktestResult",
    metrics: Optional[Dict[str, Callable[[np.ndarray], float]]] = None,
    n_bootstrap: int = 1000,
    confidence_level: float = 0.95,
    seed: Optional[int] = None,
) -> List[BootstrapResult]:
    """
    Calculate bootstrap confidence intervals for performance metrics.

    Uses non-parametric bootstrap to estimate uncertainty in performance metrics.

    Args:
        strategy_result: Backtest result
        metrics: Dict of metric_name -> function(returns) mappings
        n_bootstrap: Number of bootstrap samples
        confidence_level: Confidence level (e.g., 0.95 for 95%)
        seed: Random seed

    Returns:
        List of BootstrapResult objects
    """
    logger.info(f"Calculating bootstrap CIs for {strategy_result.strategy_name}")

    if metrics is None:
        # Default metrics
        metrics = {
            "Sharpe Ratio": lambda r: (
                (r.mean() * 252) / (r.std() * np.sqrt(252)) if r.std() > 0 else 0
            ),
            "Total Return %": lambda r: ((1 + r).prod() - 1) * 100,
            "Volatility %": lambda r: r.std() * np.sqrt(252) * 100,
        }

    if seed is not None:
        np.random.seed(seed)

    # Get returns
    equity_df = strategy_result.get_equity_df()
    if len(equity_df) < 2:
        logger.warning("Insufficient data for bootstrap")
        return []

    returns = equity_df["equity"].pct_change().dropna().values
    n_samples = len(returns)

    results = []

    for metric_name, metric_func in metrics.items():
        # Calculate point estimate
        point_estimate = metric_func(returns)

        # Bootstrap distribution
        bootstrap_values = []

        for _ in range(n_bootstrap):
            # Resample with replacement
            boot_returns = returns[
                np.random.choice(n_samples, size=n_samples, replace=True)
            ]
            boot_value = metric_func(boot_returns)
            bootstrap_values.append(boot_value)

        bootstrap_values_array = np.array(bootstrap_values)

        # Calculate confidence intervals
        alpha = 1 - confidence_level
        ci_lower = np.percentile(bootstrap_values_array, alpha / 2 * 100)
        ci_upper = np.percentile(bootstrap_values_array, (1 - alpha / 2) * 100)

        result = BootstrapResult(
            metric_name=metric_name,
            point_estimate=point_estimate,
            mean=float(np.mean(bootstrap_values_array)),
            median=float(np.median(bootstrap_values_array)),
            std=float(np.std(bootstrap_values_array)),
            ci_lower=ci_lower,
            ci_upper=ci_upper,
            confidence_level=confidence_level,
            n_bootstrap=n_bootstrap,
        )

        results.append(result)

    logger.success(f"Bootstrap CIs calculated for {len(metrics)} metrics")

    return results


# ============================================================================
# DEFLATED SHARPE RATIO
# ============================================================================


def deflated_sharpe_ratio(
    observed_sharpe: float,
    n_trials: int,
    n_observations: int,
    expected_sharpe: float = 0.0,
    skewness: float = 0.0,
    kurtosis: float = 3.0,
) -> Tuple[float, float]:
    """
    Calculate Deflated Sharpe Ratio (DSR).

    Adjusts Sharpe ratio for multiple testing and non-normality.
    Answers: "What's the probability that the Sharpe ratio is due to luck?"

    Reference: Bailey & López de Prado (2014). "The Deflated Sharpe Ratio:
    Correcting for Selection Bias, Backtest Overfitting, and Non-Normality."

    Args:
        observed_sharpe: Observed Sharpe ratio from backtest
        n_trials: Number of strategies tested (trials)
        n_observations: Number of return observations
        expected_sharpe: Expected Sharpe under null (usually 0)
        skewness: Return skewness
        kurtosis: Return kurtosis (3 = normal)

    Returns:
        Tuple of (deflated_sharpe, p_value)
        - deflated_sharpe: Adjusted Sharpe ratio accounting for trials
        - p_value: Probability that observed Sharpe is due to luck
    """
    logger.info(
        f"Calculating Deflated Sharpe Ratio (trials={n_trials}, n={n_observations})"
    )

    if n_trials < 1 or n_observations < 2:
        return 0.0, 1.0

    # Variance of Sharpe ratio estimator (accounting for non-normality)
    # Var(SR) = (1 + (1/2)*SR^2 - skew*SR + ((kurtosis-1)/4)*SR^2) / n
    var_sharpe = (
        1.0
        + 0.5 * observed_sharpe**2
        - skewness * observed_sharpe
        + ((kurtosis - 1) / 4) * observed_sharpe**2
    ) / n_observations

    # Standard deviation of Sharpe ratio
    std_sharpe = np.sqrt(var_sharpe)

    # Expected maximum Sharpe ratio among n_trials (accounting for selection bias)
    # E[max(SR)] ≈ expected_SR + std(SR) * z_max
    # where z_max ≈ (1 - γ) * Φ^(-1)(1 - 1/n_trials)
    # γ ≈ 0.5772 (Euler-Mascheroni constant)

    euler_mascheroni = 0.5772156649

    if n_trials > 1:
        # Inverse CDF of standard normal at (1 - 1/n_trials)
        z_max = stats.norm.ppf(1 - 1 / n_trials)
        expected_max_sharpe = (
            expected_sharpe + std_sharpe * (1 - euler_mascheroni) * z_max
        )
    else:
        expected_max_sharpe = expected_sharpe

    # Deflated Sharpe ratio
    if std_sharpe > 0:
        deflated_sharpe = (observed_sharpe - expected_max_sharpe) / std_sharpe
    else:
        deflated_sharpe = 0.0

    # Calculate p-value (probability observed Sharpe is due to luck)
    # p-value = P(Z > deflated_sharpe) where Z ~ N(0, 1)
    p_value = 1 - stats.norm.cdf(deflated_sharpe)

    logger.success(f"DSR = {deflated_sharpe:.4f}, p-value = {p_value:.4f}")

    return deflated_sharpe, p_value


# ============================================================================
# WALK-FORWARD STABILITY
# ============================================================================


def stability_score(
    walk_forward_results: List[Dict[str, Any]], metric_key: str = "sharpe_ratio"
) -> Dict[str, float]:
    """
    Calculate stability score for walk-forward analysis.

    Measures consistency of performance across walk-forward windows.
    High stability = robust strategy. Low stability = overfitting.

    Args:
        walk_forward_results: List of walk-forward window results
            Each dict should have: {'train_metric': float, 'test_metric': float, ...}
        metric_key: Key for metric to analyze (e.g., 'sharpe_ratio', 'total_return')

    Returns:
        Dict with stability metrics:
        - test_mean: Average test performance
        - test_std: Std dev of test performance
        - test_min: Worst test performance
        - test_max: Best test performance
        - stability_ratio: test_mean / test_std (higher is better)
        - degradation: (train_mean - test_mean) / train_mean (lower is better)
        - consistency: % of windows where test > 0
    """
    logger.info(f"Calculating stability score for {len(walk_forward_results)} windows")

    if len(walk_forward_results) == 0:
        return {
            "test_mean": 0.0,
            "test_std": 0.0,
            "test_min": 0.0,
            "test_max": 0.0,
            "stability_ratio": 0.0,
            "degradation": 1.0,
            "consistency": 0.0,
        }

    # Extract test metrics
    train_key = f"train_{metric_key}"
    test_key = f"test_{metric_key}"

    train_metrics = [w[train_key] for w in walk_forward_results if train_key in w]
    test_metrics = [w[test_key] for w in walk_forward_results if test_key in w]

    if len(test_metrics) == 0:
        logger.warning("No test metrics found in walk-forward results")
        return {
            "test_mean": 0.0,
            "test_std": 0.0,
            "test_min": 0.0,
            "test_max": 0.0,
            "stability_ratio": 0.0,
            "degradation": 1.0,
            "consistency": 0.0,
        }

    test_metrics_array = np.array(test_metrics)
    train_metrics_array = (
        np.array(train_metrics) if len(train_metrics) > 0 else np.array([0])
    )

    # Calculate statistics
    test_mean = test_metrics_array.mean()
    test_std = test_metrics_array.std()
    test_min = test_metrics_array.min()
    test_max = test_metrics_array.max()

    # Stability ratio (higher is better)
    stability_ratio = test_mean / test_std if test_std > 0 else 0.0

    # Performance degradation from train to test (lower is better)
    train_mean = train_metrics_array.mean()
    if train_mean != 0:
        degradation = (train_mean - test_mean) / abs(train_mean)
    else:
        degradation = 0.0

    # Consistency (% of windows with positive test performance)
    consistency = np.mean(test_metrics_array > 0) * 100

    stability = {
        "test_mean": test_mean,
        "test_std": test_std,
        "test_min": test_min,
        "test_max": test_max,
        "stability_ratio": stability_ratio,
        "degradation": degradation,
        "consistency": consistency,
    }

    logger.success(
        f"Stability: mean={test_mean:.4f}, ratio={stability_ratio:.4f}, "
        f"degradation={degradation:.2%}"
    )

    return stability


# ============================================================================
# UTILITY FUNCTIONS
# ============================================================================


def print_statistical_validation_report(
    permutation_result: Optional[PermutationTestResult] = None,
    bootstrap_results: Optional[List[BootstrapResult]] = None,
    deflated_sharpe_result: Optional[Tuple[float, float]] = None,
    stability_result: Optional[Dict[str, float]] = None,
    whites_result: Optional[WhitesRealityCheckResult] = None,
) -> None:
    """
    Print comprehensive statistical validation report.

    Args:
        permutation_result: Permutation test result
        bootstrap_results: Bootstrap confidence intervals
        deflated_sharpe_result: (DSR, p-value) tuple
        stability_result: Walk-forward stability metrics
        whites_result: White's Reality Check result
    """
    print("\n" + "=" * 70)
    print("STATISTICAL VALIDATION REPORT")
    print("=" * 70)

    if permutation_result:
        print("\n" + "-" * 70)
        print("PERMUTATION TEST")
        print("-" * 70)
        print(f"  Metric: {permutation_result.metric_name}")
        print(f"  Observed Value:      {permutation_result.observed_value:>10.4f}")
        print(
            f"  Null Mean:           {permutation_result.null_distribution_mean:>10.4f}"
        )
        print(f"  P-value:             {permutation_result.p_value:>10.4f}")
        print(f"  Significance Level:  {permutation_result.significance_level:>10.4f}")
        print(
            f"  Result:              {'✓ Significant' if permutation_result.is_significant else '✗ Not Significant'}"
        )

    if bootstrap_results:
        print("\n" + "-" * 70)
        print("BOOTSTRAP CONFIDENCE INTERVALS")
        print("-" * 70)
        for br in bootstrap_results:
            print(f"\n  {br.metric_name}:")
            print(f"    Point Estimate:    {br.point_estimate:>10.4f}")
            print(f"    Bootstrap Mean:    {br.mean:>10.4f}")
            print(f"    Bootstrap Median:  {br.median:>10.4f}")
            print(f"    Bootstrap Std:     {br.std:>10.4f}")
            print(
                f"    {br.confidence_level*100:.0f}% CI:           [{br.ci_lower:>8.4f}, {br.ci_upper:>8.4f}]"
            )

    if deflated_sharpe_result:
        dsr, p_value = deflated_sharpe_result
        print("\n" + "-" * 70)
        print("DEFLATED SHARPE RATIO")
        print("-" * 70)
        print(f"  Deflated Sharpe:     {dsr:>10.4f}")
        print(f"  P-value (luck):      {p_value:>10.4f}")
        if p_value < 0.05:
            print("  Interpretation:      ✓ Significant (unlikely due to luck)")
        else:
            print("  Interpretation:      ✗ Not significant (may be luck)")

    if stability_result:
        print("\n" + "-" * 70)
        print("WALK-FORWARD STABILITY")
        print("-" * 70)
        print(f"  Test Mean:           {stability_result['test_mean']:>10.4f}")
        print(f"  Test Std:            {stability_result['test_std']:>10.4f}")
        print(f"  Test Min:            {stability_result['test_min']:>10.4f}")
        print(f"  Test Max:            {stability_result['test_max']:>10.4f}")
        print(f"  Stability Ratio:     {stability_result['stability_ratio']:>10.4f}")
        print(f"  Degradation:         {stability_result['degradation']:>10.2%}")
        print(f"  Consistency:         {stability_result['consistency']:>10.1f}%")

    if whites_result:
        print("\n" + "-" * 70)
        print("WHITE'S REALITY CHECK")
        print("-" * 70)
        print(f"  Best Strategy:       {whites_result.best_strategy_name}")
        print(f"  Best Performance:    {whites_result.best_performance:>10.4f}")
        print(f"  Strategies Tested:   {whites_result.n_strategies:>10}")
        print(f"  P-value:             {whites_result.p_value:>10.4f}")
        print(
            f"  Result:              {'✓ Significant' if whites_result.is_significant else '✗ Likely Overfit'}"
        )

    print("\n" + "=" * 70 + "\n")

