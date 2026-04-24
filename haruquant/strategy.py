import pandas as pd
import numpy as np
from typing import Dict, Any, Optional, Union, List
from haruquant.data import Data
from backend.services.execution.core import RunResult

from concurrent.futures import ThreadPoolExecutor
from dataclasses import replace

def _deep_merge(base, overrides):
    """Recursively merge two dictionaries."""
    for key, value in overrides.items():
        if isinstance(value, dict) and key in base and isinstance(base[key], dict):
            _deep_merge(base[key], value)
        else:
            base[key] = value
    return base

DEFAULT_SIM_CONFIG = {
    "engine_type": "vectorized",
    "backend": "sim",
    "account": {
        "initial_balance": 10000.0,
        "commission": 7.0,
        "leverage": 400,
        "currency": "USD",
    },
    "data": {
        "source": "metatrader",
        "symbols": ["GBPUSD"],
        "timeframe": "H1",
        "start": "2023-01-01",
        "end": "2023-12-31",
        "warmup_start": "2022-10-01",
    },
    "strategy": {
        "name": "TrendFollowingStrategy",
        "params": {
            "fast_period": 20,
            "slow_period": 50,
            "filter_period": 200,
        },
    },
    "execution": {
        "tick_model": "timeframe_ticks",
        "spread_model": "native_spread",
        "slippage_model": "fixed",
        "slippage_points": 1,
        "contract_size": 100000,
        "position_size": {
            "type": "fixed_lot",
            "lot_size": 0.1,
        },
    },
    "reporting": {
        "print_summary": False,
        "save_to_db": False,
        "alias": "default_run",
        "description": "HaruQuant default simulation run.",
        "equity_snapshot_policy": "position_update",
    },
}

from backend.services.strategy.catalog import (
    StrategyCatalogCreateRequest,
    StrategyCatalogService,
    StrategyCatalogUpdateRequest,
)

import inspect
from backend.services.strategy.baselines import (
    EmaCrossBaselineStrategy,
    NaiveMomentumStrategy,
    RsiBaselineStrategy,
)

# Map known baseline strategy names to their classes for source-code fallback
_BASELINE_STRATEGIES: Dict[str, type] = {
    "ema_cross": EmaCrossBaselineStrategy,
    "ema_cross_baseline_strategy": EmaCrossBaselineStrategy,
    "naive_momentum": NaiveMomentumStrategy,
    "naive_momentum_strategy": NaiveMomentumStrategy,
    "rsi": RsiBaselineStrategy,
    "rsi_baseline_strategy": RsiBaselineStrategy,
}

def _get_baseline_source_code(strategy_name: str) -> Optional[str]:
    """Return the Python source code for a built-in baseline strategy."""
    cls = _BASELINE_STRATEGIES.get(strategy_name.lower().strip())
    if cls is None:
        return None
    try:
        return inspect.getsource(cls)
    except (OSError, TypeError):
        return None

class Catalog:
    """Centralized catalog for managing strategies, versions, and governance."""
    
    def __init__(self, db_manager: Optional[DatabaseManager] = None):
        self._service = StrategyCatalogService(db_manager=db_manager)
        
    def create(self, request: StrategyCatalogCreateRequest, user_id: int) -> Dict[str, Any]:
        return self._service.create_strategy(request, user_id=user_id)
        
    def list(self, user_id: int, status: Optional[str] = None, category: Optional[str] = None) -> List[Dict[str, Any]]:
        return self._service.list_strategies(user_id=user_id, status=status, category=category)
        
    def get(self, strategy_id: int, user_id: Optional[int] = None) -> Dict[str, Any]:
        return self._service.get_strategy(strategy_id, user_id=user_id)
        
    def update(self, strategy_id: int, request: StrategyCatalogUpdateRequest, user_id: int) -> Dict[str, Any]:
        return self._service.update_strategy(strategy_id, request, user_id=user_id)
        
    def delete(self, strategy_id: int, user_id: int) -> None:
        self._service.delete_strategy(strategy_id, user_id=user_id)
        
    def list_versions(self, strategy_id: int) -> List[Dict[str, Any]]:
        return self._service.list_versions(strategy_id)
        
    def get_version_code(self, strategy_id: int, version_id: int, user_id: int) -> Dict[str, Any]:
        return self._service.get_version_code(
            strategy_id=strategy_id,
            version_id=version_id,
            user_id=user_id,
            baseline_source_lookup=_get_baseline_source_code
        )
        
    def rollback(self, strategy_id: int, version_id: int, user_id: int) -> None:
        self._service.rollback_version(strategy_id=strategy_id, version_id=version_id, user_id=user_id)
        
    def export(self, strategy_id: int, user_id: int) -> str:
        return self._service.export_strategy(strategy_id=strategy_id, user_id=user_id)
        
    def import_zip(self, strategy_id: int, import_path: str, filename: str, user_id: int) -> str:
        return self._service.import_strategy(
            strategy_id=strategy_id,
            import_path=import_path,
            original_filename=filename,
            user_id=user_id
        )

class Portfolio:
    """Result of a backtest, mimicking VectorBT's Portfolio class."""
    
    def __init__(self, run_result: Union[RunResult, Any], initial_balance: float):
        self._raw_result = run_result
        self.initial_balance = initial_balance
        
    @property
    def result(self):
        # Compatibility with existing code expecting .result to be RunResult
        from backend.services.simulation.results import SimulationRunResult
        if isinstance(self._raw_result, SimulationRunResult):
            return self._raw_result.run_result
        return self._raw_result

    @property
    def trades(self) -> List[Any]:
        return self.result.trades
        
    @property
    def equity_curve(self) -> List[Any]:
        return self.result.equity_curve
        
    @property
    def init_cash(self) -> float:
        return self.initial_balance
        
    @property
    def final_value(self) -> float:
        return self.result.final_equity
        
    def total_profit(self) -> float:
        """Returns the total net profit (realized + unrealized)."""
        return self.result.final_equity - self.initial_balance
        
    def total_return(self) -> float:
        """Returns the total return as a percentage of initial balance."""
        if self.initial_balance == 0:
            return 0.0
        return (self.total_profit() / self.initial_balance) * 100.0

    def summary(self) -> str:
        """Returns a formatted summary table of All, Long, and Short results."""
        from backend.services.simulation.results import SimulationRunResult
        from backend.services.simulation.reporting import simulation_summary_rows
        
        if not isinstance(self._raw_result, SimulationRunResult):
            # Fallback for simple RunResult (e.g. from_holding)
            return (
                f"Backtest Summary\n"
                f"{'-'*30}\n"
                f"Initial Balance: {self.initial_balance:.2f}\n"
                f"Final Equity:    {self.result.final_equity:.2f}\n"
                f"Total Profit:    {self.total_profit():.2f}\n"
                f"Total Return:    {self.total_return():.2f}%\n"
                f"Number of Trades: {len(self.trades)}\n"
            )
            
        # Filter trades
        all_trades = self.trades
        long_trades = [t for t in all_trades if str(t.type).lower() == "buy"]
        short_trades = [t for t in all_trades if str(t.type).lower() == "sell"]
        
        # Parallel Calculation Helper
        def get_subset_metrics(trades_subset):
            if not trades_subset and trades_subset is not all_trades:
                return None
            
            # Create a localized result for this subset
            # We clear equity_curve so reporting helper regenerates it from the trade subset
            subset_run_result = replace(self.result, trades=trades_subset, equity_curve=[])
            subset_sim_result = replace(self._raw_result, run_result=subset_run_result)
            
            # Calculate metrics
            return simulation_summary_rows(subset_sim_result)

        # Run All, Long, and Short in parallel
        with ThreadPoolExecutor(max_workers=3) as executor:
            futures = [
                executor.submit(get_subset_metrics, all_trades),
                executor.submit(get_subset_metrics, long_trades),
                executor.submit(get_subset_metrics, short_trades),
            ]
            results = [f.result() for f in futures]
            
        all_rows, long_rows, short_rows = results
        
        if not all_rows:
            return "No simulation data available."

        # Format Table
        table = []
        header = f"{'Metric':<25} | {'All Trades':<18} | {'Long':<18} | {'Short':<18}"
        table.append(header)
        table.append("-" * len(header))
        
        for i in range(len(all_rows)):
            label, all_val = all_rows[i]
            long_val = long_rows[i][1] if long_rows else "N/A"
            short_val = short_rows[i][1] if short_rows else "N/A"
            
            # Filter out irrelevant metrics for subsets if needed, 
            # but usually it's best to show everything for comparison.
            table.append(f"{label:<25} | {all_val:<18} | {long_val:<18} | {short_val:<18}")

        # Add symbol summary at the bottom
        if self._raw_result.symbol_summary:
            table.append("\nSymbol Summary:")
            for symbol, row in self._raw_result.symbol_summary.items():
                table.append(
                    f"  {symbol:<10} trades={int(row.get('trades', 0.0)):<5} "
                    f"pnl={float(row.get('pnl', 0.0)):.2f}"
                )
                
        return "\n".join(table)
        
    def print_trades(self):
        """Prints a detailed summary of all trades filled in the portfolio."""
        from backend.services.simulation.results import SimulationRunResult
        from backend.services.simulation.reporting import print_trade_record_summary
        
        if isinstance(self._raw_result, SimulationRunResult):
            print_trade_record_summary(self._raw_result)
        else:
            # Manual print for raw RunResult
            print(f"completed_trades={len(self.trades)}")
            for idx, r in enumerate(self.trades, start=1):
                print(
                    f"trade[{idx}] ticket={r.ticket} symbol={r.symbol} side={r.type} "
                    f"size={r.size:.2f} pnl={r.profit_loss:.2f} mfe={r.mfe_usd:.2f} "
                    f"mae={r.mae_usd:.2f} close_type={r.close_type} exit_reason={r.exit_reason}"
                )

    def print_equity_curve(self):
        """Prints the equity curve points."""
        print(f"equity_points={len(self.equity_curve)}")
        print(f"{'Timestamp':<25} {'Balance':<15} {'Equity':<15}")
        print("-" * 55)
        for p in self.equity_curve:
            ts_str = str(p.timestamp) if p.timestamp else "N/A"
            print(f"{ts_str:<25} {p.balance:<15.2f} {p.equity:<15.2f}")
        
    @classmethod
    def run(cls, config: Optional[Union[Dict[str, Any], Any]] = None, user_id: Optional[int] = None) -> 'Portfolio':
        """
        Run a full simulation. If a config is provided, it overides the defaults.
        
        Args:
            config: Optional simulation configuration overrides.
            user_id: Optional user ID to resolve MT5 credentials.
        """
        from backend.services.simulation.engine import Engine
        
        # Load defaults
        import copy
        full_config = copy.deepcopy(DEFAULT_SIM_CONFIG)
        
        # Apply user overrides
        if config is not None and isinstance(config, dict):
            _deep_merge(full_config, config)
            
        # Determine backend
        backend = full_config.get("backend", "sim")
            
        engine = Engine(backend=backend)
        if backend == "sim":
            engine.fast_mode = True
            
        # If user_id provided, ensure engine is connected with correct credentials
        if user_id is not None:
            from backend.data.database.sqlite.database_operations import DatabaseManager
            db = DatabaseManager()
            creds = db.get_mt5_credentials(user_id)
            if creds and engine.client:
                engine.client.connect(
                    path=creds.get("path", ""),
                    login=int(creds.get("login", 0)),
                    password=creds.get("password", ""),
                    server=creds.get("server", ""),
                )
            
        # Execute simulation
        run_result = engine.run(full_config)
        
        return cls(run_result, initial_balance=run_result.initial_balance)

    @classmethod
    def from_random_signals(
        cls, 
        price: Union[pd.Series, pd.DataFrame], 
        n: Optional[int] = None, 
        prob: Optional[float] = None, 
        init_cash: float = 10000.0, 
        symbol: str = "ASSET",
        seed: Optional[int] = None
    ) -> 'Portfolio':
        """
        Create a portfolio from random signals.
        
        Args:
            price: Price series or single-column DataFrame.
            n: Number of random signals to generate.
            prob: Probability of a signal at each tick (0-1).
            init_cash: Initial cash.
            symbol: Symbol name.
            seed: Random seed for reproducibility.
        """
        from backend.services.simulation.engine import Engine
        
        if len(price) == 0:
            raise ValueError("Price series is empty.")
        if n is None and prob is None:
            n = 10 # Default to 10 random signals
            
        if seed is not None:
            np.random.seed(seed)
            
        price_vals = np.asarray(price).ravel()
        n_ticks = len(price_vals)
        
        # Generate random entries
        entries = np.zeros(n_ticks, dtype=np.int64)
        if prob is not None:
            entries = (np.random.random(n_ticks) < prob).astype(np.int64)
        else:
            # Pick exactly n random indices for entries
            indices = np.random.choice(n_ticks - 1, size=min(n, n_ticks - 1), replace=False)
            entries[indices] = 1
            
        # Generate random exits (simple logic: exit 5 ticks after entry, or random)
        exits = np.zeros(n_ticks, dtype=np.int64)
        entry_indices = np.where(entries == 1)[0]
        for start_idx in entry_indices:
            # Pick a random exit between 1 and 20 ticks after entry
            exit_offset = np.random.randint(1, 21)
            exit_idx = min(start_idx + exit_offset, n_ticks - 1)
            exits[exit_idx] = 1

        # Initialize engine in simulation mode
        engine = Engine(backend="sim")
        engine.fast_mode = True
        
        # Prepare tick data for vectorized engine
        data = pd.DataFrame({
            "bid": price_vals,
            "ask": price_vals,
            "symbol": symbol,
            "entry_signal": entries,
            "exit_signal": exits,
            "is_bar_close": False
        }, index=price.index)
        
        # Ensure final snapshot
        data.iloc[-1, data.columns.get_loc("is_bar_close")] = True
        
        # Run simulation
        engine.run_vectorized(
            data,
            initial_balance=init_cash,
            contract_size=1.0,
            position_size=0.1, # Default 0.1 units
            slippage_model="none"
        )
        
        result = engine.get_run_result(processed_ticks=len(data))
        return cls(result, initial_balance=init_cash)

    @classmethod
    def from_holding(cls, price: Union[pd.Series, pd.DataFrame], init_cash: float = 10000.0, symbol: str = "ASSET") -> 'Portfolio':
        """
        Create a buy-and-hold portfolio from a price series.
        
        Args:
            price: Price series or single-column DataFrame.
            init_cash: Initial cash.
            symbol: Symbol name.
        """
        from backend.services.simulation.engine import Engine
        
        if len(price) == 0:
            raise ValueError("Price series is empty.")
            
        # Ensure price is a 1D array
        price_vals = np.asarray(price).ravel()
        
        # Initialize engine in simulation mode
        engine = Engine(backend="sim")
        engine.fast_mode = True
        
        # Prepare tick data for vectorized engine
        data = pd.DataFrame({
            "bid": price_vals,
            "ask": price_vals,
            "symbol": symbol,
            "is_bar_close": False
        }, index=price.index)
        
        # Signal: Buy at the very first tick
        data["entry_signal"] = 0
        data.iloc[0, data.columns.get_loc("entry_signal")] = 1 # 1 = BUY
        
        # Ensure we take an equity snapshot at the last bar to see unrealized profit
        data.iloc[-1, data.columns.get_loc("is_bar_close")] = True
        
        # Calculate position size to use all initial cash
        # Assuming contract size of 1.0 for simplicity in this utility
        contract_size = 1.0
        pos_size = init_cash / price_vals[0]
        
        # Run simulation
        engine.run_vectorized(
            data,
            initial_balance=init_cash,
            contract_size=contract_size,
            position_size=pos_size,
            slippage_model="none"
        )
        
        result = engine.get_run_result(processed_ticks=len(data))
        return cls(result, initial_balance=init_cash)

class Strategy:
    """Wrapper for HaruQuant strategies to easily access signals."""
    
    def __init__(self, strategy_cls, params: Optional[Dict[str, Any]] = None):
        self.strategy_instance = strategy_cls(params or {})
        self.data: Optional[pd.DataFrame] = None
        self._last_run_config: Optional[Dict[str, Any]] = None
        
    def run(self, data: Union[pd.DataFrame, Data]) -> pd.DataFrame:
        """Run the strategy on the provided data."""
        if isinstance(data, Data):
            df = data.df
        else:
            df = data
            
        self.strategy_instance.on_init()
        self.data = self.strategy_instance.on_bar(df)
        return self.data
        
    def backtest(self, data: Union[pd.DataFrame, Data], init_cash: float = 10000.0) -> Portfolio:
        """Run the strategy and execute a backtest, returning a Portfolio."""
        df = self.run(data)
        
        engine = Engine(backend="sim")
        engine.fast_mode = True
        
        # Determine symbol
        symbol = "STRATEGY"
        if isinstance(data, Data) and data._symbol:
            symbol = data._symbol
            
        # Prepare simulation data
        sim_data = pd.DataFrame({
            "bid": df["close"],
            "ask": df["close"],
            "symbol": symbol,
            "entry_signal": df.get("entry_signal", 0),
            "exit_signal": df.get("exit_signal", 0),
            "is_bar_close": True
        }, index=df.index)
        
        engine.run_vectorized(
            sim_data,
            initial_balance=init_cash,
            position_size=0.1 # Default lot size
        )
        
        result = engine.get_run_result(processed_ticks=len(sim_data))
        return Portfolio(result, initial_balance=init_cash)
        
    @property
    def entries(self) -> pd.Series:
        """Returns the entry signals."""
        if self.data is None:
            raise ValueError("Strategy hasn't been run yet. Call .run(data) first.")
        return self.data.get('entry_signal', pd.Series(0, index=self.data.index))
        
    @property
    def exits(self) -> pd.Series:
        """Returns the exit signals."""
        if self.data is None:
            raise ValueError("Strategy hasn't been run yet. Call .run(data) first.")
        return self.data.get('exit_signal', pd.Series(0, index=self.data.index))
        
    @property
    def pendings(self) -> pd.Series:
        """Returns the pending signals."""
        if self.data is None:
            raise ValueError("Strategy hasn't been run yet. Call .run(data) first.")
        return self.data.get('pending_signal', pd.Series(0, index=self.data.index))

# Import and expose specific strategies
from backend.data.strategies.trend_following import TrendFollowingStrategy as _TrendFollowingStrategy
from backend.data.strategies.breakout import BreakoutStrategy as _BreakoutStrategy
from backend.data.strategies.mean_reversion import MeanReversionStrategy as _MeanReversionStrategy
from backend.data.strategies.close_breakout import CloseBreakoutStrategy as _CloseBreakoutStrategy

class TrendFollowingStrategy(Strategy):
    def __init__(self, params: Optional[Dict[str, Any]] = None):
        super().__init__(_TrendFollowingStrategy, params)

class BreakoutStrategy(Strategy):
    def __init__(self, params: Optional[Dict[str, Any]] = None):
        super().__init__(_BreakoutStrategy, params)

class MeanReversionStrategy(Strategy):
    def __init__(self, params: Optional[Dict[str, Any]] = None):
        super().__init__(_MeanReversionStrategy, params)

class CloseBreakoutStrategy(Strategy):
    def __init__(self, params: Optional[Dict[str, Any]] = None):
        super().__init__(_CloseBreakoutStrategy, params)
