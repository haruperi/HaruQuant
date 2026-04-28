import os
import sys
from datetime import datetime
import pandas as pd
import numpy as np

# Add project root and backend to sys.path
current_dir = os.path.dirname(os.path.abspath(__file__))
project_root = os.path.abspath(os.path.join(current_dir, '..', '..', '..', '..'))
if project_root not in sys.path:
    sys.path.insert(0, project_root)
    
backend_dir = os.path.join(project_root, 'backend')
if backend_dir not in sys.path:
    sys.path.insert(0, backend_dir)

import haruquant as hqt
from backend.services.optimization.methods import grid_search, random_search, bayesian_optimization, genetic_algorithm, walk_forward_optimization
from backend.services.optimization.monte_carlo import robustness_simulation
from backend.services.optimization import scoring
from backend.data.strategies.trend_following import TrendFollowingStrategy

# --- HELPER: Map UI string to scoring function ---
def get_scoring_func(objective_name: str):
    scoring_map = {
        "Sharpe Ratio": scoring.sharpe_score,
        "Sortino Ratio": scoring.sortino_score,
        "Calmar Ratio": scoring.calmar_score,
        "Total Return": scoring.total_return_score,
        "Profit Factor": scoring.profit_factor_score
    }
    return scoring_map.get(objective_name, scoring.sharpe_score)

# --- EXAMPLES ALIGNED WITH UI INPUTS ---

def example_01_grid_search(
    bars: pd.DataFrame, 
    strategy_class=TrendFollowingStrategy,
    objective="Sharpe Ratio",
    param_grid=None,
    max_workers=4,
    initial_balance=10000.0
):
    print("\n" + "="*50)
    print(f"Example 01: Grid Search (Objective: {objective})")
    print("="*50)

    if param_grid is None:
        # Mimic UI "min, max, step" by generating lists
        param_grid = {
            'fast_period': list(range(10, 31, 10)),  # 10, 20, 30
            'slow_period': list(range(40, 61, 10)),  # 40, 50, 60
            'filter_period': [150, 200]
        }

    summary = grid_search(
        strategy_class=strategy_class,
        data=bars,
        param_grid=param_grid,
        symbol="GBPUSD",
        initial_balance=initial_balance,
        scoring_func=get_scoring_func(objective),
        engine_type="vectorized",
        max_workers=max_workers,
        verbose=True
    )

    print(f"\nBest Parameters: {summary.best_params}")
    print(f"Best Score: {summary.best_score:.4f}")

def example_02_random_search(
    bars: pd.DataFrame,
    strategy_class=TrendFollowingStrategy,
    objective="Sharpe Ratio",
    param_distributions=None,
    n_iter=20,
    max_workers=4,
    initial_balance=10000.0
):
    print("\n" + "="*50)
    print(f"Example 02: Random Search (Objective: {objective})")
    print("="*50)

    if param_distributions is None:
        param_distributions = {
            'fast_period': (5, 50),
            'slow_period': (40, 100),
            'filter_period': (100, 300)
        }

    summary = random_search(
        strategy_class=strategy_class,
        data=bars,
        param_distributions=param_distributions,
        n_iter=n_iter,
        symbol="GBPUSD",
        initial_balance=initial_balance,
        scoring_func=get_scoring_func(objective),
        engine_type="vectorized",
        max_workers=max_workers,
        verbose=True
    )

    print(f"\nBest Parameters: {summary.best_params}")
    print(f"Best Score: {summary.best_score:.4f}")

def example_03_bayesian(
    bars: pd.DataFrame,
    strategy_class=TrendFollowingStrategy,
    objective="Sharpe Ratio",
    param_space=None,
    n_iterations=20,
    max_workers=4,
    initial_balance=10000.0
):
    print("\n" + "="*50)
    print(f"Example 03: Bayesian Optimization (Objective: {objective})")
    print("="*50)

    if param_space is None:
        param_space = {
            'fast_period': (5, 50),
            'slow_period': (40, 100),
            'filter_period': (100, 300)
        }

    summary = bayesian_optimization(
        strategy_class=strategy_class,
        data=bars,
        param_space=param_space,
        n_iterations=n_iterations,
        symbol="GBPUSD",
        initial_balance=initial_balance,
        scoring_func=get_scoring_func(objective),
        engine_type="vectorized",
        max_workers=max_workers,
        verbose=True
    )

    print(f"\nBest Parameters: {summary.best_params}")
    print(f"Best Score: {summary.best_score:.4f}")

def example_04_genetic(
    bars: pd.DataFrame,
    strategy_class=TrendFollowingStrategy,
    objective="Sharpe Ratio",
    param_ranges=None,
    population_size=10,
    generations=3,
    max_workers=4,
    initial_balance=10000.0
):
    print("\n" + "="*50)
    print(f"Example 04: Genetic Algorithm (Objective: {objective})")
    print("="*50)

    if param_ranges is None:
        param_ranges = {
            'fast_period': (5, 50),
            'slow_period': (40, 100),
            'filter_period': (100, 300)
        }

    summary = genetic_algorithm(
        strategy_class=strategy_class,
        data=bars,
        param_ranges=param_ranges,
        population_size=population_size,
        generations=generations,
        symbol="GBPUSD",
        initial_balance=initial_balance,
        scoring_func=get_scoring_func(objective),
        engine_type="vectorized",
        max_workers=max_workers,
        verbose=True
    )

    print(f"\nBest Parameters: {summary.best_params}")
    print(f"Best Score: {summary.best_score:.4f}")

def example_05_walk_forward_optimazation(
    bars: pd.DataFrame,
    strategy_class=TrendFollowingStrategy,
    train_period=3000,
    test_period=1000,
    initial_balance=10000.0,
    objective="Sharpe Ratio",
    param_grid=None
):
    print("\n" + "="*50)
    print(f"Example 05: Walk-Forward Optimization (Objective: {objective})")
    print("="*50)

    if param_grid is None:
        param_grid = {
            'fast_period': [10, 20],
            'slow_period': [40, 60],
            'filter_period': [150, 200]
        }

    results_summary = walk_forward_optimization(
        strategy_class=strategy_class,
        data=bars,
        param_grid=param_grid,
        train_period=train_period,
        test_period=test_period,
        symbol="GBPUSD",
        initial_balance=initial_balance,
        scoring_func=get_scoring_func(objective),
        verbose=True
    )

    print("\n" + "-"*30)
    print("WALK-FORWARD SUMMARY")
    print("-"*30)
    results = results_summary["windows"]
    print(f"Total Walks: {len(results)}")
    print(f"Average OOS Return: {results_summary['avg_test_return']:.2f}%")
    print(f"Robustness Ratio: {results_summary['robustness_ratio']:.4f}")

def example_06_MC_strategy_robustness(
    backtest_id: str,
    simulation_type: str = "shuffle", # "shuffle" or "bootstrap"
    skip_probability: float = 0.1,    # 10% chance to skip a trade
    deterioration_pct: float = 0.05,  # 5% deterioration in returns
    simulations: int = 1000
):
    print("\n" + "="*50)
    print(f"Example 06: Monte Carlo Strategy Robustness (Type: {simulation_type})")
    print("="*50)

    print(f"Running {simulations} simulations for Backtest: {backtest_id}...")
    
    # --- MOCKING DATA IF DB IS EMPTY (For demonstration) ---
    # In a real UI, this would fetch from the database.
    # Here we'll generate some dummy trades to show the math works.
    if backtest_id == "LATEST_BACKTEST_ID":
        print("Using dummy trades for demonstration...")
        # 100 random trades with positive expectancy
        np.random.seed(42)
        original_profits = np.random.normal(100, 500, 100) 
    else:
        # Real logic (Try to fetch from DB)
        try:
            from backend.data.database.repositories.backtest_repository import get_backtest_trades_df
            df = get_backtest_trades_df(backtest_id)
            original_profits = df["profit"].to_numpy()
        except Exception:
            print(f"Backtest {backtest_id} not found. Falling back to dummy data.")
            original_profits = np.random.normal(100, 500, 100)

    # --- CORE SIMULATION LOGIC ---
    # (Simplified version of robustness_simulation for this example)
    initial_balance = 10000.0
    final_profits = []
    max_drawdowns = []
    
    for _ in range(simulations):
        # 1. Resample
        if simulation_type == "shuffle":
            sim_profits = np.random.permutation(original_profits)
        else:
            sim_profits = np.random.choice(original_profits, size=len(original_profits), replace=True)

        # 2. Skip Trades
        mask = np.random.random(len(sim_profits)) > skip_probability
        sim_profits = sim_profits[mask]

        # 3. Deterioration
        sim_profits = sim_profits * (1.0 - deterioration_pct)

        # Calculate Results
        curve = np.cumsum(np.insert(sim_profits, 0, 0)) + initial_balance
        final_profits.append(curve[-1] - initial_balance)
        
        peak = np.maximum.accumulate(curve)
        dd = (peak - curve) / peak * 100
        max_drawdowns.append(np.max(dd))

    # --- RESULTS ---
    print("\n" + "-"*30)
    print("MONTE CARLO ROBUSTNESS STATS")
    print("-"*30)
    print(f"Original Approx Profit: ${np.sum(original_profits):,.2f}")
    print(f"Mean Sim Profit: ${np.mean(final_profits):,.2f}")
    print(f"Worst-Case Drawdown (95th): {np.percentile(max_drawdowns, 95):.2f}%")
    print(f"Probability of Profit: {np.mean(np.array(final_profits) > 0)*100:.2f}%")
    print(f"95% CI: [${np.percentile(final_profits, 2.5):,.2f}, ${np.percentile(final_profits, 97.5):,.2f}]")

if __name__ == "__main__":
    # 1. Download data once
    print("Downloading data for GBPUSD...")
    data = hqt.MT5Data.download(
        symbol="GBPUSD",
        timeframe="H1",
        start=datetime(2024, 1, 1),
        end=datetime(2025, 12, 31)
    )
    bars = data.df

    # example_01_grid_search(bars=bars)
    # example_02_random_search(bars=bars)
    # example_03_bayesian(bars=bars)
    # example_04_genetic(bars=bars)
    # example_05_walk_forward_optimazation(bars=bars)
    
    # Monte Carlo Example (Requires a valid Backtest ID from DB)
    example_06_MC_strategy_robustness(
        backtest_id="LATEST_BACKTEST_ID",
        simulation_type="bootstrap",
        skip_probability=0.1,
        deterioration_pct=0.05,
        simulations=500
    )
    
