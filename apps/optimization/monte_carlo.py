"""
Monte Carlo Simulation Module.

Statistical validation and risk analysis using Monte Carlo methods.
Supports multiple simulation approaches to assess strategy robustness.
"""

from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Tuple

import numpy as np

from apps.backtest.result import BacktestResult
from apps.logger import logger

# =========================================================================
# Data Models
# =========================================================================


@dataclass
class MonteCarloResult:
    """
    Results from Monte Carlo simulation.

    Contains distribution of outcomes across multiple simulation runs
    and statistical confidence intervals.
    """

    # Configuration
    simulation_type: str  # "shuffle_trades", "resample_returns", "bootstrap"
    num_simulations: int

    # Simulation results
    final_balances: List[float] = field(default_factory=list)
    total_returns: List[float] = field(default_factory=list)
    max_drawdowns: List[float] = field(default_factory=list)
    sharpe_ratios: List[float] = field(default_factory=list)
    win_rates: List[float] = field(default_factory=list)

    # Statistical measures
    mean_return: float = 0.0
    median_return: float = 0.0
    std_return: float = 0.0

    # Confidence intervals (95% by default)
    ci_95_lower: float = 0.0
    ci_95_upper: float = 0.0
    ci_99_lower: float = 0.0
    ci_99_upper: float = 0.0

    # Risk metrics
    probability_of_profit: float = 0.0  # % of runs with positive returns
    probability_of_ruin: float = 0.0  # % of runs with >50% drawdown
    expected_shortfall_95: float = 0.0  # Average of worst 5% outcomes

    # Percentiles
    percentile_5: float = 0.0
    percentile_25: float = 0.0
    percentile_50: float = 0.0
    percentile_75: float = 0.0
    percentile_95: float = 0.0

    # Original strategy results (for comparison)
    original_return: float = 0.0
    original_sharpe: float = 0.0
    original_max_dd: float = 0.0

    def calculate_statistics(self) -> None:
        """Calculate statistical measures from simulation results."""
        if not self.total_returns:
            return

        returns_array = np.array(self.total_returns)

        # Central tendency
        self.mean_return = float(np.mean(returns_array))
        self.median_return = float(np.median(returns_array))
        self.std_return = float(np.std(returns_array))

        # Confidence intervals
        self.ci_95_lower = float(np.percentile(returns_array, 2.5))
        self.ci_95_upper = float(np.percentile(returns_array, 97.5))
        self.ci_99_lower = float(np.percentile(returns_array, 0.5))
        self.ci_99_upper = float(np.percentile(returns_array, 99.5))

        # Percentiles
        self.percentile_5 = float(np.percentile(returns_array, 5))
        self.percentile_25 = float(np.percentile(returns_array, 25))
        self.percentile_50 = float(np.percentile(returns_array, 50))
        self.percentile_75 = float(np.percentile(returns_array, 75))
        self.percentile_95 = float(np.percentile(returns_array, 95))

        # Risk metrics
        self.probability_of_profit = float(np.mean(returns_array > 0) * 100)

        # Probability of ruin (>50% drawdown)
        if self.max_drawdowns:
            dd_array = np.array(self.max_drawdowns)
            self.probability_of_ruin = float(np.mean(dd_array > 50) * 100)

        # Expected shortfall (average of worst 5%)
        worst_5_pct = returns_array[returns_array <= self.percentile_5]
        if len(worst_5_pct) > 0:
            self.expected_shortfall_95 = float(np.mean(worst_5_pct))

    def get_summary(self) -> Dict[str, Any]:
        """
        Get summary statistics.

        Returns:
            Dict with key Monte Carlo statistics
        """
        return {
            "simulation_type": self.simulation_type,
            "num_simulations": self.num_simulations,
            "mean_return": self.mean_return,
            "median_return": self.median_return,
            "std_return": self.std_return,
            "ci_95_lower": self.ci_95_lower,
            "ci_95_upper": self.ci_95_upper,
            "probability_of_profit": self.probability_of_profit,
            "probability_of_ruin": self.probability_of_ruin,
            "expected_shortfall_95": self.expected_shortfall_95,
            "original_return": self.original_return,
        }


# =========================================================================
# Core Monte Carlo Functions
# =========================================================================


def monte_carlo_analysis(
    result: BacktestResult,
    num_simulations: int = 1000,
    simulation_type: str = "shuffle_trades",
    random_seed: Optional[int] = None,
    **kwargs,
) -> MonteCarloResult:
    """
    Run Monte Carlo analysis.

    Runs Monte Carlo simulation to assess strategy robustness and risk.

    Args:
        result: BacktestResult from original strategy run
        num_simulations: Number of Monte Carlo runs
        simulation_type: Type of simulation - "shuffle_trades", "resample_returns", or "bootstrap"
        random_seed: Random seed for reproducibility
        **kwargs: Additional parameters for specific simulation types

    Returns:
        MonteCarloResult with simulation statistics

    Raises:
        ValueError: If simulation_type is invalid
    """
    if random_seed is not None:
        np.random.seed(random_seed)

    logger.info(
        f"Starting Monte Carlo analysis: {simulation_type}, {num_simulations} simulations"
    )

    # Validate simulation type
    valid_types = ["shuffle_trades", "resample_returns", "bootstrap"]
    if simulation_type not in valid_types:
        raise ValueError(
            f"Invalid simulation_type: {simulation_type}. Valid: {valid_types}"
        )

    # Run appropriate simulation
    if simulation_type == "shuffle_trades":
        mc_result = shuffle_trades_simulation(result, num_simulations)
    elif simulation_type == "resample_returns":
        mc_result = resample_returns_simulation(result, num_simulations, **kwargs)
    elif simulation_type == "bootstrap":
        block_size = kwargs.get("block_size", 10)
        mc_result = bootstrap_simulation(result, num_simulations, block_size)

    # Calculate statistics
    mc_result.calculate_statistics()

    # Store original results for comparison
    mc_result.original_return = result.total_return_pct
    mc_result.original_sharpe = result.sharpe_ratio
    mc_result.original_max_dd = result.max_drawdown_pct

    logger.info(
        f"Monte Carlo complete: mean return={mc_result.mean_return:.2f}%, "
        f"95% CI=[{mc_result.ci_95_lower:.2f}%, {mc_result.ci_95_upper:.2f}%]"
    )

    return mc_result


def shuffle_trades_simulation(
    result: BacktestResult, num_simulations: int = 1000
) -> MonteCarloResult:
    """
    Randomize trade order to test strategy robustness.

    This simulation shuffles the order of trades while keeping their
    individual P&L values the same. It answers the question: "What if
    the same trades occurred in a different sequence?"

    Args:
        result: BacktestResult from original strategy run
        num_simulations: Number of shuffles to perform

    Returns:
        MonteCarloResult with shuffled trade outcomes
    """
    logger.debug(f"Running shuffle trades simulation: {num_simulations} runs")

    trades_df = result.get_trades_df()
    if trades_df.empty or len(trades_df) < 2:
        logger.warning("Insufficient trades for shuffle simulation")
        return MonteCarloResult(simulation_type="shuffle_trades", num_simulations=0)

    initial_balance = result.initial_balance
    trade_pnls = trades_df["profit_loss"].values

    mc_result = MonteCarloResult(
        simulation_type="shuffle_trades", num_simulations=num_simulations
    )

    for _i in range(num_simulations):
        # Shuffle trade order
        shuffled_pnls = np.random.permutation(trade_pnls)

        # Simulate equity curve
        equity_curve = [initial_balance]
        for pnl in shuffled_pnls:
            equity_curve.append(equity_curve[-1] + pnl)

        equity_array = np.array(equity_curve)

        # Calculate metrics
        final_balance = equity_curve[-1]
        total_return_pct = (final_balance - initial_balance) / initial_balance * 100

        # Calculate max drawdown
        peak = np.maximum.accumulate(equity_array)
        drawdown = (peak - equity_array) / peak * 100
        max_dd = np.max(drawdown)

        # Calculate Sharpe ratio
        returns = np.diff(equity_array) / equity_array[:-1]
        if len(returns) > 1 and returns.std() > 0:
            sharpe = (returns.mean() / returns.std()) * np.sqrt(252)
        else:
            sharpe = 0.0

        # Calculate win rate
        wins = np.sum(shuffled_pnls > 0)
        win_rate = wins / len(shuffled_pnls) * 100 if len(shuffled_pnls) > 0 else 0

        # Store results
        mc_result.final_balances.append(final_balance)
        mc_result.total_returns.append(total_return_pct)
        mc_result.max_drawdowns.append(max_dd)
        mc_result.sharpe_ratios.append(sharpe)
        mc_result.win_rates.append(win_rate)

    logger.debug(f"Shuffle simulation complete: {num_simulations} runs")

    return mc_result


def resample_returns_simulation(
    result: BacktestResult,
    num_simulations: int = 1000,
    num_trades: Optional[int] = None,
) -> MonteCarloResult:
    """
    Sample from return distribution with replacement.

    This simulation samples returns from the empirical distribution,
    allowing trades to be "repeated". It answers: "What if we continue
    trading with similar outcomes?"

    Args:
        result: BacktestResult from original strategy run
        num_simulations: Number of simulation runs
        num_trades: Number of trades per simulation (default: same as original)

    Returns:
        MonteCarloResult with resampled return outcomes
    """
    logger.debug(f"Running resample returns simulation: {num_simulations} runs")

    trades_df = result.get_trades_df()
    if trades_df.empty:
        logger.warning("No trades for resample simulation")
        return MonteCarloResult(simulation_type="resample_returns", num_simulations=0)

    initial_balance = result.initial_balance
    trade_pnls = trades_df["profit_loss"].values

    # Use same number of trades as original if not specified
    if num_trades is None:
        num_trades = len(trade_pnls)

    mc_result = MonteCarloResult(
        simulation_type="resample_returns", num_simulations=num_simulations
    )

    for _i in range(num_simulations):
        # Sample with replacement
        sampled_pnls = np.random.choice(trade_pnls, size=num_trades, replace=True)

        # Simulate equity curve
        equity_curve = [initial_balance]
        for pnl in sampled_pnls:
            equity_curve.append(equity_curve[-1] + pnl)

        equity_array = np.array(equity_curve)

        # Calculate metrics
        final_balance = equity_curve[-1]
        total_return_pct = (final_balance - initial_balance) / initial_balance * 100

        # Max drawdown
        peak = np.maximum.accumulate(equity_array)
        drawdown = (peak - equity_array) / peak * 100
        max_dd = np.max(drawdown)

        # Sharpe ratio
        returns = np.diff(equity_array) / equity_array[:-1]
        if len(returns) > 1 and returns.std() > 0:
            sharpe = (returns.mean() / returns.std()) * np.sqrt(252)
        else:
            sharpe = 0.0

        # Win rate
        wins = np.sum(sampled_pnls > 0)
        win_rate = wins / len(sampled_pnls) * 100 if len(sampled_pnls) > 0 else 0

        # Store results
        mc_result.final_balances.append(final_balance)
        mc_result.total_returns.append(total_return_pct)
        mc_result.max_drawdowns.append(max_dd)
        mc_result.sharpe_ratios.append(sharpe)
        mc_result.win_rates.append(win_rate)

    logger.debug(f"Resample simulation complete: {num_simulations} runs")

    return mc_result


def bootstrap_simulation(
    result: BacktestResult, num_simulations: int = 1000, block_size: int = 10
) -> MonteCarloResult:
    """
    Block bootstrap to preserve temporal structure.

    This simulation uses block bootstrap to maintain serial correlation
    in returns. Trades are sampled in blocks to preserve short-term
    patterns.

    Args:
        result: BacktestResult from original strategy run
        num_simulations: Number of bootstrap samples
        block_size: Size of blocks to sample

    Returns:
        MonteCarloResult with bootstrap outcomes
    """
    logger.debug(
        f"Running bootstrap simulation: {num_simulations} runs, block_size={block_size}"
    )

    trades_df = result.get_trades_df()
    if trades_df.empty or len(trades_df) < block_size:
        logger.warning(f"Insufficient trades for block bootstrap (need >={block_size})")
        return MonteCarloResult(simulation_type="bootstrap", num_simulations=0)

    initial_balance = result.initial_balance
    trade_pnls = trades_df["profit_loss"].values
    num_trades = len(trade_pnls)

    mc_result = MonteCarloResult(
        simulation_type="bootstrap", num_simulations=num_simulations
    )

    for _i in range(num_simulations):
        # Create bootstrap sample using blocks
        bootstrapped_pnls_list: List[float] = []

        while len(bootstrapped_pnls_list) < num_trades:
            # Randomly select a block start position
            start_idx = np.random.randint(0, max(1, num_trades - block_size + 1))
            end_idx = min(start_idx + block_size, num_trades)

            # Extract block
            block = trade_pnls[start_idx:end_idx]
            bootstrapped_pnls_list.extend(block)

        # Trim to original length
        bootstrapped_pnls = np.array(bootstrapped_pnls_list[:num_trades])

        # Simulate equity curve
        equity_curve = [initial_balance]
        for pnl in bootstrapped_pnls:
            equity_curve.append(equity_curve[-1] + pnl)

        equity_array = np.array(equity_curve)

        # Calculate metrics
        final_balance = equity_curve[-1]
        total_return_pct = (final_balance - initial_balance) / initial_balance * 100

        # Max drawdown
        peak = np.maximum.accumulate(equity_array)
        drawdown = (peak - equity_array) / peak * 100
        max_dd = np.max(drawdown)

        # Sharpe ratio
        returns = np.diff(equity_array) / equity_array[:-1]
        if len(returns) > 1 and returns.std() > 0:
            sharpe = (returns.mean() / returns.std()) * np.sqrt(252)
        else:
            sharpe = 0.0

        # Win rate
        wins = np.sum(bootstrapped_pnls > 0)
        win_rate = (
            wins / len(bootstrapped_pnls) * 100 if len(bootstrapped_pnls) > 0 else 0
        )

        # Store results
        mc_result.final_balances.append(final_balance)
        mc_result.total_returns.append(total_return_pct)
        mc_result.max_drawdowns.append(max_dd)
        mc_result.sharpe_ratios.append(sharpe)
        mc_result.win_rates.append(win_rate)

    logger.debug(f"Bootstrap simulation complete: {num_simulations} runs")

    return mc_result


def calculate_probability_of_ruin(
    result: BacktestResult,
    ruin_threshold_pct: float = 50.0,
    num_simulations: int = 10000,
    simulation_type: str = "resample_returns",
) -> float:
    """
    Calculate probability of ruin (catastrophic loss).

    Ruin is defined as drawdown exceeding the threshold percentage.

    Args:
        result: BacktestResult from original strategy run
        ruin_threshold_pct: Drawdown % that constitutes ruin (default 50%)
        num_simulations: Number of Monte Carlo runs
        simulation_type: Type of simulation to use

    Returns:
        Probability of ruin (0-100%)
    """
    logger.debug(f"Calculating probability of ruin: threshold={ruin_threshold_pct}%")

    mc_result = monte_carlo_analysis(
        result, num_simulations=num_simulations, simulation_type=simulation_type
    )

    if not mc_result.max_drawdowns:
        return 0.0

    # Count simulations where max DD exceeded threshold
    max_dds = np.array(mc_result.max_drawdowns)
    ruin_count = np.sum(max_dds > ruin_threshold_pct)
    probability = float((ruin_count / len(max_dds)) * 100)

    logger.info(f"Probability of ruin (>{ruin_threshold_pct}% DD): {probability:.2f}%")

    return probability


def calculate_confidence_intervals(
    result: BacktestResult,
    metric: str = "total_return_pct",
    confidence_levels: Optional[List[float]] = None,
    num_simulations: int = 1000,
    simulation_type: str = "shuffle_trades",
) -> Dict[float, Tuple[float, float]]:
    """
    Calculate confidence intervals for a specific metric.

    Args:
        result: BacktestResult from original strategy run
        metric: Metric to calculate CI for ("total_return_pct", "sharpe_ratio", "max_drawdown_pct")
        confidence_levels: List of confidence levels (e.g., [90, 95, 99])
        num_simulations: Number of Monte Carlo runs
        simulation_type: Type of simulation to use

    Returns:
        Dict mapping confidence level to (lower, upper) bounds
    """
    logger.debug(f"Calculating confidence intervals for {metric}")

    if confidence_levels is None:
        confidence_levels = [90, 95, 99]

    mc_result = monte_carlo_analysis(
        result, num_simulations=num_simulations, simulation_type=simulation_type
    )

    # Select appropriate data
    if metric == "total_return_pct":
        data = mc_result.total_returns
    elif metric == "sharpe_ratio":
        data = mc_result.sharpe_ratios
    elif metric == "max_drawdown_pct":
        data = mc_result.max_drawdowns
    else:
        raise ValueError(f"Unknown metric: {metric}")

    if not data:
        return {}

    data_array = np.array(data)
    confidence_intervals = {}

    for level in confidence_levels:
        # Calculate percentiles for CI
        lower_pct = (100 - level) / 2
        upper_pct = 100 - lower_pct

        lower = float(np.percentile(data_array, lower_pct))
        upper = float(np.percentile(data_array, upper_pct))

        confidence_intervals[level] = (lower, upper)

        logger.debug(f"{level}% CI for {metric}: [{lower:.2f}, {upper:.2f}]")

    return confidence_intervals


# =========================================================================
# Helper Functions
# =========================================================================


def compare_simulation_methods(
    result: BacktestResult, num_simulations: int = 1000
) -> Dict[str, MonteCarloResult]:
    """
    Run all three simulation methods and return results.

    Useful for comparing different Monte Carlo approaches.

    Args:
        result: BacktestResult from original strategy run
        num_simulations: Number of simulations per method

    Returns:
        Dict mapping method name to MonteCarloResult
    """
    logger.info(f"Comparing simulation methods: {num_simulations} runs each")

    results = {
        "shuffle_trades": monte_carlo_analysis(
            result, num_simulations, simulation_type="shuffle_trades"
        ),
        "resample_returns": monte_carlo_analysis(
            result, num_simulations, simulation_type="resample_returns"
        ),
        "bootstrap": monte_carlo_analysis(
            result, num_simulations, simulation_type="bootstrap", block_size=10
        ),
    }

    logger.info("Simulation comparison complete")

    return results


def assess_strategy_robustness(result: BacktestResult) -> Dict[str, Any]:
    """
    Comprehensive robustness assessment using Monte Carlo.

    Args:
        result: BacktestResult from original strategy run

    Returns:
        Dict with robustness metrics
    """
    logger.info("Assessing strategy robustness")

    # Run Monte Carlo
    mc_result = monte_carlo_analysis(
        result, num_simulations=5000, simulation_type="shuffle_trades"
    )

    # Calculate probability of ruin
    prob_ruin = calculate_probability_of_ruin(
        result, ruin_threshold_pct=50.0, num_simulations=5000
    )

    # Check if original result is statistically significant
    # Original should be within 95% CI to be "normal"
    is_outlier = (
        result.total_return_pct < mc_result.ci_95_lower
        or result.total_return_pct > mc_result.ci_95_upper
    )

    # Consistency score: lower std deviation relative to mean is more consistent
    consistency_score = 0.0
    if mc_result.mean_return != 0:
        consistency_score = abs(mc_result.mean_return / mc_result.std_return)

    robustness = {
        "mean_return": mc_result.mean_return,
        "std_return": mc_result.std_return,
        "probability_of_profit": mc_result.probability_of_profit,
        "probability_of_ruin": prob_ruin,
        "ci_95_lower": mc_result.ci_95_lower,
        "ci_95_upper": mc_result.ci_95_upper,
        "is_outlier": is_outlier,
        "consistency_score": consistency_score,
        "assessment": _get_robustness_rating(mc_result, prob_ruin, is_outlier),
    }

    logger.info(f"Robustness assessment: {robustness['assessment']}")

    return robustness


def _get_robustness_rating(
    mc_result: MonteCarloResult, prob_ruin: float, is_outlier: bool
) -> str:
    """Get qualitative robustness rating."""
    if is_outlier:
        return "Poor - Original result is statistical outlier"

    if prob_ruin > 20:
        return "Poor - High probability of ruin"

    if mc_result.probability_of_profit < 60:
        return "Weak - Low probability of profit"

    if prob_ruin < 5 and mc_result.probability_of_profit > 80:
        return "Excellent - Highly robust"

    if prob_ruin < 10 and mc_result.probability_of_profit > 70:
        return "Good - Reasonably robust"

    return "Fair - Moderate robustness"
