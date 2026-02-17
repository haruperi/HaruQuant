"""Comprehensive examples for backtest statistics module.

This script demonstrates:
1. Basic return metrics (total return, CAGR, Sharpe, Sortino)
2. Drawdown analysis (max drawdown, duration, Calmar ratio)
3. Risk metrics (volatility, VaR, CVaR, skew, kurtosis)
4. Trade-based metrics (win rate, expectancy, SQN, Kelly criterion)
5. Exposure and efficiency metrics
6. Advanced metrics (CPC Index, Common Sense Ratio, Risk of Ruin)
7. Benchmark comparison (alpha, beta, information ratio)
8. Period-based analysis (monthly/yearly returns)
9. Full compute_stats() usage
10. Visualization examples

Updated to use real market data.
"""

from __future__ import annotations

import os
import sys
from pathlib import Path
from typing import Optional

import numpy as np
import pandas as pd

project_root = Path(__file__).resolve().parents[4]
sys.path.insert(0, str(project_root))

from apps.simulation.simulator import TradeSimulator
from apps.simulation.data import AccountInfoSimulator, SymbolInfoSimulator
from apps.simulation.utils import calculate_metrics_from_simulator  # noqa: E402
from apps.finance import (  # noqa: E402
    benchmark,
    distributions,
    drawdowns,
    efficiency,
    metrics,
    ratios,
    returns,
    risks,
)
from apps.indicator import sma  # noqa: E402
from apps.utils.logger import logger  # noqa: E402
from apps.strategy import BaseStrategy  # noqa: E402
from apps.utils.data_getters import load_mt5  # noqa: E402

try:  # Optional plotting deps
    import matplotlib.pyplot as plt  # noqa: E402
except Exception:  # pragma: no cover - optional dependency
    plt = None

try:  # Optional plotting deps
    import seaborn as sns  # noqa: E402
except Exception:  # pragma: no cover - optional dependency
    sns = None


def load_market_data(
    symbol: str,
    start_date: str,
    end_date: str,
    timeframe: str = "D1",
) -> pd.DataFrame:
    """Load real market data using MT5 (with Dukascopy fallback)."""
    data = load_mt5(
        symbol,
        timeframe=timeframe,
        start_date=start_date,
        end_date=end_date,
    )
    if data is None or data.empty:
        raise ValueError(f"No data returned for {symbol}")
    return data


class MAStrategy(BaseStrategy):
    """Simple moving-average cross strategy for examples."""

    def __init__(self, params: Optional[dict] = None) -> None:
        super().__init__(params)
        self.fast_window = self.params.get("fast_window", 20)
        self.slow_window = self.params.get("slow_window", 50)

    def on_init(self) -> None:
        logger.info("MA strategy initialized")

    def on_bar(self, data: pd.DataFrame) -> pd.DataFrame:
        result = sma(data, window=self.fast_window)
        result = sma(result, window=self.slow_window)

        fast_col = f"sma_{self.fast_window}"
        slow_col = f"sma_{self.slow_window}"

        result["entry_signal"] = 0
        result["exit_signal"] = 0
        result["pending_signal"] = 0
        result["cancel_pending_signal"] = 0
        result["price"] = float("nan")

        buy = result[fast_col] > result[slow_col]
        sell = result[fast_col] < result[slow_col]

        result.loc[buy, "entry_signal"] = 1
        result.loc[buy, "price"] = result.loc[buy, "open"]
        result.loc[sell, "exit_signal"] = 1


        # Cleanup


        mt5_client.shutdown()


        


        return result


def run_backtest(
    symbol: str,
    start_date: str,
    end_date: str,
    timeframe: str = "D1",
) -> tuple[pd.DataFrame, pd.Series, pd.Series, pd.DataFrame, object]:
    """Run a simple backtest and return data, equity, returns, trades."""
    data = load_market_data(symbol, start_date, end_date, timeframe=timeframe)

    strategy = MAStrategy(params={"symbol": symbol})
    # Initialize strategy
    strategy.on_init()

    # Calculate signals
    data = strategy.on_bar(data)

    # Get MT5 client for symbol info
    mt5_client = get_mt5_client()

    # Setup simulator components
    account_info = AccountInfoSimulator(
        balance=10000.0,
        equity=10000.0,
        margin_free=10000.0,
    )
    symbol_info = SymbolInfoSimulator.from_mt5_symbol('EURUSD')
    symbol_info.symbol = 'EURUSD'

    # Create simulator
    simulator = TradeSimulator(
        simulator_name="Backtest_EURUSD",
        mt5_client=mt5_client,
        account_info=account_info,
        symbols={'EURUSD': symbol_info},
    )

    # Run simulation
    simulator.run(
        data=data,
        strategy=strategy,
        symbol='EURUSD',
        volume=0.1,
        verbose=False,
        save_db=False,
        engine_type="event_driven",
        commission_per_contract=0.0002,
        slippage_points=0,
        start_date=backtest_start,
        end_date=backtest_end,
    )

    # Get results from simulator
    result = calculate_metrics_from_simulator(simulator)

    equity_df = result.get_equity_df()
    equity = pd.Series(
        equity_df["equity"].values, index=pd.to_datetime(equity_df["timestamp"])
    )
    rets = returns.returns_series(equity)
    trades = result.get_trades_df()

    return data, equity, rets, trades, result


def calc_kelly_fraction(trades: pd.DataFrame) -> float:
    """Kelly fraction using win rate and payoff ratio."""
    if len(trades) == 0:
        return 0.0

    win_pct = metrics.win_rate(trades) / 100.0
    loss_pct = 1.0 - win_pct
    avg_win = metrics.avg_win(trades)
    avg_loss = abs(metrics.avg_loss(trades))

    if avg_loss == 0:
        return 0.0

    payoff = avg_win / avg_loss
    if payoff == 0:
        return 0.0

    kelly = win_pct - (loss_pct / payoff)
    return float(max(kelly, 0.0))


def cpc_index(
    total_return_pct: float,
    max_drawdown_pct: float,
    win_rate_pct: float,
    profit_factor_value: float,
) -> float:
    """Custom CPC Index example built from existing metrics."""
    if max_drawdown_pct <= 0 or profit_factor_value <= 0:
        return 0.0
    return float(
        (total_return_pct / max_drawdown_pct)
        * (win_rate_pct / 100.0)
        * profit_factor_value
    )


def common_sense_ratio(trades: pd.DataFrame) -> float:
    """Custom CSR example: profit factor times payoff ratio."""
    if len(trades) == 0:
        return 0.0
    pf = ratios.profit_factor(trades)
    payoff = ratios.payoff_ratio(trades)
    return float(pf * payoff)


def example_1_basic_return_metrics(equity: pd.Series, rets: pd.Series) -> None:
    """Demonstrate basic return metrics calculation."""
    logger.info("=" * 80)
    logger.info("EXAMPLE 1: Basic Return Metrics (EURUSD)")
    logger.info("=" * 80)

    total_ret = returns.total_return(equity)
    total_ret_pct = (equity.iloc[-1] - equity.iloc[0]) / equity.iloc[0] * 100
    cagr_pct = returns.cagr(equity)
    sharpe = ratios.sharpe_ratio(rets, risk_free_rate=0.0, annualize=True)
    sortino = ratios.sortino_ratio(rets, target_return=0.0, annualize=True)

    logger.info("Return Metrics:")
    logger.info(f"  Total Return:      {total_ret:>10.2f}")
    logger.info(f"  Total Return (%):  {total_ret_pct:>10.2f}%")
    logger.info(f"  CAGR (%):          {cagr_pct:>10.2f}%")
    logger.info(f"  Sharpe Ratio:      {sharpe:>10.2f}")
    logger.info(f"  Sortino Ratio:     {sortino:>10.2f}")


def example_2_drawdown_analysis(equity: pd.Series) -> None:
    """Demonstrate drawdown analysis."""
    logger.info("=" * 80)
    logger.info("EXAMPLE 2: Drawdown Analysis (GBPUSD)")
    logger.info("=" * 80)

    max_dd = drawdowns.max_strategy_drawdown(equity)
    max_dd_pct = drawdowns.max_strategy_drawdown_percent(equity)
    avg_dd = drawdowns.avg_drawdown(equity)
    max_dd_dur = drawdowns.max_drawdown_duration(equity)
    avg_dd_dur = drawdowns.avg_drawdown_duration(equity)
    calmar = ratios.calmar_ratio(returns.cagr(equity), max_dd_pct)

    logger.info("Drawdown Metrics:")
    logger.info(f"  Max Drawdown:           {max_dd:>10.2f}")
    logger.info(f"  Max Drawdown (%):       {max_dd_pct:>10.2f}%")
    logger.info(f"  Avg Drawdown:           {avg_dd:>10.2f}")
    logger.info(f"  Max Drawdown Duration:  {max_dd_dur:>10} bars")
    logger.info(f"  Avg Drawdown Duration:  {avg_dd_dur:>10.1f} bars")
    logger.info(f"  Calmar Ratio:           {calmar:>10.2f}")


def example_3_risk_metrics(rets: pd.Series) -> None:
    """Demonstrate risk metrics calculation."""
    logger.info("=" * 80)
    logger.info("EXAMPLE 3: Risk Metrics (USDJPY)")
    logger.info("=" * 80)

    vol = risks.annualized_volatility(rets, periods_per_year=252)
    down_vol = risks.downside_volatility(rets)
    var_95 = risks.value_at_risk(rets, confidence=0.95)
    cvar_95 = risks.conditional_var(rets, confidence=0.95)
    skew_val = distributions.skewness(rets)
    kurt_val = distributions.kurtosis(rets)

    logger.info("Risk Metrics:")
    logger.info(f"  Volatility (Ann):    {vol:>10.2%}")
    logger.info(f"  Downside Volatility: {down_vol:>10.2%}")
    logger.info(f"  VaR (95%):           {var_95:>10.2%}")
    logger.info(f"  CVaR (95%):          {cvar_95:>10.2%}")
    logger.info(f"  Skewness:            {skew_val:>10.2f}")
    logger.info(f"  Kurtosis:            {kurt_val:>10.2f}")


def example_4_trade_metrics(trades: pd.DataFrame) -> None:
    """Demonstrate trade-based metrics."""
    logger.info("=" * 80)
    logger.info("EXAMPLE 4: Trade-Based Metrics (AUDUSD)")
    logger.info("=" * 80)

    win_rate_pct = metrics.win_rate(trades)
    expectancy_val = ratios.expectancy(trades)
    sqn_val = metrics.sqn(trades)
    kelly = calc_kelly_fraction(trades)

    logger.info("Trade Metrics:")
    logger.info(f"  Win Rate:      {win_rate_pct:>10.2f}%")
    logger.info(f"  Expectancy:    {expectancy_val:>10.2f}")
    logger.info(f"  SQN:           {sqn_val:>10.2f}")
    logger.info(f"  Kelly Fraction:{kelly:>10.2f}")


def example_5_exposure_efficiency(trades: pd.DataFrame) -> None:
    """Demonstrate exposure and efficiency metrics."""
    logger.info("=" * 80)
    logger.info("EXAMPLE 5: Exposure and Efficiency (NZDUSD)")
    logger.info("=" * 80)

    cap_eff = efficiency.capital_efficiency(trades)
    time_eff = efficiency.time_efficiency(trades)
    exposure_ratio = risks.exposure_time_ratio(trades)

    logger.info("Exposure and Efficiency:")
    logger.info(f"  Capital Efficiency: {cap_eff:>10.6f}")
    logger.info(f"  Time Efficiency:    {time_eff:>10.6f}")
    logger.info(f"  Exposure Ratio:     {exposure_ratio:>10.2%}")


def example_6_advanced_metrics(equity: pd.Series, trades: pd.DataFrame) -> None:
    """Demonstrate advanced metrics."""
    logger.info("=" * 80)
    logger.info("EXAMPLE 6: Advanced Metrics (USDCAD)")
    logger.info("=" * 80)

    total_ret_pct = (equity.iloc[-1] - equity.iloc[0]) / equity.iloc[0] * 100
    max_dd_pct = drawdowns.max_strategy_drawdown_percent(equity)
    win_rate_pct = metrics.win_rate(trades)
    pf = ratios.profit_factor(trades)

    cpc = cpc_index(total_ret_pct, max_dd_pct, win_rate_pct, pf)
    csr = common_sense_ratio(trades)
    ror = risks.risk_of_ruin(trades, risk_per_trade=2.0, target_drawdown=50.0)

    logger.info("Advanced Metrics:")
    logger.info(f"  CPC Index (Custom):      {cpc:>10.2f}")
    logger.info(f"  Common Sense (Custom):   {csr:>10.2f}")
    logger.info(f"  Risk of Ruin (2% risk):  {ror:>10.2%}")


def example_7_benchmark_comparison(equity: pd.Series, data: pd.DataFrame) -> None:
    """Demonstrate benchmark comparison metrics."""
    logger.info("=" * 80)
    logger.info("EXAMPLE 7: Benchmark Comparison (EURUSD vs Buy/Hold)")
    logger.info("=" * 80)

    benchmark_equity = 10000.0 * (data["close"] / data["close"].iloc[0])
    bench_rets = benchmark.benchmark_returns(benchmark_equity)
    strat_rets = returns.returns_series(equity)

    beta_val = benchmark.beta(strat_rets, bench_rets)
    alpha_val = benchmark.alpha(strat_rets, bench_rets, risk_free_rate=0.0)
    info_ratio = ratios.information_ratio(strat_rets, bench_rets, annualize=True)

    logger.info("Benchmark Metrics:")
    logger.info(f"  Beta:             {beta_val:>10.2f}")
    logger.info(f"  Alpha (Ann):      {alpha_val:>10.2f}")
    logger.info(f"  Information Ratio:{info_ratio:>10.2f}")


def example_8_period_returns(equity: pd.Series) -> None:
    """Demonstrate monthly and yearly returns."""
    logger.info("=" * 80)
    logger.info("EXAMPLE 8: Monthly and Yearly Returns")
    logger.info("=" * 80)

    monthly = returns.monthly_returns(equity)
    yearly = returns.annual_returns(equity)

    logger.info("Yearly Returns:")
    for date_idx, val in yearly.items():
        logger.info(f"  {date_idx.date()}: {val:>8.2%}")

    logger.info("Monthly Returns (first 6):")
    logger.info(monthly.head(6).to_string())


def example_9_full_stats(result: object) -> None:
    """Demonstrate comprehensive stats usage."""
    logger.info("=" * 80)
    logger.info("EXAMPLE 9: Full Stats (Comprehensive Summary)")
    logger.info("=" * 80)

    summary = result.comprehensive_summary()

    logger.info("Key Summary Fields:")
    for key in [
        "total_return",
        "total_return_pct",
        "cagr",
        "max_drawdown",
        "max_drawdown_pct",
        "win_rate",
        "profit_factor",
        "sharpe_ratio",
    ]:
        value = summary.get(key, "n/a")
        logger.info(f"  {key}: {value}")


def example_10_visualizations(equity: pd.Series, output_dir: Path) -> None:
    """Generate simple plots if matplotlib is available."""
    logger.info("=" * 80)
    logger.info("EXAMPLE 10: Visualization Examples")
    logger.info("=" * 80)

    if plt is None:
        logger.warning("Matplotlib not available; skipping charts.")
        return

    output_dir.mkdir(parents=True, exist_ok=True)

    drawdown_series = drawdowns.drawdown_series(equity)

    fig, (ax1, ax2) = plt.subplots(2, 1, figsize=(12, 8), sharex=True)
    ax1.plot(equity.index, equity.values, label="Equity")
    ax1.set_title("Equity Curve")
    ax1.set_ylabel("Equity")
    ax1.grid(True, alpha=0.3)
    ax1.legend()

    ax2.fill_between(
        drawdown_series.index,
        drawdown_series.values,
        0,
        alpha=0.3,
        color="red",
    )
    ax2.set_title("Drawdown")
    ax2.set_ylabel("Drawdown")
    ax2.grid(True, alpha=0.3)

    fig.tight_layout()
    eq_path = output_dir / "stats_equity_drawdown.png"
    fig.savefig(eq_path, dpi=150, bbox_inches="tight")
    plt.close(fig)
    logger.info(f"Chart saved: {eq_path}")

    if sns is None:
        logger.info("Seaborn not available; skipping heatmap.")
        return

    monthly = returns.monthly_returns(equity)
    if monthly.empty:
        logger.info("Monthly returns empty; skipping heatmap.")
        return

    monthly_df = monthly.to_frame("return")
    monthly_df["year"] = monthly_df.index.year
    monthly_df["month"] = monthly_df.index.month
    heatmap_data = monthly_df.pivot(index="month", columns="year", values="return")
    fig, ax = plt.subplots(figsize=(10, 6))
    sns.heatmap(heatmap_data * 100, annot=True, fmt=".1f", cmap="RdYlGn", ax=ax)
    ax.set_title("Monthly Returns Heatmap")
    heatmap_path = output_dir / "stats_monthly_heatmap.png"
    fig.tight_layout()
    fig.savefig(heatmap_path, dpi=150, bbox_inches="tight")
    plt.close(fig)
    logger.info(f"Chart saved: {heatmap_path}")


def main() -> None:
    """Run all examples."""
    logger.info("\n" + "=" * 80)
    logger.info("BACKTEST STATISTICS MODULE - COMPREHENSIVE EXAMPLES")
    logger.info("=" * 80 + "\n")

    output_dir = project_root / "output" / "plotting"
    os.makedirs(output_dir, exist_ok=True)

    data, equity, rets, trades, result = run_backtest(
        symbol="EURUSD",
        start_date="2020-01-01",
        end_date="2023-12-31",
        timeframe="D1",
    )

    example_1_basic_return_metrics(equity, rets)
    example_2_drawdown_analysis(equity)
    example_3_risk_metrics(rets)
    example_4_trade_metrics(trades)
    example_5_exposure_efficiency(trades)
    example_6_advanced_metrics(equity, trades)
    example_7_benchmark_comparison(equity, data)
    example_8_period_returns(equity)
    example_9_full_stats(result)
    example_10_visualizations(equity, output_dir)

    logger.info("\nAll examples completed.")


if __name__ == "__main__":
    main()

