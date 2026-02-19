"""
Parameter Optimization Example

Purpose:
- Demonstrate parameter optimization workflows
- Show grid search and random search
- Custom scoring functions
- Optimization result analysis

Key Concepts:
- Using VectorizedEngine for speed
- Defining parameter grids
- Scoring functions (Sharpe, Sortino, custom)
- Analyzing optimization results
- Avoiding overfitting

Usage:
    python tests/usage/backtest/05_optimization.py

Output:
- Console output with optimization progress
- Best parameters and scores
- Top N parameter combinations
- Optimization results CSV

Note:
    This example uses VectorizedEngine for speed.
    For final validation, re-run best parameters with EventDrivenEngine.
"""

from pathlib import Path
import sys

# Add project root to path
project_root = Path(__file__).parent.parent.parent.parent
sys.path.insert(0, str(project_root))

import pandas as pd
from datetime import datetime
from apps.simulation.simulator import TradeSimulator
from apps.simulation.data import AccountInfoSimulator, SymbolInfoSimulator
from apps.simulation.utils import calculate_metrics_from_simulator
from data.strategies.trend_following import TrendFollowingStrategy
from apps.finance import ratios
from apps.mt5.client import MT5Client
from apps.sqlite.users import UserManager
from apps.utils.logger import logger
from itertools import product


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


def get_mt5_client():
    """Get a connected MT5 client."""
    creds = get_mt5_credentials()
    client = MT5Client()
    if not client.connect(creds["path"], creds["login"], creds["password"], creds["server"]):
        raise ConnectionError("Failed to connect to MT5")
    return client


def load_mt5_data(symbol: str, timeframe: str, date_from: datetime, date_to: datetime) -> pd.DataFrame:
    """Load historical data from MT5."""
    client = get_mt5_client()
    try:
        df = client.get_bars(symbol=symbol, timeframe=timeframe, date_from=date_from, date_to=date_to)
        if df is None or df.empty:
            raise ValueError("No data retrieved from MT5")
        return df
    finally:
        client.shutdown()


def sharpe_score(result) -> float:
    """Calculate Sharpe ratio as optimization score."""
    try:
        returns_series = result._get_returns_series()
        if len(returns_series) > 0:
            sharpe = ratios.sharpe_ratio(returns_series, risk_free_rate=0.0)
            return sharpe if not pd.isna(sharpe) else 0.0
        return 0.0
    except Exception:
        return 0.0


def sortino_score(result) -> float:
    """Calculate Sortino ratio as optimization score."""
    try:
        returns_series = result._get_returns_series()
        if len(returns_series) > 0:
            sortino = ratios.sortino_ratio(returns_series, risk_free_rate=0.0)
            return sortino if not pd.isna(sortino) else 0.0
        return 0.0
    except Exception:
        return 0.0


def custom_score(result) -> float:
    """
    Custom scoring function balancing return, risk, and drawdown.
    
    Formula: (Return% * 0.3) + (Sharpe * 0.4) - (MaxDD% * 0.3)
    """
    try:
        returns_series = result._get_returns_series()
        
        total_return = result.total_return_pct
        max_dd = abs(result.max_drawdown_pct)
        
        sharpe = 0.0
        if len(returns_series) > 0:
            sharpe = ratios.sharpe_ratio(returns_series, risk_free_rate=0.0)
            if pd.isna(sharpe):
                sharpe = 0.0
        
        # Weighted score
        score = (total_return * 0.3) + (sharpe * 0.4) - (max_dd * 0.3)
        return score
    except Exception:
        return 0.0


def grid_search(data, param_grid, scoring_func, verbose=True):
    """
    Perform grid search optimization.
    
    Args:
        data: OHLC DataFrame
        param_grid: Dict of parameter lists to test
        scoring_func: Function to score results
        verbose: Print progress
        
    Returns:
        List of (params, score, result) tuples
    """
    # Generate all parameter combinations
    param_names = list(param_grid.keys())
    param_values = list(param_grid.values())
    combinations = list(product(*param_values))
    
    total = len(combinations)
    logger.info(f"Testing {total} parameter combinations...")
    
    results = []
    
    for i, combo in enumerate(combinations, 1):
        # Create params dict
        params = dict(zip(param_names, combo))
        params['symbol'] = 'EURUSD'  # Add required symbol
        
        if verbose and i % 10 == 0:
            logger.info(f"  Progress: {i}/{total} ({i/total*100:.1f}%)")
        
        try:
            # Create strategy with these params
            strategy = TrendFollowingStrategy(params=params)

            # Initialize strategy
            strategy.on_init()

            # Calculate signals on a copy of the data
            data_copy = data.copy()
            data_copy = strategy.on_bar(data_copy)

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
                simulator_name="Optimization_EURUSD",
                mt5_client=mt5_client,
                account_info=account_info,
                symbols={'EURUSD': symbol_info},
            )

            # Run simulation
            simulator.run(
                data=data_copy,
                strategy=strategy,
                symbol='EURUSD',
                volume=0.1,
                verbose=False,
                save_db=False,
                engine_type="vectorised",
                commission_per_contract=7.0,
                slippage_points=1,
            )

            # Get results from simulator
            result = calculate_metrics_from_simulator(simulator)

            # Calculate score
            score = scoring_func(result)

            results.append((params, score, result))

            # Cleanup
            mt5_client.shutdown()

        except Exception as e:
            if verbose:
                logger.warning(f"  Error with params {params}: {e}")
            results.append((params, 0.0, None))
    
    # Sort by score (descending)
    results.sort(key=lambda x: x[1], reverse=True)

    return results


def print_optimization_results(results, top_n=10):
    """Print formatted optimization results."""
    logger.info("\n" + "=" * 70)
    logger.info("OPTIMIZATION RESULTS")
    logger.info("=" * 70)
    
    logger.info(f"\nTotal combinations tested: {len(results)}")
    
    if len(results) > 0:
        best_params, best_score, best_result = results[0]
        
        logger.info(f"\nBest Score: {best_score:.4f}")
        logger.info(f"Best Parameters:")
        for key, value in best_params.items():
            if key != 'symbol':
                logger.info(f"  {key}: {value}")
        
        if best_result:
            logger.info(f"\nBest Result Metrics:")
            logger.info(f"  Total Return: {best_result.total_return_pct:.2f}%")
            logger.info(f"  Max Drawdown: {best_result.max_drawdown_pct:.2f}%")
            logger.info(f"  Win Rate: {best_result.win_rate:.2f}%")
            logger.info(f"  Profit Factor: {best_result.profit_factor:.2f}")
            logger.info(f"  Total Trades: {best_result.total_trades}")
        
        logger.info(f"\nTop {min(top_n, len(results))} Results:")
        logger.info(f"{'Rank':<6} {'Score':<10} {'Parameters'}")
        logger.info("-" * 70)
        
        for i, (params, score, result) in enumerate(results[:top_n], 1):
            param_str = ", ".join([f"{k}={v}" for k, v in params.items() if k != 'symbol'])
            logger.info(f"{i:<6} {score:<10.4f} {param_str}")
    
    logger.info("\n" + "=" * 70)


def save_optimization_results(results, filename):
    """Save optimization results to CSV."""
    rows = []
    for params, score, result in results:
        row = params.copy()
        row['score'] = score
        
        if result:
            row['total_return_pct'] = result.total_return_pct
            row['max_drawdown_pct'] = result.max_drawdown_pct
            row['win_rate'] = result.win_rate
            row['profit_factor'] = result.profit_factor
            row['total_trades'] = result.total_trades
        
        rows.append(row)
    
    df = pd.DataFrame(rows)
    df.to_csv(filename, index=False)
    logger.info(f"\nResults saved to: {filename}")


def main():
    """Main execution function."""
    logger.info("=" * 70)
    logger.info("PARAMETER OPTIMIZATION EXAMPLE")
    logger.info("=" * 70)
    
    # Load data
    logger.info("\n[1/4] Loading data from MT5...")
    date_from = datetime(2025, 1, 1)
    date_to = datetime(2025, 12, 31)
    data = load_mt5_data('EURUSD', 'H1', date_from, date_to)
    logger.info(f"Loaded {len(data)} bars")
    
    # Define parameter grid
    logger.info("\n[2/4] Defining parameter grid...")
    param_grid = {
        'fast_period': [10, 15, 20, 25, 30],
        'slow_period': [40, 50, 60],
        'filter_period': [150, 200, 250]
    }
    
    total_combinations = 1
    for values in param_grid.values():
        total_combinations *= len(values)
    
    logger.info(f"Parameter grid:")
    for key, values in param_grid.items():
        logger.info(f"  {key}: {values}")
    logger.info(f"Total combinations: {total_combinations}")
    
    # Run optimization with different scoring functions
    logger.info("\n[3/4] Running optimizations...")
    
    # Optimization 1: Sharpe Ratio
    logger.info("\n--- Optimization 1: Sharpe Ratio ---")
    sharpe_results = grid_search(data, param_grid, sharpe_score, verbose=True)
    print_optimization_results(sharpe_results, top_n=5)
    
    sharpe_path = OUTPUT_DIR / "optimization_sharpe.csv"
    save_optimization_results(sharpe_results, sharpe_path)
    
    # Optimization 2: Sortino Ratio
    logger.info("\n--- Optimization 2: Sortino Ratio ---")
    sortino_results = grid_search(data, param_grid, sortino_score, verbose=True)
    print_optimization_results(sortino_results, top_n=5)
    
    sortino_path = OUTPUT_DIR / "optimization_sortino.csv"
    save_optimization_results(sortino_results, sortino_path)
    
    # Optimization 3: Custom Score
    logger.info("\n--- Optimization 3: Custom Balanced Score ---")
    custom_results = grid_search(data, param_grid, custom_score, verbose=True)
    print_optimization_results(custom_results, top_n=5)
    
    custom_path = OUTPUT_DIR / "optimization_custom.csv"
    save_optimization_results(custom_results, custom_path)
    
    # Validate best result with Event-Driven Engine
    logger.info("\n[4/4] Validating best parameters with Event-Driven Engine...")

    best_params, best_score, _ = sharpe_results[0]

    logger.info(f"\nRe-running best parameters with high-fidelity engine...")
    logger.info(f"Parameters: {best_params}")

    strategy = TrendFollowingStrategy(params=best_params)

    # Initialize strategy
    strategy.on_init()

    # Calculate signals
    data_validated = data.copy()
    data_validated = strategy.on_bar(data_validated)

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
        simulator_name="Validation_EURUSD",
        mt5_client=mt5_client,
        account_info=account_info,
        symbols={'EURUSD': symbol_info},
    )

    # Run simulation with event-driven engine
    simulator.run(
        data=data_validated,
        strategy=strategy,
        symbol='EURUSD',
        volume=0.1,
        verbose=False,
        save_db=False,
        engine_type="event_driven",
        commission_per_contract=7.0,
        slippage_points=1,
    )

    # Get results from simulator
    validated_result = calculate_metrics_from_simulator(simulator)

    logger.info(f"\nValidation Results:")
    logger.info(f"  Total Return: {validated_result.total_return_pct:.2f}%")
    logger.info(f"  Max Drawdown: {validated_result.max_drawdown_pct:.2f}%")
    logger.info(f"  Win Rate: {validated_result.win_rate:.2f}%")
    logger.info(f"  Profit Factor: {validated_result.profit_factor:.2f}")
    logger.info(f"  Total Trades: {validated_result.total_trades}")

    # Cleanup
    mt5_client.shutdown()
    
    # Summary
    logger.info("\n" + "=" * 70)
    logger.info("OPTIMIZATION COMPLETE")
    logger.info("=" * 70)
    
    logger.info(f"\nBest Parameters (Sharpe):")
    for key, value in best_params.items():
        if key != 'symbol':
            logger.info(f"  {key}: {value}")
    
    logger.info(f"\nOptimization files saved:")
    logger.info(f"  - Sharpe: {sharpe_path.name}")
    logger.info(f"  - Sortino: {sortino_path.name}")
    logger.info(f"  - Custom: {custom_path.name}")
    
    logger.info("\n" + "=" * 70)
    
    return validated_result


if __name__ == "__main__":
    result = main()

