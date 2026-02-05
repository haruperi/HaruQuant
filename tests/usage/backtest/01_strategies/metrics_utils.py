"""Shared metrics display utility for backtest runners."""

import pandas as pd
from apps.finance import metrics, ratios, drawdowns, risks, returns, efficiency, distributions
from apps.logger import logger

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

def display_metrics(result):
    """Display comprehensive metrics for a backtest result."""

    # Get trades DataFrame (use get_trades_df method which handles conversion)
    trades_df = result.get_trades_df()
    if trades_df.empty:
        logger.warning("No trades executed, metrics will be limited")
    
    # Get equity series
    equity_series = result._get_equity_series()
    returns_series = result._get_returns_series()
    
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
        sharpe = ratios.sharpe_ratio(returns_series, risk_free_rate=0.0)
        sortino = ratios.sortino_ratio(returns_series, target_return=0.0)
        logger.info(f"  - Sharpe ratio of {sharpe:.2f}")
        logger.info(f"  - Sortino ratio of {sortino:.2f}")
    
    logger.info(f"\n  All metrics calculated successfully!")
    logger.info(f"  Total metrics displayed: 40+")

    # ========================================================================
    # TRADES
    # ========================================================================
    print_section("Backtest Trades")
    
    if len(trades_df) > 0:
        # Print header
        header = f"{'Type':<6} {'Entry Date':<20} {'Exit Date':<20} {'Entry':>10} {'Exit':>10} {'Size':>8} {'Comm':>8} {'Swap':>8} {'Gross $':>10} {'Net $':>10} {'Pips':>8} {'Duration':>12}"
        logger.info("-" * len(header))
        logger.info(header)
        logger.info("-" * len(header))
        
        # Print top 50 trades to avoid flooding if there are too many
        for _, trade in trades_df.head(50).iterrows():
            direction = str(trade.get('type', 'UNKNOWN')).upper()
            entry_time = str(trade.get('open_time', ''))
            exit_time = str(trade.get('close_time', ''))
            entry_price = trade.get('open_price', 0.0)
            exit_price = trade.get('close_price', 0.0)
            size = trade.get('size', 0.0)
            commission = trade.get('commission', 0.0)
            swap = trade.get('swap', 0.0)
            net_pnl = trade.get('profit_loss', 0.0)
            # Calculate gross P&L (before commission and swap)
            gross_pnl = net_pnl - commission - swap
            pnl_pips = trade.get('profit_loss_pips', 0.0)
            duration = trade.get('time_in_trade_formatted', '0m')

            row = f"{direction:<6} {entry_time:<20} {exit_time:<20} {entry_price:>10.5f} {exit_price:>10.5f} {size:>8.2f} {commission:>8.2f} {swap:>8.2f} {gross_pnl:>10.2f} {net_pnl:>10.2f} {pnl_pips:>8.1f} {duration:>12}"
            logger.info(row)
            
        if len(trades_df) > 50:
            logger.info(f"... and {len(trades_df) - 50} more trades ...")

        trades_df.to_csv("trades.csv")
            
    else:
        logger.info("  No trades executed during the backtest period.")
    print_section("COMPLETE")
    
