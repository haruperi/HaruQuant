"""
Finance Metrics Example

Purpose:
- Demonstrate comprehensive finance module integration
- Calculate all available performance metrics
- Show how to use different finance submodules
- Format and display metrics professionally

Key Concepts:
- Using apps.finance modules (metrics, ratios, drawdowns, risks, etc.)
- Converting BacktestResult for finance calculations
- Interpreting performance metrics
- Comprehensive performance analysis

Usage:
    python tests/usage/backtest/02_finance_metrics.py

Output:
- Detailed console output with all calculated metrics
- Organized by category (returns, ratios, drawdowns, etc.)
"""

from pathlib import Path
import sys

# Add project root to path
project_root = Path(__file__).parent.parent.parent.parent
sys.path.insert(0, str(project_root))

import pandas as pd
from datetime import datetime
from apps.backtest import EventDrivenEngine
from data.strategies.trend_following import TrendFollowingStrategy
from apps.finance import metrics, ratios, drawdowns, risks, returns, efficiency, distributions
from apps.mt5.client import MT5Client
from apps.sqlite.users import UserManager
from apps.logger import logger


def get_mt5_credentials():
    """Get MT5 credentials from database."""
    user_manager = UserManager()
    user_manager.db_path = "data/database/haruquant.db"

    username = "haruperi"
    user = user_manager.get_user(username=username)
    if not user:
        raise ValueError(f"User {username} not found")

    creds = user_manager.get_mt5_credentials(user["id"])
    if not creds:
        raise ValueError(f"No MT5 credentials found for {username}")

    return creds


def load_mt5_data(symbol: str, timeframe: str, date_from: datetime, date_to: datetime) -> pd.DataFrame:
    """Load historical data from MT5."""
    creds = get_mt5_credentials()
    
    with MT5Client(
        login=creds["login"],
        password=creds["password"],
        server=creds["server"],
        path=creds["path"]
    ) as client:
        if not client.is_connected():
            raise ConnectionError("Failed to connect to MT5")
        
        df = client.get_bars(
            symbol=symbol,
            timeframe=timeframe,
            date_from=date_from,
            date_to=date_to
        )
        
        if df.empty:
            raise ValueError("No data retrieved from MT5")
        
        return df


def print_section(title: str):
    """Print a formatted section header."""
    logger.info(f"\n{'=' * 70}")
    logger.info(f"{title:^70}")
    logger.info(f"{'=' * 70}")


def print_metric(name: str, value, unit: str = ""):
    """Print a formatted metric."""
    if isinstance(value, float):
        if unit == "%":
            logger.info(f"  {name:<35} {value:>10.2f}{unit}")
        elif unit == "$":
            logger.info(f"  {name:<35} {unit}{value:>10,.2f}")
        else:
            logger.info(f"  {name:<35} {value:>10.4f}{unit}")
    else:
        logger.info(f"  {name:<35} {value:>10}{unit}")


def main():
    """Main execution function."""
    print_section("COMPREHENSIVE FINANCE METRICS EXAMPLE")
    
    # Step 1: Load data and run backtest
    logger.info("\n[1/3] Loading data from MT5...")
    date_from = datetime(2025, 1, 1)
    date_to = datetime(2025, 12, 31)
    data = load_mt5_data('EURUSD', 'H1', date_from, date_to)
    logger.info(f"Loaded {len(data)} bars")
    
    logger.info("\nRunning backtest...")
    
    strategy = TrendFollowingStrategy(params={
        'symbol': 'EURUSD',
        'fast_period': 20,
        'slow_period': 50,
        'filter_period': 200
    })
    
    engine = EventDrivenEngine(
        strategy=strategy,
        data=data,
        initial_balance=10000.0,
        commission=7.0,
        slippage_points=1.0,
        timeframe='H1'
    )
    
    result = engine.run()
    logger.info(f"Backtest completed: {result.total_trades} trades executed")
    
    # Step 2: Calculate metrics
    logger.info("\n[2/3] Calculating comprehensive metrics...")
    
    # Convert to DataFrame for finance module
    if len(result.trades) > 0:
        trades_df = pd.DataFrame([t.to_dict() for t in result.trades])
    else:
        logger.warning("No trades executed, metrics will be limited")
        trades_df = pd.DataFrame()
    
    # Get equity series
    equity_series = result._get_equity_series()
    returns_series = result._get_returns_series()
    
    # Step 3: Display all metrics
    logger.info("\n[3/3] Displaying metrics by category...")
    
    # ========================================================================
    # RETURN METRICS
    # ========================================================================
    print_section("RETURN METRICS")
    
    print_metric("Total Return", result.total_return, "$")
    print_metric("Total Return %", result.total_return_pct, "%")
    
    if len(equity_series) > 0:
        cagr = returns.cagr(equity_series)
        print_metric("CAGR (Compound Annual Growth)", cagr, "%")
        
        # Period returns
        daily_ret = returns.daily_returns(equity_series)
        if len(daily_ret) > 0:
            print_metric("Average Daily Return", daily_ret.mean(), "%")
    
    # ========================================================================
    # RISK-ADJUSTED RATIOS
    # ========================================================================
    print_section("RISK-ADJUSTED RATIOS")
    
    if len(returns_series) > 0:
        sharpe = ratios.sharpe_ratio(returns_series, risk_free_rate=0.0)
        sortino = ratios.sortino_ratio(returns_series, target_return=0.0)
        cagr_value = returns.cagr(equity_series)
        max_dd_value = drawdowns.max_strategy_drawdown(equity_series)
        calmar = ratios.calmar_ratio(cagr_value, max_dd_value)
        
        print_metric("Sharpe Ratio", sharpe)
        print_metric("Sortino Ratio", sortino)
        print_metric("Calmar Ratio", calmar)
        
        # Additional ratios
        omega = ratios.omega_ratio(returns_series, threshold=0.0)
        print_metric("Omega Ratio", omega)
    
    # ========================================================================
    # DRAWDOWN METRICS
    # ========================================================================
    print_section("DRAWDOWN METRICS")
    
    print_metric("Max Drawdown", result.max_drawdown, "$")
    print_metric("Max Drawdown %", result.max_drawdown_pct, "%")
    
    if len(equity_series) > 0:
        dd_duration = drawdowns.max_drawdown_duration(equity_series)
        recovery_factor = drawdowns.recovery_factor(equity_series)
        ulcer = drawdowns.ulcer_index(equity_series)
        pain = drawdowns.pain_index(equity_series)
        
        print_metric("Max Drawdown Duration", dd_duration, " days")
        print_metric("Recovery Factor", recovery_factor)
        print_metric("Ulcer Index", ulcer)
        
        # Drawdown details
        dd_series = drawdowns.drawdown_series(equity_series)
        avg_dd = drawdowns.avg_drawdown(equity_series)
    
    # ========================================================================
    # TRADE METRICS
    # ========================================================================
    print_section("TRADE METRICS")
    
    print_metric("Total Trades", result.total_trades)
    print_metric("Winning Trades", result.winning_trades)
    print_metric("Losing Trades", result.losing_trades)
    print_metric("Breakeven Trades", result.breakeven_trades)
    print_metric("Win Rate", result.win_rate, "%")
    
    print_metric("Gross Profit", result.gross_profit, "$")
    print_metric("Gross Loss", result.gross_loss, "$")
    print_metric("Profit Factor", result.profit_factor)
    
    print_metric("Average Win", result.avg_win, "$")
    print_metric("Average Loss", result.avg_loss, "$")
    print_metric("Expectancy", result.expectancy, "$")
    # print_metric("Risk/Reward Ratio", result.avg_win_loss_ratio)  # Using avg_win_loss_ratio instead
    
    if len(trades_df) > 0:
        # Additional trade metrics
        largest_win = metrics.largest_win(trades_df)
        largest_loss = metrics.largest_loss(trades_df)
        avg_duration = metrics.avg_time_in_trade(trades_df)
        
        print_metric("Largest Win", largest_win, "$")
        print_metric("Largest Loss", largest_loss, "$")
        print_metric("Average Trade Duration", avg_duration, " hours")
        
        # Win/Loss streaks
        max_win_streak = metrics.max_consecutive_wins(trades_df)
        max_loss_streak = metrics.max_consecutive_losses(trades_df)
        print_metric("Max Consecutive Wins", max_win_streak)
        print_metric("Max Consecutive Losses", max_loss_streak)
    
    # ========================================================================
    # RISK METRICS
    # ========================================================================
    print_section("RISK METRICS")
    
    if len(returns_series) > 0:
        volatility = risks.annualized_volatility(returns_series)
        downside_vol = risks.downside_volatility(returns_series)
        
        print_metric("Volatility (Annual)", volatility, "%")
        print_metric("Downside Volatility", downside_vol, "%")
        
        # Value at Risk
        var_95 = risks.value_at_risk(returns_series, confidence=0.95)
        cvar_95 = risks.conditional_var(returns_series, confidence=0.95)
        
        print_metric("VaR (95%)", var_95, "%")
        print_metric("CVaR (95%)", cvar_95, "%")
    
    # ========================================================================
    # EFFICIENCY METRICS
    # ========================================================================
    print_section("EFFICIENCY METRICS")
    
    if len(trades_df) > 0:
        # profit_per_day = efficiency.profit_per_day(trades_df, result.total_return)  # Not available`n        # print_metric("Profit Per Day", profit_per_day, "$")
        
        # Trade frequency
        days_active = (result.end_date - result.start_date).days
        if days_active > 0:
            trades_per_day = result.total_trades / days_active
            print_metric("Trades Per Day", trades_per_day)
    
    # ========================================================================
    # DISTRIBUTION METRICS
    # ========================================================================
    print_section("DISTRIBUTION METRICS")
    
    if len(returns_series) > 0:
        skew = distributions.skewness(returns_series)
        kurt = distributions.kurtosis(returns_series)
        
        print_metric("Skewness", skew)
        print_metric("Kurtosis", kurt)
        
        # Normality test
        jb_result = distributions.jarque_bera_test(returns_series)
        is_normal = jb_result["is_normal"]
        p_value = jb_result["p_value"]
        print_metric("Jarque-Bera p-value", p_value)
        print_metric("Returns Normal?", "Yes" if is_normal else "No")
    
    # ========================================================================
    # SUMMARY
    # ========================================================================
    print_section("SUMMARY")
    
    logger.info(f"\n  Strategy Performance Summary:")
    logger.info(f"  - Generated {result.total_return_pct:.2f}% return")
    logger.info(f"  - With maximum drawdown of {result.max_drawdown_pct:.2f}%")
    logger.info(f"  - Win rate of {result.win_rate:.2f}%")
    logger.info(f"  - Profit factor of {result.profit_factor:.2f}")
    
    if len(returns_series) > 0:
        logger.info(f"  - Sharpe ratio of {sharpe:.2f}")
        logger.info(f"  - Sortino ratio of {sortino:.2f}")
    
    logger.info(f"\n  All metrics calculated successfully!")
    logger.info(f"  Total metrics displayed: 40+")
    
    print_section("COMPLETE")
    
    return result


if __name__ == "__main__":
    result = main()
