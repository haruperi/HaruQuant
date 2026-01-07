"""
Plotting Results Example

Purpose:
- Demonstrate plotting module capabilities
- Show how to create individual plots
- Generate comprehensive HTML reports
- Save plots to files

Key Concepts:
- Using apps.plotting functions
- Customizing plot appearance
- Generating HTML reports
- Saving and displaying plots

Usage:
    python tests/usage/backtest/03_plotting_results.py

Output:
- Multiple plot files in output/ directory
- HTML report with embedded charts
- Console output with file locations
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
from apps.plotting import (
    plot,
    create_html_report,
    plot_returns,
    plot_drawdown,
    plot_monthly_heatmap,
    plot_distribution,
    plot_rolling_sharpe,
    initialize_plotting,
    set_theme
)
from apps.mt5.client import MT5Client
from apps.sqlite.users import UserManager
from apps.logger import logger


# Create output directory
OUTPUT_DIR = Path(__file__).parent / "output"
OUTPUT_DIR.mkdir(exist_ok=True)


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


def main():
    """Main execution function."""
    logger.info("=" * 70)
    logger.info("PLOTTING RESULTS EXAMPLE")
    logger.info("=" * 70)
    
    # Initialize plotting
    logger.info("\n[1/5] Initializing plotting system...")
    initialize_plotting()
    set_theme('professional')  # Use professional theme
    logger.info("Plotting system initialized with 'professional' theme")
    
    # Load data and run backtest
    logger.info("\n[2/5] Loading data from MT5...")
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
    logger.info(f"Backtest completed: {result.total_trades} trades")
    
    # Create individual plots
    logger.info("\n[3/5] Creating individual plots...")
    
    # Get equity and returns data
    equity_series = result._get_equity_series()
    returns_series = result._get_returns_series()
    
    plots_created = []
    
    # 1. Equity curve
    logger.info("  - Creating equity curve...")
    equity_path = OUTPUT_DIR / "equity_curve.png"
    try:
        plot_returns(
            equity_series,
            title=f"{result.strategy_name} - Equity Curve",
            save_path=str(equity_path),
            show=False
        )
        plots_created.append(("Equity Curve", equity_path))
        logger.info(f"    Saved to: {equity_path}")
    except Exception as e:
        logger.warning(f"    Could not create equity curve: {e}")
    
    # 2. Drawdown chart
    logger.info("  - Creating drawdown chart...")
    drawdown_path = OUTPUT_DIR / "drawdown.png"
    try:
        plot_drawdown(
            equity_series,
            title=f"{result.strategy_name} - Drawdown",
            save_path=str(drawdown_path),
            show=False
        )
        plots_created.append(("Drawdown Chart", drawdown_path))
        logger.info(f"    Saved to: {drawdown_path}")
    except Exception as e:
        logger.warning(f"    Could not create drawdown chart: {e}")
    
    # 3. Monthly returns heatmap
    logger.info("  - Creating monthly returns heatmap...")
    heatmap_path = OUTPUT_DIR / "monthly_heatmap.png"
    try:
        plot_monthly_heatmap(
            equity_series,
            title=f"{result.strategy_name} - Monthly Returns",
            save_path=str(heatmap_path),
            show=False
        )
        plots_created.append(("Monthly Heatmap", heatmap_path))
        logger.info(f"    Saved to: {heatmap_path}")
    except Exception as e:
        logger.warning(f"    Could not create monthly heatmap: {e}")
    
    # 4. Returns distribution
    logger.info("  - Creating returns distribution...")
    dist_path = OUTPUT_DIR / "returns_distribution.png"
    try:
        if len(returns_series) > 0:
            plot_distribution(
                returns_series,
                title=f"{result.strategy_name} - Returns Distribution",
                save_path=str(dist_path),
                show=False
            )
            plots_created.append(("Returns Distribution", dist_path))
            logger.info(f"    Saved to: {dist_path}")
    except Exception as e:
        logger.warning(f"    Could not create distribution plot: {e}")
    
    # 5. Rolling Sharpe ratio
    logger.info("  - Creating rolling Sharpe ratio...")
    sharpe_path = OUTPUT_DIR / "rolling_sharpe.png"
    try:
        if len(returns_series) > 30:  # Need enough data for rolling window
            plot_rolling_sharpe(
                returns_series,
                window=30,
                title=f"{result.strategy_name} - Rolling Sharpe (30-period)",
                save_path=str(sharpe_path),
                show=False
            )
            plots_created.append(("Rolling Sharpe", sharpe_path))
            logger.info(f"    Saved to: {sharpe_path}")
    except Exception as e:
        logger.warning(f"    Could not create rolling Sharpe: {e}")
    
    logger.info(f"\n  Created {len(plots_created)} plots successfully")
    
    # Create comprehensive HTML report
    logger.info("\n[4/5] Creating comprehensive HTML report...")
    report_path = OUTPUT_DIR / "backtest_report.html"
    
    try:
        create_html_report(
            result,
            output_path=str(report_path),
            title=f"{result.strategy_name} Backtest Report",
            include_charts=True
        )
        logger.info(f"  HTML report saved to: {report_path}")
        logger.info(f"  Open in browser to view interactive report")
    except Exception as e:
        logger.warning(f"  Could not create HTML report: {e}")
    
    # Summary
    logger.info("\n[5/5] Summary")
    logger.info("=" * 70)
    logger.info(f"\nOutput Directory: {OUTPUT_DIR}")
    logger.info(f"\nGenerated Files:")
    
    for plot_name, plot_path in plots_created:
        logger.info(f"  - {plot_name}: {plot_path.name}")
    
    if report_path.exists():
        logger.info(f"  - HTML Report: {report_path.name}")
    
    logger.info(f"\nTotal files created: {len(plots_created) + (1 if report_path.exists() else 0)}")
    
    logger.info("\n" + "=" * 70)
    logger.info("PLOTTING COMPLETE")
    logger.info("=" * 70)
    
    logger.info(f"\nTip: Open {report_path} in your browser for an interactive report!")
    
    return result


if __name__ == "__main__":
    result = main()
