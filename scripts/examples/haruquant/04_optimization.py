from datetime import datetime, timedelta
import pandas as pd
import numpy as np


import haruquant as hqt

def example_01_grid_search(bars: pd.DataFrame):
    print("\n" + "="*50)
    print("Example 01: Grid Search (Exhaustive)")
    print("="*50)

    # Define parameter grid
    param_grid = {
        'fast_period': [10, 20, 30],
        'slow_period': [40, 50, 60],
        'filter_period': [150, 200]
    }

    summary = hqt.grid_search(
        strategy_class=hqt.TrendFollowingStrategy,
        data=bars,
        param_grid=param_grid,
        symbol="GBPUSD",
        objective="Sharpe Ratio"
    )

    print(f"\nBest Parameters: {summary.best_params}")
    print(f"Best Score: {summary.best_score:.4f}")

def example_02_random_search(bars: pd.DataFrame):
    print("\n" + "="*50)
    print("Example 02: Random Search (Stochastic)")
    print("="*50)

    # Define parameter distributions (min, max)
    param_distributions = {
        'fast_period': (5, 50),
        'slow_period': (40, 100),
        'filter_period': (100, 300)
    }

    summary = hqt.random_search(
        strategy_class=hqt.TrendFollowingStrategy,
        data=bars,
        param_distributions=param_distributions,
        n_iter=15,
        symbol="GBPUSD",
        objective="Sortino Ratio"
    )

    print(f"\nBest Parameters: {summary.best_params}")
    print(f"Best Score: {summary.best_score:.4f}")

def example_03_bayesian_optimization(bars: pd.DataFrame):
    print("\n" + "="*50)
    print("Example 03: Bayesian Optimization (AI-Driven)")
    print("="*50)

    param_space = {
        'fast_period': (5, 50),
        'slow_period': (40, 100),
        'filter_period': (100, 300)
    }

    summary = hqt.bayesian(
        strategy_class=hqt.TrendFollowingStrategy,
        data=bars,
        param_space=param_space,
        n_iterations=15,
        symbol="GBPUSD",
        objective="Calmar Ratio"
    )

    print(f"\nBest Parameters: {summary.best_params}")
    print(f"Best Score: {summary.best_score:.4f}")

def example_04_genetic_algorithm(bars: pd.DataFrame):
    print("\n" + "="*50)
    print("Example 04: Genetic Algorithm (Evolutionary)")
    print("="*50)

    param_ranges = {
        'fast_period': (5, 50),
        'slow_period': (40, 100),
        'filter_period': (100, 300)
    }

    summary = hqt.genetic(
        strategy_class=hqt.TrendFollowingStrategy,
        data=bars,
        param_ranges=param_ranges,
        population_size=10,
        generations=3,
        symbol="GBPUSD",
        objective="Total Return"
    )

    print(f"\nBest Parameters: {summary.best_params}")
    print(f"Best Score: {summary.best_score:.4f}")

def example_05_walk_forward_analysis(bars: pd.DataFrame):
    print("\n" + "="*50)
    print("Example 05: Walk-Forward Analysis (Validation)")
    print("="*50)

    param_grid = {
        'fast_period': [10, 20],
        'slow_period': [40, 60]
    }

    # train_period=3000, test_period=1000
    results_summary = hqt.walk_forward(
        strategy_class=hqt.TrendFollowingStrategy,
        data=bars,
        param_grid=param_grid,
        train_period=3000,
        test_period=1000,
        symbol="GBPUSD",
        objective="Sharpe Ratio"
    )

    print("\nWALK-FORWARD SUMMARY")
    print(f"Total Walks: {len(results_summary['windows'])}")
    print(f"Avg OOS Return: {results_summary['avg_test_return']:.2f}%")
    print(f"Robustness Ratio: {results_summary['robustness_ratio']:.4f}")

def example_06_monte_carlo_robustness():
    print("\n" + "="*50)
    print("Example 06: Monte Carlo Robustness (Risk)")
    print("="*50)

    # For demonstration, we'll create some dummy trades
    # In practice, you would pass a backtest_id from your database
    np.random.seed(42)
    dummy_trades = pd.DataFrame({
        'profit_loss': np.random.normal(100, 500, 100),
        'type': np.random.choice(['buy', 'sell'], 100)
    })

    results = hqt.monte_carlo(
        trades=dummy_trades,
        simulation_type="bootstrap",
        simulations=500,
        skip_probability=0.1,
        deterioration_pct=0.05
    )

    print(f"Probability of Profit: {results['prob_profitable']*100:.2f}%")
    print(f"Worst-Case Drawdown (95th): {results['max_drawdown_95']:.2f}%")
    print(f"Expected Return (Mean): ${results['mean_profit']:,.2f}")

def example_07_data_splitter():
    print("\n" + "="*50)
    print("Example 07: Time-Series Splitting (hqt.Splitter)")
    print("="*50)
    try:
        # Pull real data for a better example
        print("Pulling BTC-USD data for 4 years...")
        data = hqt.YFData.download("BTC-USD", start="2020-01-01")
        
        # Create a rolling splitter
        # 360 days total window, 50/50 split (180 train, 180 test)
        splitter = hqt.Splitter.from_rolling(
            data.index,
            length="360 days",
            split=0.3,
            set_labels=["train", "test"],
            step="30 days"
        )
        
        print(f"Generated {len(splitter)} rolling splits!")
        
        # Access a specific split
        first_split = splitter[0]
        print(f"\nFirst Split Detail:")
        print(f" - Train: {first_split['train'][0]} to {first_split['train'][-1]} ({len(first_split['train'])} bars)")
        print(f" - Test:  {first_split['test'][0]} to {first_split['test'][-1]} ({len(first_split['test'])} bars)")
        
        # Visualization (optional, requires matplotlib)
        try:
            print("\nGenerating visualization...")
            ax = splitter.plots()
            # plt.show() # Normally we'd show it, but here we just verify it works
            print("Visualization generated successfully!")
        except Exception as ve:
            print(f"Visualization error: {ve}")

    except Exception as e:
        print(f"Splitter error: {e}")

def example_08_random_subset(bars: pd.DataFrame):
    print("\n" + "="*50)
    print("Example 08: Random Subset Grid Search (vbt-like)")
    print("="*50)

    # Use Param to define search space (vbt-style)
    # This will be automatically converted to a list by Optimizer if needed
    param_grid = {
        'fast_period': hqt.Param(np.arange(10, 50, 5)),
        'slow_period': hqt.Param(np.arange(60, 150, 10)),
        'filter_period': hqt.Param([150, 200, 250])
    }

    print(f"Testing a random subset of 10 combinations...")

    summary = hqt.grid_search(
        strategy_class=hqt.TrendFollowingStrategy,
        data=bars,
        param_grid=param_grid,
        random_subset=10,
        symbol="GBPUSD",
        objective="Total Return"
    )

    print(f"\nBest Parameters found in random subset: {summary.best_params}")
    print(f"Best Score: {summary.best_score:.4f}")
    print(f"Total combinations tested: {len(summary.all_results)}")

def example_09_parameter_combinations():
    print("\n" + "="*50)
    print("Example 09: Advanced Parameter Combinations (vbt-like)")
    print("="*50)

    from itertools import combinations
    
    # Generate 100 values
    window_space = np.arange(100)
    # Generate all pairs (fast < slow)
    fastk_windows, slowk_windows = list(zip(*combinations(window_space, 2)))
    
    # Dummy window types
    window_type_space = [1, 2, 3, 4] # e.g. SMA, EMA, etc.

    print(f"Generating combinations using levels...")
    param_product = hqt.combine_params(
        dict(
            fast_window=hqt.Param(fastk_windows, level=0),  
            slow_window=hqt.Param(slowk_windows, level=0),
            signal_window=hqt.Param(window_space, level=1),
            macd_wtype=hqt.Param(window_type_space, level=2),  
            signal_wtype=hqt.Param(window_type_space, level=2),
        ),
        random_subset=10, # Keeping it small for the example
        build_index=False
    )

    print(f"\nGenerated {len(param_product)} random combinations.")
    print("Sample combinations:")
    df_params = pd.DataFrame(param_product)
    print(df_params.head())

def example_10_portfolio_optimization():
    print("\n" + "="*50)
    print("Example 10: Portfolio Optimization (PFO)")
    print("="*50)

    # User-defined optimization callback
    def regime_change_optimize_func(data: hqt.Data):
        # Calculate total returns for this period
        # We handle MultiIndex columns by applying to close
        close = data.close
        total_return = (close.iloc[-1] / close.iloc[0]) - 1
        
        # Initialize weights with 0
        weights = pd.Series(0.0, index=data.symbols)
        
        # Strategy: Allocate proportional to positive returns, 
        # but inverse to total return (as in user request: "Allocate assets inversely...")
        # Actually user request code said: weights[pos_mask] = total_return[pos_mask] / total_return.abs().sum()
        # and then returned -1 * weights.
        
        # We'll follow the user's logic
        abs_sum = total_return.abs().sum()
        if abs_sum > 0:
            weights = total_return / abs_sum
            
        return -1 * weights

    print("Downloading multi-symbol data for Forex pairs from MT5...")
    symbols = ["EURUSD", "GBPUSD", "USDJPY", "AUDUSD", "USDCHF"]
    data = hqt.MT5Data.download(
        symbols, 
        timeframe="H4", 
        start=datetime(2023, 1, 1), 
        end=datetime(2023, 12, 31)
    )
    
    print(f"Running monthly portfolio optimization (rebalancing)...")
    pfo = hqt.PFO.from_optimize_func(
        data,
        regime_change_optimize_func,
        every="M"
    )

    print("\nCalculated Weights (First 5 months):")
    print(pfo.weights.head())

    print("\nGenerating allocation plot...")
    try:
        pfo.plot()
        print("Plot generated successfully!")
    except Exception as e:
        print(f"Plotting skipped: {e}")

if __name__ == "__main__":
    # 1. Download data once
    print("Fetching data for GBPUSD...")
    data = hqt.MT5Data.download(
        symbol="GBPUSD",
        timeframe="H1",
        start=datetime(2024, 1, 1),
        end=datetime(2025, 12, 31)
    )
    bars = data.df

    example_01_grid_search(bars)
    example_02_random_search(bars)
    example_03_bayesian_optimization(bars)
    example_04_genetic_algorithm(bars)
    example_05_walk_forward_analysis(bars)
    example_06_monte_carlo_robustness()
    example_07_data_splitter()
    example_08_random_subset(bars)
    example_09_parameter_combinations()
    example_10_portfolio_optimization()
