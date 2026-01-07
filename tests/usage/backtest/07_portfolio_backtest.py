"""
Portfolio Backtest Example

Purpose:
- Demonstrate multi-asset portfolio backtesting
- Show portfolio-level risk management
- Calculate portfolio metrics and correlations
- Analyze diversification benefits

Key Concepts:
- Using apps.backtest.portfolio module
- Multi-strategy backtesting
- Portfolio-level metrics
- Correlation analysis

Usage:
    python tests/usage/backtest/07_portfolio_backtest.py

Output:
- Console output with portfolio metrics
- Individual asset performance
- Portfolio-level statistics
- Correlation matrix
"""

from pathlib import Path
import sys

# Add project root to path
project_root = Path(__file__).parent.parent.parent.parent
sys.path.insert(0, str(project_root))

import pandas as pd
from datetime import datetime
from apps.backtest import EventDrivenEngine
from apps.backtest.portfolio import (
    AssetClass,
    AssetSpecification,
    PortfolioEngine,
    PortfolioStrategy,
)
from data.strategies.trend_following import TrendFollowingStrategy
from apps.finance import ratios, metrics
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
    logger.info("PORTFOLIO BACKTEST EXAMPLE")
    logger.info("=" * 70)
    
    # Step 1: Define portfolio assets
    logger.info("\n[1/5] Defining portfolio assets...")
    
    symbols = ['EURUSD', 'GBPUSD', 'USDJPY']
    logger.info(f"Portfolio symbols: {symbols}")
    
    # Create asset specifications
    asset_specs = {}
    for symbol in symbols:
        asset_specs[symbol] = AssetSpecification(
            symbol=symbol,
            asset_class=AssetClass.FOREX,
            contract_size=100000,
            point=0.0001 if symbol != 'USDJPY' else 0.01,
            commission=7.0,
            margin_requirement=0.01,
            max_position_pct=0.33,  # Max 33% per asset
            description=f"{symbol} Forex Pair"
        )
    
    logger.info(f"Created {len(asset_specs)} asset specifications")
    
    # Step 2: Load data for each asset from MT5
    logger.info("\n[2/5] Loading data from MT5 for each asset...")
    
    date_from = datetime(2025, 1, 1)
    date_to = datetime(2025, 12, 31)
    
    data_dict = {}
    for symbol in symbols:
        data = load_mt5_data(symbol, 'H1', date_from, date_to)
        data_dict[symbol] = data
        logger.info(f"  {symbol}: {len(data)} bars from {data.index[0]} to {data.index[-1]}")
    
    # Step 3: Create strategies for each asset
    logger.info("\n[3/5] Creating strategies...")
    
    strategies = {}
    for symbol in symbols:
        # Use different parameters for each symbol for diversification
        params = {
            'symbol': symbol,
            'fast_period': 20,
            'slow_period': 50,
            'filter_period': 200
        }
        
        strategies[symbol] = TrendFollowingStrategy(params=params)
        logger.info(f"  {symbol}: TrendFollowingStrategy (fast=20, slow=50, filter=200)")
    
    # Step 4: Create portfolio strategy
    logger.info("\n[4/5] Creating portfolio strategy...")
    
    portfolio_strategy = PortfolioStrategy(
        name="Multi-Currency Trend Following",
        strategies=strategies,
        asset_specs=asset_specs,
        data=data_dict,
        max_total_exposure=1.0,  # 100% total exposure
        max_correlated_exposure=0.6,  # Max 60% in correlated assets
        rebalance_frequency='monthly'
    )
    
    # Validate portfolio
    portfolio_strategy.validate()
    logger.info("Portfolio strategy validated successfully")
    
    # Step 5: Run portfolio backtest
    logger.info("\n[5/5] Running portfolio backtest...")
    logger.info("=" * 70)
    
    portfolio_engine = PortfolioEngine(
        portfolio_strategy=portfolio_strategy,
        initial_balance=30000.0,  # $30k for 3 assets
        config={
            'commission': 7.0,
            'slippage_points': 1.0,
            'timeframe': 'H1'
        }
    )
    
    portfolio_result = portfolio_engine.run()
    
    logger.info("\nPortfolio backtest completed!")
    
    # Display results
    logger.info("\n" + "=" * 70)
    logger.info("PORTFOLIO RESULTS")
    logger.info("=" * 70)
    
    # Portfolio summary
    summary = portfolio_result.get_portfolio_summary()
    
    logger.info(f"\nPortfolio: {portfolio_result.portfolio_name}")
    logger.info(f"Period: {portfolio_result.start_date} to {portfolio_result.end_date}")
    logger.info(f"Initial Balance: ${portfolio_result.initial_balance:,.2f}")
    logger.info(f"Final Balance: ${portfolio_result.final_balance:,.2f}")
    
    logger.info(f"\n--- Portfolio Performance ---")
    logger.info(f"Total Return: ${summary['total_return']:,.2f} ({summary['total_return_pct']:.2f}%)")
    logger.info(f"Max Drawdown: {summary['max_drawdown_pct']:.2f}%")
    logger.info(f"Sharpe Ratio: {summary.get('sharpe_ratio', 0):.2f}")
    logger.info(f"Total Trades: {summary['total_trades']}")
    
    # Individual asset performance
    logger.info(f"\n--- Individual Asset Performance ---")
    
    for symbol, result in portfolio_result.asset_results.items():
        logger.info(f"\n{symbol}:")
        logger.info(f"  Return: {result.total_return_pct:.2f}%")
        logger.info(f"  Max DD: {result.max_drawdown_pct:.2f}%")
        logger.info(f"  Trades: {result.total_trades}")
        logger.info(f"  Win Rate: {result.win_rate:.2f}%")
        logger.info(f"  Profit Factor: {result.profit_factor:.2f}")
    
    # Asset contributions
    logger.info(f"\n--- Asset Contributions to Portfolio ---")
    
    contributions = portfolio_result.get_asset_contributions()
    for symbol, contrib in contributions.items():
        logger.info(f"\n{symbol}:")
        logger.info(f"  Contribution to Return: {contrib.get('return_contribution', 0):.2f}%")
        logger.info(f"  Weight: {contrib.get('weight', 0):.2f}%")
    
    # Correlation analysis
    logger.info(f"\n--- Correlation Analysis ---")
    
    # Calculate returns correlation
    returns_data = {}
    for symbol, result in portfolio_result.asset_results.items():
        returns_series = result._get_returns_series()
        if len(returns_series) > 0:
            returns_data[symbol] = returns_series
    
    if len(returns_data) > 1:
        returns_df = pd.DataFrame(returns_data)
        correlation_matrix = returns_df.corr()
        
        logger.info("\nReturns Correlation Matrix:")
        logger.info(correlation_matrix.to_string())
        
        # Average correlation
        avg_corr = correlation_matrix.values[correlation_matrix.values != 1.0].mean()
        logger.info(f"\nAverage Correlation: {avg_corr:.3f}")
        
        if avg_corr < 0.3:
            logger.info("Assessment: Good diversification (low correlation)")
        elif avg_corr < 0.6:
            logger.info("Assessment: Moderate diversification")
        else:
            logger.info("Assessment: Poor diversification (high correlation)")
    
    # Diversification benefit
    logger.info(f"\n--- Diversification Benefit ---")
    
    # Compare portfolio Sharpe to average individual Sharpe
    individual_sharpes = []
    for symbol, result in portfolio_result.asset_results.items():
        returns_series = result._get_returns_series()
        if len(returns_series) > 0:
            sharpe = ratios.sharpe_ratio(returns_series, risk_free_rate=0.0)
            if not pd.isna(sharpe):
                individual_sharpes.append(sharpe)
    
    if len(individual_sharpes) > 0:
        avg_individual_sharpe = sum(individual_sharpes) / len(individual_sharpes)
        portfolio_sharpe = summary.get('sharpe_ratio', 0)
        
        logger.info(f"Average Individual Sharpe: {avg_individual_sharpe:.3f}")
        logger.info(f"Portfolio Sharpe: {portfolio_sharpe:.3f}")
        
        if portfolio_sharpe > avg_individual_sharpe:
            improvement = ((portfolio_sharpe - avg_individual_sharpe) / avg_individual_sharpe * 100)
            logger.info(f"Diversification Benefit: +{improvement:.1f}% improvement in Sharpe")
        else:
            logger.info("Diversification Benefit: No improvement (consider strategy selection)")
    
    # Summary
    logger.info("\n" + "=" * 70)
    logger.info("PORTFOLIO BACKTEST COMPLETE")
    logger.info("=" * 70)
    
    logger.info(f"\nKey Findings:")
    logger.info(f"  - Portfolio return: {summary['total_return_pct']:.2f}%")
    logger.info(f"  - Portfolio max drawdown: {summary['max_drawdown_pct']:.2f}%")
    logger.info(f"  - Number of assets: {len(symbols)}")
    logger.info(f"  - Total trades across portfolio: {summary['total_trades']}")
    
    if len(returns_data) > 1:
        logger.info(f"  - Average correlation: {avg_corr:.3f}")
    
    logger.info("\n" + "=" * 70)
    
    return portfolio_result


if __name__ == "__main__":
    result = main()
