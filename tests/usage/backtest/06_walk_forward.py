"""
Walk-Forward Analysis Example

Purpose:
- Demonstrate walk-forward optimization for robust validation
- Show in-sample vs out-of-sample testing
- Prevent overfitting through rolling windows
- Analyze parameter stability over time

Key Concepts:
- Out-of-sample validation
- Rolling window optimization
- Parameter stability
- Realistic performance expectations

Usage:
    python tests/usage/backtest/06_walk_forward.py

Output:
- Console output with walk-forward results
- Window-by-window performance breakdown
- CSV file with all window results
- Stability analysis

Note:
    Walk-forward analysis is the gold standard for avoiding overfitting.
    It simulates how parameters would be adapted in real trading.
"""

from pathlib import Path
import sys

# Add project root to path
project_root = Path(__file__).parent.parent.parent.parent
sys.path.insert(0, str(project_root))

import pandas as pd
from datetime import datetime
from apps.backtest import VectorizedEngine, EventDrivenEngine
from data.strategies.trend_following import TrendFollowingStrategy
from apps.finance import ratios
from apps.mt5.client import MT5Client
from apps.sqlite.users import UserManager
from apps.logger import logger
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


def optimize_on_data(data, param_grid):
    """
    Run optimization on given data.
    
    Returns:
        (best_params, best_score)
    """
    param_names = list(param_grid.keys())
    param_values = list(param_grid.values())
    combinations = list(product(*param_values))
    
    best_score = float('-inf')
    best_params = None
    
    for combo in combinations:
        params = dict(zip(param_names, combo))
        params['symbol'] = 'EURUSD'
        
        try:
            strategy = TrendFollowingStrategy(params=params)
            engine = VectorizedEngine(
                strategy=strategy,
                data=data.copy(),
                initial_balance=10000.0,
                commission=7.0,
                slippage_points=1.0,
                timeframe='H1'
            )
            
            result = engine.run()
            score = sharpe_score(result)
            
            if score > best_score:
                best_score = score
                best_params = params
                
        except Exception:
            continue
    
    return best_params, best_score


def test_on_data(data, params):
    """
    Test parameters on given data.
    
    Returns:
        BacktestResult
    """
    strategy = TrendFollowingStrategy(params=params)
    engine = VectorizedEngine(
        strategy=strategy,
        data=data.copy(),
        initial_balance=10000.0,
        commission=7.0,
        slippage_points=1.0,
        timeframe='H1'
    )
    
    return engine.run()


def walk_forward_analysis(data, param_grid, train_size=500, test_size=100, verbose=True):
    """
    Perform walk-forward analysis.
    
    Args:
        data: Full OHLC DataFrame
        param_grid: Parameter grid to optimize
        train_size: Number of bars for training (in-sample)
        test_size: Number of bars for testing (out-of-sample)
        verbose: Print progress
        
    Returns:
        List of window results
    """
    total_bars = len(data)
    window_size = train_size + test_size
    
    # Calculate number of windows
    n_windows = (total_bars - train_size) // test_size
    
    if verbose:
        logger.info(f"Walk-Forward Configuration:")
        logger.info(f"  Total bars: {total_bars}")
        logger.info(f"  Train size: {train_size}")
        logger.info(f"  Test size: {test_size}")
        logger.info(f"  Number of windows: {n_windows}")
    
    results = []
    
    for i in range(n_windows):
        start_idx = i * test_size
        train_end_idx = start_idx + train_size
        test_end_idx = train_end_idx + test_size
        
        if test_end_idx > total_bars:
            break
        
        # Split data
        train_data = data.iloc[start_idx:train_end_idx]
        test_data = data.iloc[train_end_idx:test_end_idx]
        
        if verbose:
            logger.info(f"\nWindow {i+1}/{n_windows}:")
            logger.info(f"  Train: {train_data.index[0]} to {train_data.index[-1]} ({len(train_data)} bars)")
            logger.info(f"  Test:  {test_data.index[0]} to {test_data.index[-1]} ({len(test_data)} bars)")
        
        # Optimize on training data
        if verbose:
            logger.info(f"  Optimizing...")
        best_params, train_score = optimize_on_data(train_data, param_grid)
        
        if verbose:
            logger.info(f"  Best params: {best_params}")
            logger.info(f"  Train score: {train_score:.4f}")
        
        # Test on out-of-sample data
        if verbose:
            logger.info(f"  Testing on out-of-sample data...")
        test_result = test_on_data(test_data, best_params)
        test_score = sharpe_score(test_result)
        
        if verbose:
            logger.info(f"  Test score: {test_score:.4f}")
            logger.info(f"  Test return: {test_result.total_return_pct:.2f}%")
            logger.info(f"  Test trades: {test_result.total_trades}")
        
        # Store results
        window_result = {
            'window': i + 1,
            'train_start': train_data.index[0],
            'train_end': train_data.index[-1],
            'test_start': test_data.index[0],
            'test_end': test_data.index[-1],
            'best_params': best_params,
            'train_score': train_score,
            'test_score': test_score,
            'test_return': test_result.total_return_pct,
            'test_max_dd': test_result.max_drawdown_pct,
            'test_win_rate': test_result.win_rate,
            'test_trades': test_result.total_trades,
            'test_result': test_result
        }
        
        results.append(window_result)
    
    return results


def analyze_stability(results):
    """Analyze parameter stability across windows."""
    logger.info("\n" + "=" * 70)
    logger.info("PARAMETER STABILITY ANALYSIS")
    logger.info("=" * 70)
    
    # Extract parameters from each window
    param_history = {}
    for window in results:
        params = window['best_params']
        for key, value in params.items():
            if key != 'symbol':
                if key not in param_history:
                    param_history[key] = []
                param_history[key].append(value)
    
    # Calculate statistics
    logger.info("\nParameter Stability:")
    for param_name, values in param_history.items():
        unique_values = set(values)
        most_common = max(set(values), key=values.count)
        frequency = values.count(most_common) / len(values) * 100
        
        logger.info(f"\n  {param_name}:")
        logger.info(f"    Unique values: {sorted(unique_values)}")
        logger.info(f"    Most common: {most_common} ({frequency:.1f}% of windows)")
        logger.info(f"    Range: {min(values)} to {max(values)}")


def main():
    """Main execution function."""
    logger.info("=" * 70)
    logger.info("WALK-FORWARD ANALYSIS EXAMPLE")
    logger.info("=" * 70)
    
    # Load data
    logger.info("\n[1/4] Loading data from MT5...")
    date_from = datetime(2025, 1, 1)
    date_to = datetime(2025, 12, 31)
    data = load_mt5_data('EURUSD', 'H1', date_from, date_to)
    logger.info(f"Loaded {len(data)} bars")
    
    # Define parameter grid (smaller for faster execution)
    logger.info("\n[2/4] Defining parameter grid...")
    param_grid = {
        'fast_period': [15, 20, 25],
        'slow_period': [45, 50, 55],
        'filter_period': [180, 200, 220]
    }
    
    logger.info(f"Parameter grid:")
    for key, values in param_grid.items():
        logger.info(f"  {key}: {values}")
    
    # Run walk-forward analysis
    logger.info("\n[3/4] Running walk-forward analysis...")
    logger.info("=" * 70)
    
    wf_results = walk_forward_analysis(
        data=data,
        param_grid=param_grid,
        train_size=500,  # Optimize on 500 bars
        test_size=100,   # Test on 100 bars
        verbose=True
    )
    
    # Analyze results
    logger.info("\n[4/4] Analyzing results...")
    logger.info("=" * 70)
    
    # Calculate aggregate statistics
    train_scores = [w['train_score'] for w in wf_results]
    test_scores = [w['test_score'] for w in wf_results]
    test_returns = [w['test_return'] for w in wf_results]
    
    logger.info("\nAggregate Statistics:")
    logger.info(f"  Number of windows: {len(wf_results)}")
    logger.info(f"\n  Train Scores:")
    logger.info(f"    Average: {sum(train_scores)/len(train_scores):.4f}")
    logger.info(f"    Min: {min(train_scores):.4f}")
    logger.info(f"    Max: {max(train_scores):.4f}")
    logger.info(f"\n  Test Scores (Out-of-Sample):")
    logger.info(f"    Average: {sum(test_scores)/len(test_scores):.4f}")
    logger.info(f"    Min: {min(test_scores):.4f}")
    logger.info(f"    Max: {max(test_scores):.4f}")
    logger.info(f"\n  Test Returns:")
    logger.info(f"    Average: {sum(test_returns)/len(test_returns):.2f}%")
    logger.info(f"    Min: {min(test_returns):.2f}%")
    logger.info(f"    Max: {max(test_returns):.2f}%")
    
    # Performance degradation
    avg_train = sum(train_scores) / len(train_scores)
    avg_test = sum(test_scores) / len(test_scores)
    degradation = ((avg_train - avg_test) / avg_train * 100) if avg_train != 0 else 0
    
    logger.info(f"\n  Performance Degradation:")
    logger.info(f"    Train → Test: {degradation:.1f}%")
    if degradation < 20:
        logger.info(f"    Assessment: ✓ Good (< 20% degradation)")
    elif degradation < 40:
        logger.info(f"    Assessment: ⚠ Moderate (20-40% degradation)")
    else:
        logger.info(f"    Assessment: ✗ High (> 40% degradation - possible overfitting)")
    
    # Parameter stability
    analyze_stability(wf_results)
    
    # Save results
    logger.info("\n" + "=" * 70)
    logger.info("SAVING RESULTS")
    logger.info("=" * 70)
    
    # Create DataFrame
    results_data = []
    for w in wf_results:
        row = {
            'window': w['window'],
            'train_start': w['train_start'],
            'train_end': w['train_end'],
            'test_start': w['test_start'],
            'test_end': w['test_end'],
            'train_score': w['train_score'],
            'test_score': w['test_score'],
            'test_return': w['test_return'],
            'test_max_dd': w['test_max_dd'],
            'test_win_rate': w['test_win_rate'],
            'test_trades': w['test_trades']
        }
        # Add parameters
        for key, value in w['best_params'].items():
            if key != 'symbol':
                row[f'param_{key}'] = value
        
        results_data.append(row)
    
    df = pd.DataFrame(results_data)
    csv_path = OUTPUT_DIR / "walk_forward_results.csv"
    df.to_csv(csv_path, index=False)
    logger.info(f"\nResults saved to: {csv_path}")
    
    # Summary
    logger.info("\n" + "=" * 70)
    logger.info("WALK-FORWARD ANALYSIS COMPLETE")
    logger.info("=" * 70)
    
    logger.info(f"\nKey Findings:")
    logger.info(f"  - Tested {len(wf_results)} windows")
    logger.info(f"  - Average out-of-sample return: {sum(test_returns)/len(test_returns):.2f}%")
    logger.info(f"  - Performance degradation: {degradation:.1f}%")
    logger.info(f"  - Results saved to: {csv_path.name}")
    
    logger.info("\n" + "=" * 70)
    
    return wf_results


if __name__ == "__main__":
    results = main()
