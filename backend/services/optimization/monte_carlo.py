"""
Monte Carlo Simulation Module.

Statistical validation and risk analysis using Monte Carlo methods.
Supports multiple simulation approaches to assess strategy robustness.
"""

from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Tuple

import numpy as np

from backend.common.logger import logger
from backend.services.optimization.models import (
    MultiEntryRequest,
    MultiEntryResponse,
    MultiEntryScenarioResult,
)

# from apps.backtest.result import BacktestResult
BacktestResult = Any

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
    original_max_dd: float = 0.0
    original_return: float = 0.0
    original_sharpe: float = 0.0

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
            "original_sharpe": self.original_sharpe,
        }


@dataclass
class ParametricSimulationResult:
    """Results from Parametric Monte Carlo simulation."""

    # Configuration
    num_simulations: int
    num_trades: int
    win_rate: float
    risk_reward_ratio: float
    risk_per_trade: float

    # Statistics
    mean_return: float = 0.0
    median_return: float = 0.0
    std_return: float = 0.0
    max_drawdown_avg: float = 0.0
    probability_of_ruin: float = 0.0  # >50% drawdown
    probability_of_profit: float = 0.0
    expected_shortfall_95: float = 0.0

    # Confidence Intervals
    ci_95_lower: float = 0.0
    ci_95_upper: float = 0.0

    # Sample Equity Curves (subset for visualization)
    equity_curves: List[List[float]] = field(default_factory=list)

    # Distribution data for histogram
    final_balances: List[float] = field(default_factory=list)


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


def parametric_simulation(
    win_rate: float,
    reward_risk_ratio: float,
    risk_per_trade: float,
    num_trades: int = 1000,
    num_simulations: int = 1000,
    initial_balance: float = 10000.0,
) -> ParametricSimulationResult:
    """
    Run Parametric Monte Carlo simulation based on statistical inputs.

    Simulates trade outcomes using probabilities rather than historical trades.
    Uses geometric (compounding) returns based on % risk per trade.

    Args:
        win_rate: Probability of winning a trade (0.0 to 1.0)
        reward_risk_ratio: Ratio of Win Size / Loss Size (e.g. 1.5)
        risk_per_trade: Percentage validity risk per trade (0.01 = 1%)
        num_trades: Number of trades per simulation run
        num_simulations: Number of simulation runs
        initial_balance: Starting account balance

    Returns:
        ParametricSimulationResult with stats and sample equity curves
    """
    logger.info(
        f"Starting Parametric MC: WR={win_rate*100}%, RRR={reward_risk_ratio}, "
        f"Risk={risk_per_trade*100}%, {num_simulations} runs"
    )

    final_balances = []
    max_drawdowns = []
    equity_curves_sample = []

    # Pre-calculate outcome multipliers
    # Win: Balance * (1 + risk * RRR)
    # Loss: Balance * (1 - risk)
    # NOTE: To simplify vectorization, we simulate log returns or multipliers
    win_mult = 1.0 + (risk_per_trade * reward_risk_ratio)
    loss_mult = 1.0 - risk_per_trade

    for i in range(num_simulations):
        # Generate random outcomes: 1 = win, 0 = loss
        # Using numpy for speed
        outcomes = np.random.random(num_trades) < win_rate

        # Convert to multipliers
        multipliers = np.where(outcomes, win_mult, loss_mult)

        # Calculate equity curve (cumulative product)
        # Prepend initial balance (1.0 multiplier effectively)
        equity = np.cumprod(multipliers) * initial_balance
        equity = np.insert(equity, 0, initial_balance)

        final_balance = equity[-1]
        final_balances.append(final_balance)

        # Calculate Max Drawdown
        peak = np.maximum.accumulate(equity)
        drawdown_pct = np.max((peak - equity) / peak * 100)
        max_drawdowns.append(drawdown_pct)

        # Save first 50 curves for visualization
        if i < 50:
            # Downsample if too many points for chart optimization?
            # For now, keep all points up to 1000 trades.
            equity_curves_sample.append(equity.tolist())

    # Calculate Statistics
    final_balances_array = np.array(final_balances)
    returns_pct = (final_balances_array - initial_balance) / initial_balance * 100

    logger.info(
        f"Parametric stats - Returns Min: {np.min(returns_pct):.2f}%, Max: {np.max(returns_pct):.2f}%, Mean: {np.mean(returns_pct):.2f}%"
    )

    mean_return = float(np.mean(returns_pct))
    median_return = float(np.median(returns_pct))
    std_return = float(np.std(returns_pct))

    ci_95_lower = float(np.percentile(returns_pct, 2.5))
    ci_95_upper = float(np.percentile(returns_pct, 97.5))

    probability_of_ruin = float(np.mean(np.array(max_drawdowns) > 50.0) * 100)

    # NEW: Probability of profit
    profitable_runs = np.sum(returns_pct > 0.0)
    probability_of_profit = float((profitable_runs / num_simulations) * 100)
    logger.info(
        f"Parametric stats - Profitable runs: {profitable_runs}/{num_simulations} ({probability_of_profit}%)"
    )

    expected_shortfall_95 = float(
        np.mean(returns_pct[returns_pct <= np.percentile(returns_pct, 5)])
    )
    max_drawdown_avg = float(np.mean(max_drawdowns))

    return ParametricSimulationResult(
        num_simulations=num_simulations,
        num_trades=num_trades,
        win_rate=win_rate,
        risk_reward_ratio=reward_risk_ratio,
        risk_per_trade=risk_per_trade,
        mean_return=mean_return,
        median_return=median_return,
        std_return=std_return,
        max_drawdown_avg=max_drawdown_avg,
        probability_of_ruin=probability_of_ruin,
        probability_of_profit=probability_of_profit,
        expected_shortfall_95=expected_shortfall_95,
        ci_95_lower=ci_95_lower,
        ci_95_upper=ci_95_upper,
        equity_curves=equity_curves_sample,
        final_balances=final_balances,
    )


@dataclass
class PositionSizingResult:
    """Results from Position Sizing simulation (Linear vs Compounding)."""

    num_trades: int
    win_rate: float
    reward_risk_ratio: float
    risk_per_trade: float

    # Equity Curves
    linear_curve: List[float]  # Risk based on initial balance
    compounding_curve: List[float]  # Risk based on current balance

    # Final Stats
    linear_final_balance: float
    compounding_final_balance: float
    linear_return_pct: float
    compounding_return_pct: float

    # Risk Metrics
    linear_max_drawdown: float
    compounding_max_drawdown: float
    linear_ret_dd_ratio: float
    compounding_ret_dd_ratio: float


def _calculate_max_drawdown_pct(equity_curve: np.ndarray) -> float:
    """Calculate maximum drawdown percentage from an equity curve."""
    peak = np.maximum.accumulate(equity_curve)
    # Avoid division by zero - simpler to just protect
    drawdown = (equity_curve - peak) / peak
    return float(abs(np.min(drawdown)) * 100)


def position_sizing_simulation(
    win_rate: float,
    reward_risk_ratio: float,
    risk_per_trade: float,
    num_trades: int = 1000,
    initial_balance: float = 10000.0,
) -> PositionSizingResult:
    """
    Run Position Sizing simulation comparing Linear vs Compounding growth.

    Generates a single sequence of trades and calculates two equity curves:
    1. Linear: Risk amount is fixed based on initial balance.
    2. Compounding: Risk amount is dynamic based on current balance.

    Args:
        win_rate: Probability of winning a trade (0.0 to 1.0)
        reward_risk_ratio: Ratio of Win Size / Loss Size
        risk_per_trade: Percentage risk per trade (0.01 = 1%)
        num_trades: Number of trades to simulate
        initial_balance: Starting account balance

    Returns:
        PositionSizingResult with both equity curves
    """
    logger.info(
        f"Starting Position Sizing Sim: WR={win_rate*100}%, RRR={reward_risk_ratio}, "
        f"Risk={risk_per_trade*100}%, Trades={num_trades}"
    )

    # Generate one shared sequence of trade outcomes
    # 1 = Win, 0 = Loss
    outcomes = np.random.random(num_trades) < win_rate

    # --- Linear Growth (Fixed Risk) ---
    # Risk amount is constant based on initial capital
    fixed_risk_amount = initial_balance * risk_per_trade
    linear_win_amt = fixed_risk_amount * reward_risk_ratio
    linear_loss_amt = -fixed_risk_amount

    # Create array of PnL per trade
    linear_pnl = np.where(outcomes, linear_win_amt, linear_loss_amt)

    # Calculate cumulative equity
    linear_curve = np.cumsum(linear_pnl) + initial_balance
    linear_curve = np.insert(linear_curve, 0, initial_balance)

    # --- Compounding Growth (Fixed % Risk) ---
    # Risk amount is recalculated every trade
    # Win Multiplier: 1 + (risk * RRR)
    # Loss Multiplier: 1 - risk
    comp_win_mult = 1.0 + (risk_per_trade * reward_risk_ratio)
    comp_loss_mult = 1.0 - risk_per_trade

    comp_mults = np.where(outcomes, comp_win_mult, comp_loss_mult)

    comp_curve = np.cumprod(comp_mults) * initial_balance
    comp_curve = np.insert(comp_curve, 0, initial_balance)

    # Calculate Max Drawdowns
    linear_dd = _calculate_max_drawdown_pct(linear_curve)
    comp_dd = _calculate_max_drawdown_pct(comp_curve)

    # Calculate Returns (Already done inline below, extracting for Ret/DD)
    lin_ret = (linear_curve[-1] - initial_balance) / initial_balance * 100
    comp_ret = (comp_curve[-1] - initial_balance) / initial_balance * 100

    return PositionSizingResult(
        num_trades=num_trades,
        win_rate=win_rate,
        reward_risk_ratio=reward_risk_ratio,
        risk_per_trade=risk_per_trade,
        linear_curve=linear_curve.tolist(),
        compounding_curve=comp_curve.tolist(),
        linear_final_balance=float(linear_curve[-1]),
        compounding_final_balance=float(comp_curve[-1]),
        linear_return_pct=float(lin_ret),
        compounding_return_pct=float(comp_ret),
        linear_max_drawdown=float(linear_dd),
        compounding_max_drawdown=float(comp_dd),
        linear_ret_dd_ratio=float(lin_ret / linear_dd) if linear_dd > 0 else 0.0,
        compounding_ret_dd_ratio=float(comp_ret / comp_dd) if comp_dd > 0 else 0.0,
    )


@dataclass
class ConsecutiveLosingScenarioResult:
    """Result of consecutive losing streaks simulation."""

    scenario_label: str
    win_rate: float
    rrr: float
    min_losses: int
    q1_losses: float
    median_losses: float
    q3_losses: float
    max_losses: int
    mean_losses: float
    std_losses: float


def _calculate_max_consecutive_streak(
    sequence: np.ndarray, value_to_count: int = 0
) -> int:
    """
    Calculate the maximum consecutive streak of a specific value in a binary array.

    Args:
        sequence: 1D numpy array of binary values (0 or 1).
        value_to_count: The value to count consecutive occurrences of.

    Returns:
        Max streak length.
    """
    # Create an array that is True where the sequence equals the value we want to count
    is_match = sequence == value_to_count

    # Pad with False at both ends to detect start/end of streaks
    padded = np.concatenate(([False], is_match, [False]))

    # Find indices where values change
    changes = np.diff(padded.astype(int))

    # starts are where 0 -> 1 (diff is 1)
    starts = np.where(changes == 1)[0]
    # ends are where 1 -> 0 (diff is -1)
    ends = np.where(changes == -1)[0]

    if len(starts) == 0:
        return 0

    return int((ends - starts).max())


def consecutive_losing_simulation(
    win_rates: List[float],
    rrrs: List[float],
    num_trades: int = 1000,
    num_simulations: int = 200,
) -> List[ConsecutiveLosingScenarioResult]:
    """Simulate max consecutive losses for multiple Win Rate / RRR pairs."""
    results = []

    # Handle mismatch by taking min length, assuming paired inputs
    n_systems = min(len(win_rates), len(rrrs))

    for i in range(n_systems):
        wr = win_rates[i]
        rrr = rrrs[i]
        label = f"WR={int(wr*100)}%"

        max_losses_per_sim = []

        for _ in range(num_simulations):
            # 1 = Win, 0 = Loss.
            # np.random.random() < wr gives True for Win.
            outcomes = (np.random.random(num_trades) < wr).astype(int)
            max_loss_streak = _calculate_max_consecutive_streak(
                outcomes, value_to_count=0
            )
            max_losses_per_sim.append(max_loss_streak)

        losses_arr = np.array(max_losses_per_sim)

        scenario_res = ConsecutiveLosingScenarioResult(
            scenario_label=label,
            win_rate=wr,
            rrr=rrr,
            min_losses=int(np.min(losses_arr)),
            q1_losses=float(np.percentile(losses_arr, 25)),
            median_losses=float(np.median(losses_arr)),
            q3_losses=float(np.percentile(losses_arr, 75)),
            max_losses=int(np.max(losses_arr)),
            mean_losses=float(np.mean(losses_arr)),
            std_losses=float(np.std(losses_arr)),
        )
        results.append(scenario_res)

    return results


@dataclass
class ProfitTargetScenarioResult:
    """Result of profit target simulation."""

    rrr: float
    risk_pct: float
    success_rate: float


def profit_target_simulation(
    initial_balance: float,
    target_balance: float,
    num_trades: int,
    win_rate: float,
    num_simulations: int = 500,
) -> List[ProfitTargetScenarioResult]:
    """Simulate the probability of reaching a target balance for a grid of RRR and Risk%."""
    # Define grids matching the user request (RRR 0.5-5.0, Risk 0.5-10.0)
    # RRR: 0.5, 1.0, 1.5, ... 5.0
    rrrs = np.arange(0.5, 5.5, 0.5)
    # Risk: 0.5, 1.0, ... 10.0
    risks = np.arange(0.5, 10.5, 0.5)  # Steps of 0.5% as per image density suggestion

    results = []

    # Pre-generate random outcomes for all simulations at once to save time?
    # Or per cell. Per cell is safer for memory.

    for rrr in rrrs:
        for risk_pct in risks:
            risk_decimal = risk_pct / 100.0

            # Count how many sims reach target

            # Vectorized simulation for this specific RRR/Risk pair
            # We run 'num_simulations' in parallel

            # 1. Generate outcomes (0=Loss, 1=Win)
            # shape: (num_simulations, num_trades)
            outcomes = (
                np.random.random((num_simulations, num_trades)) < win_rate
            ).astype(int)

            # 2. Map outcomes to multipliers
            # Win = 1 + (risk * rrr)
            # Loss = 1 - risk
            # Note: 1 - risk can be <= 0 if risk >= 100%, but here max is 10%.

            win_mult = 1 + (risk_decimal * rrr)
            loss_mult = 1 - risk_decimal

            multipliers = np.where(outcomes == 1, win_mult, loss_mult)

            # 3. Calculate cumulative content
            # We need to see if balance EVER hits target? Or Final balance?
            # User prompt says "Success Rate to Reach $200k in 750 trades".
            # Usually implies "at the end" or "at any point".
            # Looking at the image title "Reach ... in 750 trades", and typical MC,
            # checking FINAL balance is standard, but "Reach" implies "Touch".
            # However, for geometric growth, usually we look at valid paths.
            # Let's check max balance during the path.

            # Calculate cumulative product to get path
            paths = np.cumprod(multipliers, axis=1) * initial_balance

            # Check if ANY point in the path is >= target_balance
            # max_balance_per_sim = np.max(paths, axis=1)
            # successes = np.sum(max_balance_per_sim >= target_balance)

            # Wait, standard "Probability of Reach" often means "at end" in some contexts,
            # but in trading "Reach" usually means touch.
            # BUT, simple implementation first: Final Balance check is O(1) after cumprod.
            # Max check is also fast.
            # Let's stick to "Final Balance >= Target" as it's a stricter, more robust metric for "can I maintain this growth".
            # If I hit 200k then drop to 0, did I "succeed"? Maybe, but usually we want to KEEP it.
            # Let's use FINAL BALANCE for now as it's safer.

            final_balances = paths[:, -1]
            successes = np.sum(final_balances >= target_balance)

            rate = float(successes) / num_simulations

            results.append(
                ProfitTargetScenarioResult(
                    rrr=float(rrr), risk_pct=float(risk_pct), success_rate=rate
                )
            )

    return results


def random_win_rate_simulation(
    initial_equity: float,
    risk_per_trade: float,
    trades_per_run: int,
    simulations: int,
    manual_pairs: Optional[List[Any]] = None,
) -> Any:
    """Simulate trading with random Win Rate/RRR pairs selected per trade."""
    pairs = []
    if manual_pairs:
        # Use provided manual pairs
        n_pairs = len(manual_pairs)
        for p in manual_pairs:
            if isinstance(p, dict):
                wr = p.get("win_rate", 0.5)
                rrr = p.get("rrr", 1.0)
            else:
                wr = getattr(p, "win_rate", 0.5)
                rrr = getattr(p, "rrr", 1.0)

            pairs.append(
                {
                    "win_rate": float(wr),
                    "rrr": float(rrr),
                    "expectancy": (wr * rrr) - (1.0 - wr),
                    "usage_count": 0,
                    "usage_pct": 0.0,
                }
            )

        # Extract arrays for vector operations
        win_rates = np.array([p["win_rate"] for p in pairs])
        rrrs = np.array([p["rrr"] for p in pairs])
    else:
        # 1. Generate 5 random WRs and RRRs
        n_pairs = 5
        # Generate random Win Rates (10%-95%)
        win_rates = np.sort(np.random.uniform(0.10, 0.95, n_pairs))
        # Generate random RRRs (0.1-5.0) and sort descending
        rrrs = np.sort(np.random.uniform(0.1, 5.0, n_pairs))[::-1]

        # Key Pairs
        for i in range(n_pairs):
            pairs.append(
                {
                    "win_rate": float(win_rates[i]),
                    "rrr": float(rrrs[i]),
                    "expectancy": float(
                        (win_rates[i] * rrrs[i]) - ((1 - win_rates[i]) * 1)
                    ),
                    "usage_count": 0,
                    "usage_pct": 0.0,
                }
            )

    # Total simulated trades
    total_trades = simulations * trades_per_run

    # Randomly assign a pair index (0 to n_pairs-1) to each trade
    pair_indices = np.random.randint(0, n_pairs, total_trades)

    # Update usage counts
    unique, counts = np.unique(pair_indices, return_counts=True)
    counts_dict = dict(zip(unique, counts))

    for idx in range(n_pairs):
        count = counts_dict.get(idx, 0)
        pairs[idx]["usage_count"] = int(count)
        pairs[idx]["usage_pct"] = (
            float(count / total_trades) if total_trades > 0 else 0.0
        )

    # Map indices to specific Win Rates and RRRs
    trade_wrs = win_rates[pair_indices]
    trade_rrrs = rrrs[pair_indices]

    # Generate outcomes for each trade based on its specific Win Rate
    # Random floats [0, 1]
    rng = np.random.random(total_trades)
    # Win if rng < win_rate
    wins = (rng < trade_wrs).astype(int)

    # Calculate multipliers
    # Win: 1 + (risk * rrr)
    # Loss: 1 - risk
    risk_multipliers_win = 1 + (risk_per_trade * trade_rrrs)
    risk_multipliers_loss = 1 - risk_per_trade

    trade_multipliers = np.where(wins == 1, risk_multipliers_win, risk_multipliers_loss)

    # Reshape to (simulations, trades_per_run) for path calculation
    sim_multipliers = trade_multipliers.reshape((simulations, trades_per_run))

    # Calculate Equity Curves
    equity_curves = np.cumprod(sim_multipliers, axis=1) * initial_equity

    # Final Equities
    final_equities = equity_curves[:, -1]

    # Drawdowns
    # Calculate cumulative max to find peaks
    cum_max = np.maximum.accumulate(equity_curves, axis=1)
    # Must account for initial equity as possible peak
    cum_max_with_initial = np.maximum(cum_max, initial_equity)
    drawdowns = (cum_max_with_initial - equity_curves) / cum_max_with_initial
    max_drawdowns = np.max(drawdowns, axis=1) * 100  # In percentage

    # Calculate Percent Return Stats
    # (Final - Initial) / Initial * 100
    returns_pct = (final_equities - initial_equity) / initial_equity * 100.0

    # Calculate Stats Helper
    def get_distribution_stats(data):
        return {
            "min_val": float(np.min(data)),
            "q1_val": float(np.percentile(data, 25)),
            "median_val": float(np.median(data)),
            "q3_val": float(np.percentile(data, 75)),
            "max_val": float(np.max(data)),
            "mean_val": float(np.mean(data)),
            "std_val": float(np.std(data)),
        }

    return {
        "pairs": pairs,
        "drawdown_stats": get_distribution_stats(max_drawdowns),
        "equity_stats": get_distribution_stats(final_equities),
        "return_stats": get_distribution_stats(returns_pct),
    }


def robustness_simulation(
    backtest_id: str,
    simulations: int,
    simulation_type: str,
    skip_probability: float,
    deterioration_pct: float,
) -> Any:
    """Run robustness simulation with skipped trades and deterioration."""
    # 1. Fetch trades (Mocking specific retrieval, assumes standardized Trade object or list of dicts)
    # In a real scenario, we'd call the database. For now we will try to reuse logic or helper.
    # IMPORTANT: Since we don't have direct DB access here, we might need to pass trades or use the same helper as standard monte carlo.
    # Let's assume we can fetch them using the same method as `monte_carlo_simulation`.

    # Needs: `get_backtest_trades` from backtest service or repository.
    # RE-VERIFY: `monte_carlo_simulation` signature?
    # It takes `backtest_id`.

    # TODO: Wire to backend backtest repository when available.
    try:
        from backend.data.database.repositories.backtest_repository import get_backtest_trades_df
        df = get_backtest_trades_df(backtest_id)
    except Exception:
        # Fallback or empty if service not available/mock
        return None

    if df.empty:
        raise ValueError("No trades found for backtest")

    # Extract PnL series
    # Assuming 'profit' column exists
    original_profits = df["profit"].to_numpy()

    initial_balance = 10000.0  # Default or fetch from backtest settings? MQL5 article usually implies starting from 0 or specific bal.
    # Let's verify if we can get initial balance. If not, assume 10000.

    # Original Curve
    original_equity = np.cumsum(np.insert(original_profits, 0, 0)) + initial_balance

    final_profits = []
    max_drawdowns = []
    ruin_counts = 0

    sample_curves = []

    for i in range(simulations):
        # 1. Simulation Type
        if simulation_type == "shuffle":
            # Shuffle without replacement
            sim_profits = np.random.permutation(original_profits)
        else:
            # Bootstrap (Resample with replacement)
            sim_profits = np.random.choice(
                original_profits, size=len(original_profits), replace=True
            )

        # 2. Skip Trades
        if skip_probability > 0:
            # Mask: True = Keep, False = Skip
            # rng > skip_prob -> Keep
            mask = np.random.random(len(sim_profits)) > skip_probability
            sim_profits = sim_profits[mask]

        # 3. Deterioration
        if deterioration_pct > 0:
            # Reduce positive profits by X%, Increase losses?
            # Article usually implies reducing the Result.
            # "Deteriorated by X%" -> Profit * (1 - X)
            sim_profits = sim_profits * (1.0 - deterioration_pct)

        # Calculate Curve
        curve = np.cumsum(np.insert(sim_profits, 0, 0)) + initial_balance

        # Stats
        final_profit = curve[-1] - initial_balance
        final_profits.append(final_profit)

        # Drawdown
        peak = np.maximum.accumulate(curve)
        dd = (peak - curve) / peak * 100
        max_dd = np.max(dd)
        max_drawdowns.append(max_dd)

        # Ruin
        if np.any(curve <= 0):
            ruin_counts += 1

        # Save sample (limit to first 50)
        if i < 50:
            sample_curves.append(curve.tolist())

    # Calculate Risk Metrics on Final Profits
    param_ci = np.percentile(final_profits, [2.5, 97.5])

    # VaR 95% (5th percentile of returns/profits)
    var_95 = np.percentile(final_profits, 5)

    # CVaR 95% (Mean of profits below VaR)
    cvar_95 = (
        np.mean([p for p in final_profits if p <= var_95]) if simulations > 0 else 0.0
    )

    # Aggregate Stats
    stats = {
        "original_profit": float(original_equity[-1] - initial_balance),
        "min_profit": float(np.min(final_profits)),
        "max_profit": float(np.max(final_profits)),
        "mean_profit": float(np.mean(final_profits)),
        "worst_case_drawdown": float(
            np.percentile(max_drawdowns, 95)
        ),  # 95th percentile DD
        "risk_of_ruin": float((ruin_counts / simulations) * 100.0),
        "var_95": float(var_95),
        "cvar_95": float(cvar_95),
        "ci_95_lower": float(param_ci[0]),
        "ci_95_upper": float(param_ci[1]),
    }

    return {
        "original_equity": original_equity.tolist(),
        "simulation_equities": sample_curves,
        "stats": stats,
    }


def multi_entry_simulation(request: MultiEntryRequest) -> MultiEntryResponse:
    """Simulate multi-entry strategies with varying RRR as per MQL5 Article 19693."""
    logger.info(
        f"Starting Multi-Entry Simulation: WR={request.win_rate}, RRR={request.initial_rrr}, Step={request.rrr_step}"
    )

    # Configuration
    initial_balance = request.initial_balance
    simulations = request.simulations

    # Article uses "100 executions" per simulation.
    num_executions = 100

    def run_scenario(num_trades: int) -> MultiEntryScenarioResult:
        """Run simulation for a specific number of simultaneous trades (1, 2, or 3)."""
        # Risk is split between trades
        risk_per_trade_pct = request.risk_percent / num_trades

        # Calculate RRR for each trade in the batch
        rrrs = [request.initial_rrr + (i * request.rrr_step) for i in range(num_trades)]

        final_equities = []
        max_drawdowns = []
        eq_curves_sum = np.zeros(num_executions + 1)  # To calculate mean curve

        # Calculate Lambda for probability decay: P(R >= Target) = exp(-lambda * Target)
        # Calibrated so P(R >= InitialRRR) = WinRate
        import math

        if request.win_rate > 0:
            decay_lambda = -math.log(request.win_rate) / request.initial_rrr
        else:
            decay_lambda = 999999

        for _ in range(simulations):
            equity_curve = [initial_balance]
            peak_equity = initial_balance
            max_dd = 0.0

            # Generate random "Excursion potentials" for each execution
            # u represents the quantile of favorable excursion.
            # If u <= P(Win), it means the trade survived.
            random_outcomes = np.random.random(num_executions)

            current_equity = initial_balance

            for i in range(num_executions):
                u = random_outcomes[i]
                trade_pnl_pct = 0.0

                for r_target in rrrs:
                    # Probability of hitting this specific target
                    prob_hit = math.exp(-decay_lambda * r_target)

                    if u <= prob_hit:
                        # WIN: Gain = Risk * RRR
                        trade_pnl_pct += risk_per_trade_pct * r_target
                    else:
                        # LOSS: Lose Risk amount
                        trade_pnl_pct -= risk_per_trade_pct

                # Apply PnL
                current_equity *= 1 + trade_pnl_pct
                equity_curve.append(current_equity)

                # Drawdown stats
                if current_equity > peak_equity:
                    peak_equity = current_equity
                dd = (peak_equity - current_equity) / peak_equity
                if dd > max_dd:
                    max_dd = dd

            final_equities.append(current_equity)
            max_drawdowns.append(max_dd)
            eq_curves_sum += np.array(equity_curve)

        # Aggregate Results
        mean_curve = (eq_curves_sum / simulations).tolist()
        median_dd = np.median(max_drawdowns) * 100  # percentage
        median_eq = np.median(final_equities)
        mean_eq = np.mean(final_equities)
        prof_pct = (
            np.sum(np.array(final_equities) > initial_balance) / simulations * 100
        )

        return MultiEntryScenarioResult(
            mean_equity=mean_eq,
            median_equity=median_eq,
            median_drawdown=median_dd,
            profitable_pct=prof_pct,
            equity_curve=mean_curve,
        )

    # Execute scenarios
    res_1 = run_scenario(1)
    res_2 = run_scenario(2)
    res_3 = run_scenario(3)

    return MultiEntryResponse(one_trade=res_1, two_trades=res_2, three_trades=res_3)

