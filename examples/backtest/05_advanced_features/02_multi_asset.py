"""Example 02: Multi-Asset Portfolio Trading

This example demonstrates portfolio backtesting with multiple instruments using PortfolioEngine.

Topics covered:
- PortfolioEngine and PortfolioStrategy usage
- Trading multiple currency pairs simultaneously
- Portfolio-level statistics
- Correlation analysis
- Risk distribution

Author: HaruQuant Development Team
Created: 2025-12-03
Updated: 2026-02-06 - Updated to use apps.simulation.portfolio
"""

import sys
from pathlib import Path

# Add project root to path
project_root = Path(__file__).resolve().parents[4]
sys.path.insert(0, str(project_root))

import pandas as pd  # noqa: E402
import numpy as np  # noqa: E402
from datetime import datetime  # noqa: E402

from data.strategies.trend_following import TrendFollowingStrategy  # noqa: E402
from apps.simulation.portfolio import (  # noqa: E402
    PortfolioEngine,
    PortfolioStrategy,
)
from apps.simulation.data import SymbolInfoSimulator  # noqa: E402
from apps.utils.logger import logger  # noqa: E402
from apps.mt5 import MT5Client  # noqa: E402
from apps.sqlite.users import UserManager  # noqa: E402


def get_mt5_credentials():
    """Get MT5 credentials from the database."""
    creds = UserManager().get_mt5_credentials()
    if not creds:
        logger.error("No default broker credentials found")
        sys.exit(1)
    return creds


def load_mt5_data(symbol: str, timeframe: str, count: int = 500) -> pd.DataFrame:
    """Load historical data from MT5."""
    try:
        creds = get_mt5_credentials()

        # Initialize MT5 client (needed for Option 1)
        client = MT5Client()
        connected = client.connect(
            login=creds["login"],
            password=creds["password"],
            server=creds["server"],
            path=creds["path"]
        )

        if not connected:
            logger.error("Failed to connect to MT5. Please ensure MT5 terminal is running.")
            return

        # Get recent data
        date_to = datetime.now()
        df = client.get_bars(symbol=symbol, timeframe=timeframe, count=count)

        if df.empty:
            raise ValueError("No data retrieved from MT5")
        return df
    except Exception as e:
        logger.warning(f"Failed to load MT5 data for {symbol}: {e}")
        return None



def example1_basic_multi_asset():
    """Basic multi-asset portfolio backtest."""
    print("\n" + "=" * 70)
    print("Example 1: Basic Multi-Asset Portfolio")
    print("=" * 70)

    # Load data for multiple symbols
    symbols = ["EURUSD", "GBPUSD", "USDJPY"]
    print(f"\nLoading data for {len(symbols)} symbols from MT5...")

    datasets = {}
    for symbol in symbols:
        data = load_mt5_data(symbol, timeframe="H1", count=500)
        if data is not None and len(data) > 0:
            datasets[symbol] = data
            print(f"  {symbol}: {len(data):,} bars (from MT5)")
        else:
            logger.warning(f"Failed to load data for {symbol}")

    if len(datasets) == 0:
        print("\nNo data loaded. Exiting...")
        return

    # Create symbol specs using SymbolInfoSimulator
    print(f"\nCreating symbol specifications...")
    symbol_specs = {}
    for symbol in datasets.keys():
        symbol_specs[symbol] = SymbolInfoSimulator.from_mt5_symbol(symbol)
        print(f"  {symbol}: Created SymbolInfoSimulator")

    # Build strategies and calculate indicators/signals
    print(f"\nCreating strategies and calculating signals...")
    strategies = {}
    for symbol in datasets.keys():
        strat = TrendFollowingStrategy(
            params={
                "symbol": symbol,
                "fast_period": 20,
                "slow_period": 50,
                "filter_period": 200
            }
        )
        strat.on_init()
        datasets[symbol] = strat.on_bar(datasets[symbol])
        strategies[symbol] = strat
        print(f"  {symbol}: Signals calculated")

    # Create portfolio strategy
    print(f"\nCreating portfolio strategy...")
    portfolio_strategy = PortfolioStrategy(
        strategies=strategies,
        symbol_specs=symbol_specs,
        data=datasets,
        max_total_exposure=1.0,  # 100% total exposure
        max_correlated_exposure=0.6,  # Max 60% in correlated assets
        allocation_method='equal_weight'  # or 'risk_parity'
    )

    # Validate portfolio
    portfolio_strategy.validate()
    print("Portfolio strategy validated successfully")

    # Run portfolio backtest
    print(f"\nRunning portfolio backtest on {len(datasets)} instruments...")
    portfolio_engine = PortfolioEngine(
        portfolio_strategy=portfolio_strategy,
        initial_balance=30000.0,
        config={
            'portfolio_name': 'Multi-Asset MA Portfolio',
            'volume': 0.3,
            'commission': 7.0,
            'slippage': 0.5,
            'verbose': False
        }
    )

    results = portfolio_engine.run(synchronize_data=True, sync_method='ffill')

    print("\n" + "-" * 70)
    print("PORTFOLIO RESULTS")
    print("-" * 70)

    # Portfolio-level stats
    summary = results.get_portfolio_summary()
    print(f"\nPortfolio Performance:")
    print(f"  Initial Balance: ${summary['initial_balance']:,.2f}")
    print(f"  Final Balance: ${summary['final_balance']:,.2f}")
    print(f"  Total Return: {summary['total_return_pct']:.2f}%")
    print(f"  Max Drawdown: {summary['max_drawdown_pct']:.2f}%")
    print(f"  Sharpe Ratio: {summary.get('sharpe_ratio', 0):.2f}")
    print(f"  Total Trades: {summary['total_trades']}")
    print(f"  Win Rate: {summary['win_rate']:.2f}%")
    print(f"  Profit Factor: {summary['profit_factor']:.2f}")

    # Individual instrument stats
    print(f"\nIndividual Instruments:")
    if results.asset_results:
        for symbol, result in results.asset_results.items():
            print(f"\n  {symbol}:")
            print(f"    Return: {result.total_return_pct:.2f}%")
            print(f"    Trades: {result.total_trades}")
            print(f"    Win Rate: {result.win_rate:.2f}%")
            print(f"    Profit Factor: {result.profit_factor:.2f}")
    else:
        print("  No per-asset results available.")

    # Asset contributions
    print(f"\n--- Asset Contributions to Portfolio ---")
    contributions = results.get_asset_contributions()
    for symbol, contrib in contributions.items():
        print(f"\n{symbol}:")
        print(f"  Contribution: {contrib['contribution_pct']:.2f}%")
        print(f"  Total Return: ${contrib['total_return']:,.2f}")
        print(f"  Sharpe Ratio: {contrib['sharpe_ratio']:.2f}")


def example2_correlation_analysis():
    """Analyze correlation between instruments."""
    print("\n" + "=" * 70)
    print("Example 2: Correlation Analysis")
    print("=" * 70)

    symbols = ["EURUSD", "GBPUSD", "EURGBP"]
    print(f"\nLoading data for correlation analysis from MT5...")

    datasets = {}
    for symbol in symbols:
        data = load_mt5_data(symbol, timeframe="H1", count=500)
        if data is not None and len(data) > 0:
            datasets[symbol] = data
            print(f"  {symbol}: {len(data):,} bars (from MT5)")
        else:
            logger.warning(f"Failed to load data for {symbol}")

    if len(datasets) < 2:
        print("Need at least 2 symbols for correlation. Skipping...")
        return

    # Calculate returns for each symbol
    returns = {}
    for symbol, data in datasets.items():
        returns[symbol] = data['close'].pct_change().dropna()

    # Align returns (same timestamps)
    returns_df = pd.DataFrame(returns)
    returns_df = returns_df.dropna()

    # Calculate correlation matrix
    corr_matrix = returns_df.corr()

    print(f"\nCorrelation Matrix:")
    print(corr_matrix)

    print(f"\nInterpretation:")
    print("  1.0  = Perfect positive correlation")
    print("  0.0  = No correlation")
    print(" -1.0  = Perfect negative correlation")

    print(f"\nDiversification Benefits:")
    for i, sym1 in enumerate(symbols):
        for sym2 in symbols[i+1:]:
            if sym1 in corr_matrix.columns and sym2 in corr_matrix.columns:
                corr = corr_matrix.loc[sym1, sym2]
                if abs(corr) < 0.5:
                    print(f"  {sym1}-{sym2}: Low correlation ({corr:.2f}) - Good diversification")
                elif abs(corr) > 0.8:
                    print(f"  {sym1}-{sym2}: High correlation ({corr:.2f}) - Limited diversification")
                else:
                    print(f"  {sym1}-{sym2}: Moderate correlation ({corr:.2f})")

    # Now demonstrate using PortfolioBacktestResult.get_correlation_matrix()
    print(f"\n--- Portfolio Engine Correlation Analysis ---")
    print(f"Creating portfolio and running backtest to calculate trade correlations...")

    # Create symbol specs
    symbol_specs = {
        symbol: SymbolInfoSimulator.from_mt5_symbol(symbol)
        for symbol in datasets.keys()
    }

    # Build strategies and calculate indicators/signals
    strategies = {}
    for symbol in datasets.keys():
        strat = TrendFollowingStrategy(
            params={
                "symbol": symbol,
                "fast_period": 20,
                "slow_period": 50,
            }
        )
        strat.on_init()
        datasets[symbol] = strat.on_bar(datasets[symbol])
        strategies[symbol] = strat

    # Create portfolio strategy
    portfolio_strategy = PortfolioStrategy(
        strategies=strategies,
        symbol_specs=symbol_specs,
        data=datasets,
        allocation_method='equal_weight'
    )

    # Run backtest
    portfolio_engine = PortfolioEngine(
        portfolio_strategy=portfolio_strategy,
        initial_balance=20000.0,
        config={'volume': 0.3, 'verbose': False}
    )

    result = portfolio_engine.run(synchronize_data=True)

    # Get correlation matrix from backtest results
    trade_corr_matrix = result.get_correlation_matrix()

    if not trade_corr_matrix.empty:
        print(f"\nTrade Returns Correlation Matrix:")
        print(trade_corr_matrix)

        # Average correlation (excluding diagonal)
        mask = np.ones(trade_corr_matrix.shape, dtype=bool)
        np.fill_diagonal(mask, False)
        avg_corr = trade_corr_matrix.values[mask].mean()

        print(f"\nAverage Trade Correlation: {avg_corr:.3f}")

        if avg_corr < 0.3:
            print("Assessment: Good diversification (low correlation)")
        elif avg_corr < 0.6:
            print("Assessment: Moderate diversification")
        else:
            print("Assessment: Poor diversification (high correlation)")
    else:
        print("\nNot enough trades to calculate correlation matrix")


def example3_best_practices():
    """Best practices for multi-asset trading."""
    print("\n" + "=" * 70)
    print("Example 3: Best Practices")
    print("=" * 70)

    print("\n1. Symbol Selection:")
    print("   - Choose low-correlated instruments")
    print("   - Mix different asset classes")
    print("   - Consider market hours overlap")
    print("   - Don't trade highly correlated pairs (e.g., EURUSD + GBPUSD have ~0.7-0.9 correlation)")

    print("\n2. Capital Allocation:")
    print("   - Equal weight: 33% each for 3 instruments (allocation_method='equal_weight')")
    print("   - Risk parity: Allocate by inverse volatility (allocation_method='risk_parity')")
    print("   - Strategic: Adjust allocations based on performance")

    print("\n3. Risk Management:")
    print("   - Set portfolio-level max drawdown limits")
    print("   - Limit per-instrument exposure (max_total_exposure parameter)")
    print("   - Monitor correlation changes over time")
    print("   - Use max_correlated_exposure to limit correlated positions")

    print("\n4. Performance:")
    print("   - PortfolioEngine coordinates instruments on a unified timeline")
    print("   - Data synchronization (ffill/drop/interpolate methods)")
    print("   - Memory usage scales linearly with number of symbols")
    print("   - Expected speed: N symbols ~ Nx time of single symbol")

    print("\n5. Common Use Cases:")
    print("   - Currency portfolio (EUR, GBP, JPY pairs)")
    print("   - Multi-market strategies (Forex + Indices + Commodities)")
    print("   - Diversification strategies (low-correlation instruments)")
    print("   - Sector rotation (trading across different markets)")

    print("\n6. API Usage:")
    print("   # Create symbol specs")
    print("   symbol_specs = {")
    print("       symbol: SymbolInfoSimulator.from_mt5_symbol(symbol)")
    print("       for symbol in ['EURUSD', 'GBPUSD', 'USDJPY']")
    print("   }")
    print("")
    print("   # Create portfolio strategy")
    print("   portfolio_strategy = PortfolioStrategy(")
    print("       strategies={sym: strategy for sym in symbols},")
    print("       symbol_specs=symbol_specs,")
    print("       data={sym: df for sym, df in data.items()},")
    print("       allocation_method='equal_weight'  # or 'risk_parity'")
    print("   )")
    print("")
    print("   # Run backtest")
    print("   engine = PortfolioEngine(portfolio_strategy, initial_balance=30000)")
    print("   result = engine.run(synchronize_data=True)")


def main():
    """Run all examples."""
    print("\n" + "=" * 70)
    print("MULTI-ASSET PORTFOLIO EXAMPLES")
    print("=" * 70)

    try:
        example1_basic_multi_asset()
        example2_correlation_analysis()
        example3_best_practices()

        print("\n" + "=" * 70)
        print("ALL EXAMPLES COMPLETED")
        print("=" * 70)

        print("\nKey Takeaways:")
        print("1. PortfolioEngine coordinates multiple instruments with synchronized data")
        print("2. Diversification reduces portfolio risk (aim for low correlation)")
        print("3. Choose allocation method: equal_weight or risk_parity")
        print("4. Monitor portfolio-level metrics (Sharpe ratio, max drawdown, correlations)")
        print("5. Use SymbolInfoSimulator.from_mt5_symbol() for automatic symbol specs")

    except Exception as e:
        logger.error(f"Error running examples: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    main()

