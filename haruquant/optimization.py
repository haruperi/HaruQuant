from typing import Any, Dict, List, Optional, Union, Callable
import pandas as pd
import numpy as np
from services.optimization import methods, scoring, monte_carlo
from . import resolve_service_attr, service_modules


_SERVICE_MODULES = service_modules("services.optimization")

class Splitter:
    """ Powerful time-series splitting for backtesting and ML validation. """
    
    def __init__(self, index: pd.Index, splits: List[Dict[str, pd.Index]], set_labels: List[str]):
        self.index = index
        self.splits = splits
        self.set_labels = set_labels

    def __len__(self):
        return len(self.splits)

    def __getitem__(self, i):
        return self.splits[i]

    @classmethod
    def from_rolling(
        cls, 
        index: pd.Index, 
        length: Union[int, str], 
        split: Union[float, int, str] = 0.5,
        step: Union[int, str] = 1,
        set_labels: List[str] = ["train", "test"],
        freq: Optional[str] = None
    ) -> 'Splitter':
        """ Create rolling windows. """
        if freq:
            index = pd.to_datetime(index)
            
        # Convert string lengths/steps to integers if possible
        def to_int(v, idx):
            if isinstance(v, str):
                delta = pd.to_timedelta(v)
                # Find number of bars matching this delta
                # This is a simplification; ideally we'd use exact time logic
                avg_delta = (idx[-1] - idx[0]) / (len(idx) - 1)
                return int(delta / avg_delta)
            return v

        n = len(index)
        win_len = to_int(length, index)
        step_len = to_int(step, index)
        
        # Calculate split index
        if isinstance(split, float):
            split_idx = int(win_len * split)
        else:
            split_idx = to_int(split, index)

        splits = []
        for i in range(0, n - win_len + 1, step_len):
            window = index[i : i + win_len]
            splits.append({
                set_labels[0]: window[:split_idx],
                set_labels[1]: window[split_idx:]
            })
        
        return cls(index, splits, set_labels)

    @classmethod
    def from_expanding(
        cls,
        index: pd.Index,
        min_length: Union[int, str],
        split: Union[float, int, str] = 0.5,
        step: Union[int, str] = 1,
        set_labels: List[str] = ["train", "test"]
    ) -> 'Splitter':
        """ Create expanding windows. """
        # Implementation logic similar to rolling but start index stays 0
        n = len(index)
        # ... simplified for now ...
        return cls.from_rolling(index, min_length, split, step, set_labels)

    def plots(self):
        """ Visualize the splits. """
        import matplotlib.pyplot as plt
        import matplotlib.patches as mpatches
        
        fig, ax = plt.subplots(figsize=(12, 6))
        colors = {"train": "steelblue", "test": "orange", "valid": "green"}
        
        for i, split in enumerate(self.splits[::-1]): # Show latest at top
            for label, sub_index in split.items():
                if len(sub_index) == 0: continue
                # Find positions in original index
                start_pos = self.index.get_loc(sub_index[0])
                end_pos = self.index.get_loc(sub_index[-1])
                ax.barh(i, end_pos - start_pos, left=start_pos, color=colors.get(label, "gray"), alpha=0.8)
        
        ax.set_yticks(range(len(self.splits)))
        ax.set_yticklabels([f"Split {len(self.splits)-i}" for i in range(len(self.splits))])
        ax.set_xlabel("Bars")
        ax.set_title("Time Series Splits Visualization")
        
        # Legend
        patches = [mpatches.Patch(color=colors.get(l, "gray"), label=l.capitalize()) for l in self.set_labels]
        ax.legend(handles=patches, loc="upper right")
        
        return ax

    @staticmethod
    def rolling_split(
        data: Any,
        window_len: int,
        set_lens: tuple = (1, 1),
        left_to_right: bool = False,
        step: int = 1,
    ) -> List[dict]:
        """
        Perform a rolling split of the data into training and testing sets.
        Mimics vbt.rolling_split.
        """
        # We use Any for data to avoid circular imports, but check for .df property
        if hasattr(data, "df"):
            df = data.df
        else:
            df = data
            
        n = len(df)
        splits = []
        
        total_set_len = sum(set_lens)
        # Normalize set_lens to be fractions of window_len
        unit = window_len / total_set_len
        actual_lens = [int(l * unit) for l in set_lens]
        
        if left_to_right:
            indices = range(0, n - window_len + 1, step)
        else:
            indices = range(n - window_len, -1, -step)
            
        for i in indices:
            current_window = df.iloc[i : i + window_len]
            split = {}
            start = 0
            
            names = ['train', 'valid', 'test'] if len(set_lens) == 3 else ['train', 'test']
            for name, length in zip(names, actual_lens):
                split[name] = current_window.iloc[start : start + length]
                start += length
                
            splits.append(split)
            
        return splits if left_to_right else splits[::-1]

class PortfolioOptimizer:
    """
    Handles portfolio-level optimization and rebalancing.
    Mimics vbt.PFO.
    """
    def __init__(self, weights: pd.DataFrame):
        self.weights = weights

    @classmethod
    def from_optimize_func(cls, data: Any, optimize_func: Callable, every: str = "M"):
        """
        Periodically optimize portfolio weights.
        
        Args:
            data: Data object containing multiple symbols.
            optimize_func: Callback function(data_slice) returning weights Series.
            every: Frequency string (e.g., 'M', 'W', 'D').
        """
        from .data import Data
        
        # Ensure we have a Data object
        if not hasattr(data, "df"):
            raise ValueError("Data must be a HaruQuant Data object.")
            
        # Group by frequency
        # Handle pandas 2.0+ frequency names (M -> ME, etc)
        freq = every
        if freq == "M": freq = "ME"
        elif freq == "Y": freq = "YE"
        elif freq == "H": freq = "h" # Pandas uses lowercase 'h' for hours usually, or just H
        
        groups = data.df.groupby(pd.Grouper(freq=freq))
        
        all_weights = []
        for timestamp, group_df in groups:
            if group_df.empty:
                continue
                
            # Create a slice of data
            # We want to pass data up to this point, or just this window?
            # VBT's from_optimize_func usually passes the slice up to 'index_slice'
            # For simplicity, we pass the current group_df
            slice_data = Data(group_df)
            
            # Call user optimization function
            weights = optimize_func(slice_data)
            
            if isinstance(weights, pd.Series):
                row = weights.to_dict()
            elif isinstance(weights, dict):
                row = weights
            else:
                # Assume it's a list/array matching symbols
                row = dict(zip(data.symbols, weights))
                
            row['timestamp'] = timestamp
            all_weights.append(row)
            
        weights_df = pd.DataFrame(all_weights).set_index('timestamp')
        return cls(weights_df)

    def plot(self):
        """Plot the weights over time."""
        import matplotlib.pyplot as plt
        try:
            # Check if we have negative weights
            if (self.weights < 0).any().any():
                # For mixed weights, a line plot or non-stacked bar is better
                ax = self.weights.plot(kind='line', figsize=(12, 6), marker='o', alpha=0.8)
            else:
                ax = self.weights.plot(kind='area', stacked=True, figsize=(12, 6), alpha=0.8)
                
            ax.set_title("Portfolio Allocation Over Time")
            ax.set_ylabel("Weights")
            ax.set_xlabel("Date")
            ax.legend(loc='center left', bbox_to_anchor=(1, 0.5))
            ax.axhline(0, color='black', lw=1, ls='--')
            plt.tight_layout()
            return ax
        except Exception as e:
            print(f"Plotting error: {e}")
            return None

class Optimizer:
    """High-level encapsulation for strategy optimization and robustness testing."""

    @staticmethod
    def _service_strategy_class(strategy_class: Any) -> Any:
        return getattr(strategy_class, "_service_strategy_class", strategy_class)

    @staticmethod
    def get_scoring_func(objective: str) -> Callable:
        """Map common objective names to scoring functions."""
        scoring_map = {
            "Sharpe Ratio": scoring.sharpe_score,
            "Sortino Ratio": scoring.sortino_score,
            "Calmar Ratio": scoring.calmar_score,
            "Total Return": scoring.total_return_score,
            "Profit Factor": scoring.profit_factor_score
        }
        return scoring_map.get(objective, scoring.sharpe_score)

    @staticmethod
    def grid_search(
        strategy_class: Any,
        data: pd.DataFrame,
        param_grid: Dict[str, List[Any]],
        symbol: str = "SYMBOL",
        initial_balance: float = 10000.0,
        objective: str = "Sharpe Ratio",
        max_workers: int = 4,
        random_subset: Optional[int] = None,
        verbose: bool = True
    ):
        """Exhaustive search over a specified parameter grid."""
        # Automatically unpack Param objects if present
        actual_grid = {
            k: (v.values if hasattr(v, "values") and not isinstance(v, (list, pd.Series, np.ndarray)) else v)
            for k, v in param_grid.items()
        }

        return methods.grid_search(
            strategy_class=Optimizer._service_strategy_class(strategy_class),
            data=data,
            param_grid=actual_grid,
            symbol=symbol,
            initial_balance=initial_balance,
            scoring_func=Optimizer.get_scoring_func(objective),
            max_workers=max_workers,
            random_subset=random_subset,
            verbose=verbose
        )

    @staticmethod
    def run_combinations(
        strategy_class: Any,
        data: pd.DataFrame,
        combinations: List[Dict[str, Any]],
        symbol: str = "SYMBOL",
        initial_balance: float = 10000.0,
        objective: str = "Sharpe Ratio",
        max_workers: int = 4,
        verbose: bool = True
    ):
        """Run backtests over a pre-defined list of parameter combinations."""
        # TODO: Implement parallel execution for arbitrary parameter sets
        pass

    @staticmethod
    def random_search(
        strategy_class: Any,
        data: pd.DataFrame,
        param_distributions: Dict[str, Any],
        n_iter: int = 20,
        symbol: str = "SYMBOL",
        initial_balance: float = 10000.0,
        objective: str = "Sharpe Ratio",
        max_workers: int = 4,
        verbose: bool = True
    ):
        """Randomized search over parameter distributions."""
        return methods.random_search(
            strategy_class=Optimizer._service_strategy_class(strategy_class),
            data=data,
            param_distributions=param_distributions,
            n_iter=n_iter,
            symbol=symbol,
            initial_balance=initial_balance,
            scoring_func=Optimizer.get_scoring_func(objective),
            max_workers=max_workers,
            verbose=verbose
        )

    @staticmethod
    def bayesian(
        strategy_class: Any,
        data: pd.DataFrame,
        param_space: Dict[str, Any],
        n_iterations: int = 20,
        symbol: str = "SYMBOL",
        initial_balance: float = 10000.0,
        objective: str = "Sharpe Ratio",
        max_workers: int = 4,
        verbose: bool = True
    ):
        """Bayesian optimization using Gaussian Processes."""
        return methods.bayesian_optimization(
            strategy_class=Optimizer._service_strategy_class(strategy_class),
            data=data,
            param_space=param_space,
            n_iterations=n_iterations,
            symbol=symbol,
            initial_balance=initial_balance,
            scoring_func=Optimizer.get_scoring_func(objective),
            max_workers=max_workers,
            verbose=verbose
        )

    @staticmethod
    def genetic(
        strategy_class: Any,
        data: pd.DataFrame,
        param_ranges: Dict[str, Any],
        population_size: int = 10,
        generations: int = 3,
        symbol: str = "SYMBOL",
        initial_balance: float = 10000.0,
        objective: str = "Sharpe Ratio",
        max_workers: int = 4,
        verbose: bool = True
    ):
        """Optimization using Genetic Algorithms (Evolutionary Search)."""
        return methods.genetic_algorithm(
            strategy_class=Optimizer._service_strategy_class(strategy_class),
            data=data,
            param_ranges=param_ranges,
            population_size=population_size,
            generations=generations,
            symbol=symbol,
            initial_balance=initial_balance,
            scoring_func=Optimizer.get_scoring_func(objective),
            max_workers=max_workers,
            verbose=verbose
        )

    @staticmethod
    def walk_forward(
        strategy_class: Any,
        data: pd.DataFrame,
        param_grid: Dict[str, List[Any]],
        train_period: int,
        test_period: int,
        symbol: str = "SYMBOL",
        initial_balance: float = 10000.0,
        objective: str = "Sharpe Ratio",
        verbose: bool = True
    ):
        """Walk-Forward Analysis (WFA) to test strategy robustness over time."""
        return methods.walk_forward_optimization(
            strategy_class=Optimizer._service_strategy_class(strategy_class),
            data=data,
            param_grid=param_grid,
            train_period=train_period,
            test_period=test_period,
            symbol=symbol,
            initial_balance=initial_balance,
            scoring_func=Optimizer.get_scoring_func(objective),
            verbose=verbose
        )

    @staticmethod
    def monte_carlo(
        backtest_id: str = None,
        trades: pd.DataFrame = None,
        simulation_type: str = "shuffle",
        simulations: int = 1000,
        skip_probability: float = 0.1,
        deterioration_pct: float = 0.05,
        initial_balance: float = 10000.0
    ):
        """Monte Carlo simulation for strategy robustness and risk analysis."""
        if trades is None and backtest_id:
            from data.database.repositories.backtest_repository import get_backtest_trades_df
            trades = get_backtest_trades_df(backtest_id)
            
        if trades is None or trades.empty:
            raise ValueError("Either 'trades' DataFrame or a valid 'backtest_id' must be provided.")
            
        return monte_carlo.robustness_simulation(
            trades=trades,
            simulation_type=simulation_type,
            simulations=simulations,
            skip_probability=skip_probability,
            deterioration_pct=deterioration_pct,
            initial_balance=initial_balance,
        )


def __getattr__(name: str):
    return resolve_service_attr(name, _SERVICE_MODULES)
