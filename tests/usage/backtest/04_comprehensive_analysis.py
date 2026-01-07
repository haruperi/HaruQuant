"""
Comprehensive Analysis Example

Purpose:
- Demonstrate complete end-to-end backtest workflow
- Combine backtest execution, finance metrics, and plotting
- Create professional analysis report
- Show best practices for real-world usage

Key Concepts:
- Complete workflow integration
- Professional reporting
- Result organization
- Best practices

Usage:
    python tests/usage/backtest/04_comprehensive_analysis.py

Output:
- Comprehensive console output
- Multiple analysis files in output/ directory
- Professional HTML report with all metrics and charts
"""

from pathlib import Path
import sys
from datetime import datetime

# Add project root to path
project_root = Path(__file__).parent.parent.parent.parent
sys.path.insert(0, str(project_root))

import pandas as pd
from datetime import datetime
from apps.backtest import EventDrivenEngine
from data.strategies.trend_following import TrendFollowingStrategy
from apps.finance import metrics, ratios, drawdowns, risks, returns, efficiency, distributions
from apps.plotting import (
    create_html_report,
    plot_returns,
    plot_drawdown,
    plot_monthly_heatmap,
    plot_distribution,
    initialize_plotting,
    set_theme
)
from apps.mt5.client import MT5Client
from apps.sqlite.users import UserManager
from apps.logger import logger


# Create output directory with timestamp
TIMESTAMP = datetime.now().strftime("%Y%m%d_%H%M%S")
OUTPUT_DIR = Path(__file__).parent / "output" / f"comprehensive_{TIMESTAMP}"
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)


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
        raise ValueError(f"No MT5 credentials found")
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
        df = client.get_bars(symbol=symbol, timeframe=timeframe, date_from=date_from, date_to=date_to)
        if df.empty:
            raise ValueError("No data retrieved from MT5")
        return df


def save_metrics_to_file(result, equity_series, returns_series, trades_df):
    """Save all metrics to a text file."""
    metrics_path = OUTPUT_DIR / "metrics_summary.txt"
    
    with open(metrics_path, 'w') as f:
        f.write("=" * 70 + "\n")
        f.write("COMPREHENSIVE BACKTEST METRICS SUMMARY\n")
        f.write("=" * 70 + "\n\n")
        
        # Strategy info
        f.write(f"Strategy: {result.strategy_name}\n")
        f.write(f"Symbol: {result.symbol}\n")
        f.write(f"Timeframe: {result.timeframe}\n")
        f.write(f"Period: {result.start_date} to {result.end_date}\n")
        f.write(f"Initial Balance: ${result.initial_balance:,.2f}\n")
        f.write(f"Final Balance: ${result.final_balance:,.2f}\n\n")
        
        # Returns
        f.write("-" * 70 + "\n")
        f.write("RETURN METRICS\n")
        f.write("-" * 70 + "\n")
        f.write(f"Total Return: ${result.total_return:,.2f} ({result.total_return_pct:.2f}%)\n")
        if len(equity_series) > 0:
            cagr = returns.cagr(equity_series)
            f.write(f"CAGR: {cagr:.2f}%\n")
        f.write("\n")
        
        # Ratios
        f.write("-" * 70 + "\n")
        f.write("RISK-ADJUSTED RATIOS\n")
        f.write("-" * 70 + "\n")
        if len(returns_series) > 0:
            sharpe = ratios.sharpe_ratio(returns_series, risk_free_rate=0.0)
            sortino = ratios.sortino_ratio(returns_series, target_return=0.0)
            cagr_value = returns.cagr(equity_series)
            max_dd_value = drawdowns.max_strategy_drawdown(equity_series)
            calmar = ratios.calmar_ratio(cagr_value, max_dd_value)
            f.write(f"Sharpe Ratio: {sharpe:.4f}\n")
            f.write(f"Sortino Ratio: {sortino:.4f}\n")
            f.write(f"Calmar Ratio: {calmar:.4f}\n")
        f.write("\n")
        
        # Drawdowns
        f.write("-" * 70 + "\n")
        f.write("DRAWDOWN METRICS\n")
        f.write("-" * 70 + "\n")
        f.write(f"Max Drawdown: ${result.max_drawdown:,.2f} ({result.max_drawdown_pct:.2f}%)\n")
        if len(equity_series) > 0:
            dd_duration = drawdowns.max_drawdown_duration(equity_series)
            recovery_factor = drawdowns.recovery_factor(equity_series)
            ulcer = drawdowns.ulcer_index(equity_series)
            f.write(f"Max DD Duration: {dd_duration} days\n")
            f.write(f"Recovery Factor: {recovery_factor:.2f}\n")
            f.write(f"Ulcer Index: {ulcer:.2f}\n")
        f.write("\n")
        
        # Trades
        f.write("-" * 70 + "\n")
        f.write("TRADE METRICS\n")
        f.write("-" * 70 + "\n")
        f.write(f"Total Trades: {result.total_trades}\n")
        f.write(f"Win Rate: {result.win_rate:.2f}%\n")
        f.write(f"Profit Factor: {result.profit_factor:.2f}\n")
        f.write(f"Expectancy: ${result.expectancy:.2f}\n")
        f.write("\n")
        
        f.write("=" * 70 + "\n")
        f.write(f"Report generated: {datetime.now()}\n")
        f.write("=" * 70 + "\n")
    
    return metrics_path


def save_trades_to_csv(result):
    """Save trade history to CSV."""
    if len(result.trades) == 0:
        return None
    
    trades_path = OUTPUT_DIR / "trades_history.csv"
    trades_df = pd.DataFrame([t.to_dict() for t in result.trades])
    trades_df.to_csv(trades_path, index=False)
    
    return trades_path


def main():
    """Main execution function."""
    logger.info("=" * 70)
    logger.info("COMPREHENSIVE BACKTEST ANALYSIS")
    logger.info("=" * 70)
    logger.info(f"\nOutput Directory: {OUTPUT_DIR}")
    
    # Step 1: Initialize
    logger.info("\n[1/6] Initializing...")
    initialize_plotting()
    set_theme('professional')
    
    # Step 2: Load data
    logger.info("\n[2/6] Loading data from MT5...")
    date_from = datetime(2025, 1, 1)
    date_to = datetime(2025, 12, 31)
    data = load_mt5_data('EURUSD', 'H1', date_from, date_to)
    logger.info(f"Loaded {len(data)} bars from {data.index[0]} to {data.index[-1]}")
    
    # Step 3: Configure and run backtest
    logger.info("\n[3/6] Running backtest...")
    
    strategy_params = {
        'symbol': 'EURUSD',
        'fast_period': 20,
        'slow_period': 50,
        'filter_period': 200
    }
    
    strategy = TrendFollowingStrategy(params=strategy_params)
    
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
    
    # Step 4: Calculate comprehensive metrics
    logger.info("\n[4/6] Calculating comprehensive metrics...")
    
    equity_series = result._get_equity_series()
    returns_series = result._get_returns_series()
    
    if len(result.trades) > 0:
        trades_df = pd.DataFrame([t.to_dict() for t in result.trades])
    else:
        trades_df = pd.DataFrame()
    
    # Save metrics to file
    metrics_path = save_metrics_to_file(result, equity_series, returns_series, trades_df)
    logger.info(f"Metrics saved to: {metrics_path}")
    
    # Save trades to CSV
    trades_path = save_trades_to_csv(result)
    if trades_path:
        logger.info(f"Trades saved to: {trades_path}")
    
    # Step 5: Create visualizations
    logger.info("\n[5/6] Creating visualizations...")
    
    # Equity curve
    equity_path = OUTPUT_DIR / "equity_curve.png"
    plot_returns(equity_series, title="Equity Curve", savefig=str(equity_path), show=False)
    logger.info(f"  - Equity curve: {equity_path.name}")
    
    # Drawdown
    drawdown_path = OUTPUT_DIR / "drawdown.png"
    plot_drawdown(equity_series, title="Drawdown", savefig=str(drawdown_path), show=False)
    logger.info(f"  - Drawdown chart: {drawdown_path.name}")
    
    # Monthly heatmap
    heatmap_path = OUTPUT_DIR / "monthly_returns.png"
    try:
        plot_monthly_heatmap(equity_series, title="Monthly Returns", savefig=str(heatmap_path), show=False)
        logger.info(f"  - Monthly heatmap: {heatmap_path.name}")
    except Exception as e:
        logger.warning(f"  - Could not create monthly heatmap: {e}")
    
    # Returns distribution
    if len(returns_series) > 0:
        dist_path = OUTPUT_DIR / "returns_distribution.png"
        try:
            plot_distribution(equity_series, title="Returns Distribution", savefig=str(dist_path), show=False)
            logger.info(f"  - Returns distribution: {dist_path.name}")
        except Exception as e:
            logger.warning(f"  - Could not create distribution: {e}")
    
    # Step 6: Create HTML report
    logger.info("\n[6/6] Creating HTML report...")
    report_path = OUTPUT_DIR / "comprehensive_report.html"
    
    try:
        class _ReportBroker:
            def __init__(self, equity):
                self.equity = equity
                self.closed_trades = []

        class _ReportData:
            def __init__(self, df):
                self.df = df

        class _ReportStrategy:
            def __init__(self, df):
                self.data = _ReportData(df)

        report_stats = {
            "Total Return [%]": result.total_return_pct,
            "Sharpe Ratio": result.sharpe_ratio,
            "Max. Drawdown [%]": result.max_drawdown_pct,
            "Win Rate [%]": result.win_rate,
            "# Trades": result.total_trades,
            "Avg. Trade [%]": 0.0,
        }

        plot_df = data.copy()
        rename_map = {}
        for col in plot_df.columns:
            lower_col = str(col).lower()
            if lower_col == "open":
                rename_map[col] = "Open"
            elif lower_col == "high":
                rename_map[col] = "High"
            elif lower_col == "low":
                rename_map[col] = "Low"
            elif lower_col == "close":
                rename_map[col] = "Close"
            elif lower_col in ("volume", "tick_volume"):
                rename_map[col] = "Volume"
        if rename_map:
            plot_df = plot_df.rename(columns=rename_map)

        report_payload = {
            "stats": report_stats,
            "broker": _ReportBroker(equity_series),
            "strategy": _ReportStrategy(plot_df),
        }

        create_html_report(
            report_payload,
            output_path=str(report_path),
            title=f"Comprehensive Backtest Analysis - {result.strategy_name}",
            include_plots=["main", "equity", "drawdown", "monthly_heatmap"],
        )
        logger.info(f"HTML report created: {report_path}")
    except Exception as e:
        logger.warning(f"Could not create HTML report: {e}")
    
    # Final summary
    logger.info("\n" + "=" * 70)
    logger.info("ANALYSIS COMPLETE")
    logger.info("=" * 70)
    
    logger.info(f"\nStrategy Performance:")
    logger.info(f"  Return: {result.total_return_pct:.2f}%")
    logger.info(f"  Max Drawdown: {result.max_drawdown_pct:.2f}%")
    logger.info(f"  Win Rate: {result.win_rate:.2f}%")
    logger.info(f"  Profit Factor: {result.profit_factor:.2f}")
    
    if len(returns_series) > 0:
        sharpe = ratios.sharpe_ratio(returns_series, risk_free_rate=0.0)
        sortino = ratios.sortino_ratio(returns_series, target_return=0.0)
        logger.info(f"  Sharpe Ratio: {sharpe:.2f}")
        logger.info(f"  Sortino Ratio: {sortino:.2f}")
    
    logger.info(f"\nAll results saved to: {OUTPUT_DIR}")
    logger.info(f"\nGenerated Files:")
    for file in OUTPUT_DIR.iterdir():
        if file.is_file():
            logger.info(f"  - {file.name}")
    
    logger.info("\n" + "=" * 70)
    
    return result


if __name__ == "__main__":
    result = main()
