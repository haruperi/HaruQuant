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
"""

import sys
from pathlib import Path

# Add project root to path
project_root = Path(__file__).resolve().parents[4]
sys.path.insert(0, str(project_root))

import pandas as pd  # noqa: E402

from data.strategies.trend_following import TrendFollowingStrategy  # noqa: E402
from apps.backtest.portfolio import (  # noqa: E402
    AssetClass,
    AssetSpecification,
    PortfolioEngine,
    PortfolioStrategy,
)
from apps.logger import logger  # noqa: E402
from apps.utils.data_getters import load_mt5  # noqa: E402


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
        try:
            data = load_mt5(symbol, timeframe="H1", count=500)
            if data is not None and len(data) > 0:
                datasets[symbol] = data
                print(f"  {symbol}: {len(data):,} bars")
        except Exception as e:
            print(f"  {symbol}: Failed to load - {e}")

    if len(datasets) == 0:
        print("\nNo data loaded. Exiting...")
        return

    # Build portfolio specs and strategies
    asset_specs = {
        symbol: AssetSpecification(
            symbol=symbol,
            asset_class=AssetClass.FOREX,
            contract_size=100000,
            point=0.0001 if symbol != "USDJPY" else 0.01,
            commission=7,
            leverage=400,
            margin_requirement=0.0025,
            max_position_pct=0.34,
            description=f"{symbol} Forex Pair",
        )
        for symbol in datasets.keys()
    }

    strategies = {
        symbol: TrendFollowingStrategy(
            params={"symbol": symbol, "fast_period": 20, "slow_period": 50, "filter_period": 200}
        )
        for symbol in datasets.keys()
    }

    portfolio_strategy = PortfolioStrategy(
        name="Multi-Asset MA Portfolio",
        strategies=strategies,
        asset_specs=asset_specs,
        data=datasets,
        max_total_exposure=1.0,
        max_correlated_exposure=0.6,
        rebalance_frequency="monthly",
    )

    # Run portfolio backtest
    print(f"\nRunning portfolio backtest on {len(datasets)} instruments...")
    portfolio_engine = PortfolioEngine(
        portfolio_strategy=portfolio_strategy,
        initial_balance=30000.0,
        engines={},
        config={"commission": 0.0, "timeframe": "H1"},
    )
    results = portfolio_engine.run()

    print("\n" + "-" * 70)
    print("PORTFOLIO RESULTS")
    print("-" * 70)

    # Portfolio-level stats
    summary = results.get_portfolio_summary()
    print(f"\nPortfolio Performance:")
    print(f"  Total Return: {summary.get('total_return_pct', 0):.2f}%")
    print(f"  Max Drawdown: {summary.get('max_drawdown_pct', 0):.2f}%")
    print(f"  Assets Traded: {summary.get('assets_traded', 0)}")

    # Individual instrument stats
    print(f"\nIndividual Instruments:")
    if results.asset_results:
        for symbol, result in results.asset_results.items():
            print(f"\n  {symbol}:")
            print(f"    Return: {getattr(result, 'total_return_pct', 0):.2f}%")
            print(f"    Trades: {getattr(result, 'total_trades', 0)}")
    else:
        print("  No per-asset results available in this example.")


def example2_correlation_analysis():
    """Analyze correlation between instruments."""
    print("\n" + "=" * 70)
    print("Example 2: Correlation Analysis")
    print("=" * 70)

    symbols = ["EURUSD", "GBPUSD", "EURGBP"]
    print(f"\nLoading data for correlation analysis from MT5...")
    
    datasets = {}
    for symbol in symbols:
        try:
            data = load_mt5(symbol, timeframe="H1", count=500)
            if data is not None and len(data) > 0:
                datasets[symbol] = data
        except:
            pass

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


def example3_best_practices():
    """Best practices for multi-asset trading."""
    print("\n" + "=" * 70)
    print("Example 3: Best Practices")
    print("=" * 70)

    print("\n1. Symbol Selection:")
    print("   - Choose low-correlated instruments")
    print("   - Mix different asset classes")
    print("   - Consider market hours overlap")
    print("   - Don't trade highly correlated pairs")

    print("\n2. Capital Allocation:")
    print("   - Equal weight: 33% each for 3 instruments")
    print("   - Risk parity: Allocate by inverse volatility")
    print("   - Strategic: More to better performers")

    print("\n3. Risk Management:")
    print("   - Set portfolio-level max drawdown")
    print("   - Limit per-instrument exposure")
    print("   - Monitor correlation changes")
    print("   - Rebalance periodically")

    print("\n4. Performance:")
    print("   - PortfolioEngine coordinates instruments on a unified timeline")
    print("   - Slower than single-instrument backtest")
    print("   - Memory usage increases with instruments")

    print("\n5. Common Use Cases:")
    print("   - Currency portfolio (EUR, GBP, JPY pairs)")
    print("   - Multi-market strategies")
    print("   - Diversification strategies")
    print("   - Sector rotation")


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
        print("1. PortfolioEngine coordinates multiple instruments")
        print("2. Diversification reduces portfolio risk")
        print("3. Choose low-correlated instruments")
        print("4. Monitor portfolio-level metrics")


    except Exception as e:
        logger.error(f"Error running examples: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    main()
