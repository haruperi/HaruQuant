import pandas as pd
import numpy as np
from typing import Dict, Any, Optional, Union, List
from haruquant.data import Data
from backend.services.execution.core import RunResult, EquityPoint

from concurrent.futures import ThreadPoolExecutor

def _deep_merge(base, overrides):
    """Recursively merge two dictionaries."""
    if overrides is None:
        return base
    for key, value in overrides.items():
        if isinstance(value, dict) and key in base and isinstance(base[key], dict):
            _deep_merge(base[key], value)
        else:
            base[key] = value
    return base

DEFAULT_SIM_CONFIG = {
    "backend": "sim",
    "engine_type": "vectorized",
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
    
    def __init__(self, run_result: Union[RunResult, Any], initial_balance: Optional[float] = None):
        self._raw_result = run_result
        
        # Extract initial balance from SimulationRunResult if available
        if initial_balance is None:
            from backend.services.simulation.results import SimulationRunResult
            if isinstance(run_result, SimulationRunResult):
                self.initial_balance = float(run_result.metrics.get("initial_balance", 0.0))
            else:
                self.initial_balance = 0.0 # Fallback for raw RunResult
        else:
            self.initial_balance = initial_balance
        
    @property
    def trades(self) -> List[Any]:
        from backend.services.simulation.results import SimulationRunResult
        if isinstance(self._raw_result, SimulationRunResult):
            return self._raw_result.result.trades
        return self._raw_result.trades
        
    @property
    def equity_curve(self) -> List[Any]:
        from backend.services.simulation.results import SimulationRunResult
        if isinstance(self._raw_result, SimulationRunResult):
            return self._raw_result.result.equity_curve
        return self._raw_result.equity_curve
        
    @property
    def init_cash(self) -> float:
        return self.initial_balance
        
    @property
    def final_value(self) -> float:
        from backend.services.simulation.results import SimulationRunResult
        if isinstance(self._raw_result, SimulationRunResult):
            return float(self._raw_result.metrics.get("final_equity", self.initial_balance))
        return self.equity_curve[-1].equity if self.equity_curve else self.initial_balance
        
    def total_profit(self) -> float:
        """Returns the total net profit (realized + unrealized)."""
        return self.final_value - self.initial_balance
        
    def total_return(self) -> float:
        """Returns the total return as a percentage of initial balance."""
        if self.initial_balance == 0:
            return 0.0
        return (self.total_profit() / self.initial_balance) * 100.0

    def metadata(self) -> Dict[str, Any]:
        """Returns the simulation metadata as a formatted dictionary."""
        from backend.services.simulation.results import SimulationRunResult
        from dataclasses import asdict
        from datetime import datetime

        if not isinstance(self._raw_result, SimulationRunResult):
            return {}

        def _serialize(obj):
            if isinstance(obj, datetime):
                return obj.isoformat()
            if isinstance(obj, dict):
                return {k: _serialize(v) for k, v in obj.items()}
            if isinstance(obj, (list, tuple)):
                return [_serialize(x) for x in obj]
            if hasattr(obj, "__dataclass_fields__"):
                return _serialize(asdict(obj))
            return obj

        return _serialize(dict(self._raw_result.metadata))

    def analytics(self) -> Dict[str, Any]:
        """Returns comprehensive simulation analytics as a formatted dictionary."""
        from backend.services.simulation.results import SimulationRunResult
        from backend.services.analytics.overview import get_analytics_overview
        
        if not isinstance(self._raw_result, SimulationRunResult):
            return {}
            
        meta = self.metadata()
        start_time = meta.get("data", {}).get("start")
        end_time = meta.get("data", {}).get("end")
        
        return get_analytics_overview(
            trades=self.trades,
            initial_balance=self.initial_balance,
            start_time=start_time,
            end_time=end_time
        )

    def metrics(self) -> Dict[str, Any]:
        """Returns the simulation metrics as a dictionary."""
        from backend.services.simulation.results import SimulationRunResult
        if isinstance(self._raw_result, SimulationRunResult):
            return dict(self._raw_result.metrics)
        return {}

    def prepared(self) -> Dict[str, Any]:
        """
        Returns the prepared simulation data as a dictionary.
        DataFrames are kept as-is to ensure they 'show well' with Pandas truncation.
        """
        from backend.services.simulation.results import SimulationRunResult
        from dataclasses import asdict
        from datetime import datetime

        if not isinstance(self._raw_result, SimulationRunResult):
            return {}

        def _serialize(obj):
            if isinstance(obj, datetime):
                return obj.isoformat()
            if isinstance(obj, pd.DataFrame):
                return obj  # Keep as DataFrame for better display/performance
            if isinstance(obj, dict):
                return {k: _serialize(v) for k, v in obj.items()}
            if isinstance(obj, (list, tuple)):
                return [_serialize(x) for x in obj]
            if hasattr(obj, "__dataclass_fields__"):
                return _serialize(asdict(obj))
            return obj

        return _serialize(asdict(self._raw_result.prepared))

    def result(self) -> Dict[str, Any]:
        """
        Returns the core execution outputs (trades and equity curve) as a dictionary.
        Both are returned as Pandas DataFrames.
        """
        from dataclasses import asdict
        from backend.services.simulation.results import SimulationRunResult
        
        if isinstance(self._raw_result, SimulationRunResult):
            res = self._raw_result.result
        else:
            res = self._raw_result
        
        # Convert lists of dataclasses to DataFrames
        trades_df = pd.DataFrame([asdict(t) for t in res.trades]) if res.trades else pd.DataFrame()
        equity_df = pd.DataFrame([asdict(p) for p in res.equity_curve]) if res.equity_curve else pd.DataFrame()
        
        return {
            "trades": trades_df,
            "equity_curve": equity_df,
        }

    def snapshot(self) -> Dict[str, Any]:
        """
        Returns a JSON-ready snapshot of the portfolio result.

        This is the canonical payload for database persistence:
        metadata + result + analytics.
        """
        import json

        def _frame_to_records(frame: pd.DataFrame) -> list[dict[str, Any]]:
            if frame.empty:
                return []
            return json.loads(frame.to_json(orient="records", date_format="iso"))

        result = self.result()
        return {
            "metadata": self.metadata(),
            "result": {
                "trades": _frame_to_records(result["trades"]),
                "equity_curve": _frame_to_records(result["equity_curve"]),
            },
            "analytics": self.analytics(),
        }

    def summary(self) -> str:
        """Returns a formatted summary table of All, Long, and Short results."""
        from backend.services.simulation.results import SimulationRunResult
        from backend.services.analytics.overview import format_summary_as_rows, calculate_analytics_for_subset
        
        if not isinstance(self._raw_result, SimulationRunResult):
            # Fallback for simple RunResult (e.g. from_holding)
            return (
                f"Backtest Summary\n"
                f"{'-'*30}\n"
                f"Initial Balance: {self.initial_balance:.2f}\n"
                f"Final Equity:    {self.final_value:.2f}\n"
                f"Total Profit:    {self.total_profit():.2f}\n"
                f"Total Return:    {self.total_return():.2f}%\n"
                f"Number of Trades: {len(self.trades)}\n"
            )
            
        # Filter trades
        all_trades = self.trades
        long_trades = [t for t in all_trades if str(t.type).lower() == "buy"]
        short_trades = [t for t in all_trades if str(t.type).lower() == "sell"]
        
        meta = self.metadata()
        data_config = meta.get("data", {})
        period_start = pd.Timestamp(data_config.get("start")) if data_config.get("start") else None
        period_end = pd.Timestamp(data_config.get("end")) if data_config.get("end") else None
        
        # Parallel Calculation Helper
        def get_subset_metrics(trades_subset, *, is_all: bool = False):
            if not trades_subset and not is_all:
                return None

            # Convert trades to list of dicts for the calculator
            from dataclasses import asdict
            trade_records = [asdict(t) for t in trades_subset] if trades_subset else []
            
            # Calculate analytics for this subset
            analytics = calculate_analytics_for_subset(
                pd.DataFrame(trade_records),
                initial_balance=self.initial_balance,
                start_time=period_start,
                end_time=period_end
            )
            
            return format_summary_as_rows(analytics["summary"])

        # Run All, Long, and Short in parallel
        with ThreadPoolExecutor(max_workers=3) as executor:
            futures = [
                executor.submit(get_subset_metrics, all_trades, is_all=True),
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
        metrics = self.metrics()
        symbol_summary = metrics.get("symbol_summary", {})
        if symbol_summary:
            table.append("\nSymbol Summary:")
            for symbol, row in symbol_summary.items():
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
            # In the new structure, we can pass the metrics directly or handle locally
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

    def slice(self, start: Union[str, datetime, pd.Timestamp], end: Union[str, datetime, pd.Timestamp]) -> 'Portfolio':
        """
        Create a new Portfolio by slicing the current one by date range.
        
        Args:
            start: Start date of the slice.
            end: End date of the slice.
            
        Returns:
            A new Portfolio object containing only data from the specified range.
        """
        from backend.services.simulation.results import SimulationRunResult, build_symbol_summary
        from backend.services.execution.core import RunResult, EquityPoint
        import copy
        
        # Parse dates
        start_ts = pd.Timestamp(start)
        end_ts = pd.Timestamp(end)
        
        # Filter trades: exit time within range
        # Filter trades: exit time within range
        filtered_trades = [t for t in self.trades if start_ts <= pd.Timestamp(t.close_time) <= end_ts]
        
        # 1. Correct new_initial_balance: the equity at EXACTLY start_ts
        # We find the last equity point before or at start_ts in the original curve
        pre_points = [p for p in self.equity_curve if pd.Timestamp(p.timestamp) <= start_ts]
        if pre_points:
            new_initial_balance = pre_points[-1].equity
            start_balance = pre_points[-1].balance
        else:
            new_initial_balance = self.initial_balance
            start_balance = self.initial_balance

        # 2. Reconstruct filtered_equity to span the full window [start_ts, end_ts]
        # This ensures time-based metrics (CAGR) are accurate even for sparse results.
        start_point = EquityPoint(
            timestamp=start_ts.to_pydatetime(), 
            balance=float(start_balance),
            equity=float(new_initial_balance)
        )
                                 
        mid_points = [p for p in self.equity_curve if start_ts < pd.Timestamp(p.timestamp) < end_ts]
        
        last_points = [p for p in self.equity_curve if pd.Timestamp(p.timestamp) <= end_ts]
        if last_points:
             end_val = last_points[-1].equity
             end_bal = last_points[-1].balance
        else:
             end_val = new_initial_balance
             end_bal = start_balance

        end_point = EquityPoint(
            timestamp=end_ts.to_pydatetime(),
            balance=float(end_bal),
            equity=float(end_val)
        )
        
        filtered_equity = [start_point] + mid_points + [end_point]

        # Construct a new result object
        new_run_result = RunResult(
            trades=filtered_trades,
            equity_curve=filtered_equity
        )
        
        if isinstance(self._raw_result, SimulationRunResult):
            # Recalculate metrics for the slice
            meta = self.metadata()
            symbols = tuple(meta.get("data", {}).get("symbols", []))
            
            final_equity = filtered_equity[-1].equity if filtered_equity else new_initial_balance
            final_balance = filtered_equity[-1].balance if filtered_equity else new_initial_balance
            
            new_metrics = {
                "processed_ticks": len(filtered_equity),
                "trade_count": len(filtered_trades),
                "equity_points": len(filtered_equity),
                "initial_balance": float(new_initial_balance),
                "final_balance": float(final_balance),
                "final_equity": float(final_equity),
                "total_profit": float(final_equity - new_initial_balance),
                "total_return": (
                    float((final_equity - new_initial_balance) / new_initial_balance)
                    if new_initial_balance > 0.0
                    else 0.0
                ),
                "symbol_summary": build_symbol_summary(symbols, filtered_trades),
            }
            
            # Update metadata
            new_metadata = copy.deepcopy(meta)
            new_metadata["data"]["start"] = start_ts.isoformat()
            new_metadata["data"]["end"] = end_ts.isoformat()
            
            # Create the sliced SimulationRunResult
            sliced_run_result = SimulationRunResult(
                metadata=new_metadata,
                prepared=self._raw_result.prepared,
                result=new_run_result,
                metrics=new_metrics
            )
            return Portfolio(sliced_run_result, initial_balance=new_initial_balance)
        else:
            # Fallback for simple RunResult (e.g. from_holding)
            return Portfolio(new_run_result, initial_balance=new_initial_balance)
        
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
        preloaded_bars = None
        if config is not None and isinstance(config, dict):
            # Extract preloaded data if present to avoid merging it into metadata
            preloaded_bars = config.pop("preloaded_data", None)
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
        if preloaded_bars is not None:
            # If we have preloaded bars, we use the engine's lower level run_prepared logic
            # but for now we'll just inject it into the runner if it supported it.
            # Since we want to simplify execution.py, let's make the engine.run handle it.
            full_config["preloaded_data"] = preloaded_bars
            
        run_result = engine.run(full_config)
        
        return cls(run_result)

    @classmethod
    def from_random_signals(
        cls, 
        price: Union[pd.Series, pd.DataFrame], 
        n: Optional[Union[int, List[int]]] = None, 
        prob: Optional[float] = None, 
        init_cash: float = 10000.0, 
        symbol: str = "ASSET",
        seed: Optional[int] = None,
        chunked: Optional[str] = None
    ) -> Union['Portfolio', List['Portfolio']]:
        """
        Create a portfolio from random signals.
        
        Args:
            price: Price series or single-column DataFrame.
            n: Number of random signals to generate. Can be a list of ints for multiple simulations.
            prob: Probability of a signal at each tick (0-1).
            init_cash: Initial cash.
            symbol: Symbol name.
            seed: Random seed for reproducibility.
            chunked: Execution backend for multiple simulations ('threadpool', None).
        """
        from backend.services.simulation.engine import Engine
        from concurrent.futures import ThreadPoolExecutor

        if len(price) == 0:
            raise ValueError("Price series is empty.")

        # Handle multiple simulations
        if isinstance(n, (list, tuple, np.ndarray)):
            # If a list of n is provided, we run multiple simulations
            seeds = [seed + i if seed is not None else None for i in range(len(n))]
            
            def run_single(n_val, s_val):
                return cls.from_random_signals(price, n=n_val, prob=prob, init_cash=init_cash, symbol=symbol, seed=s_val)

            if chunked == "threadpool":
                with ThreadPoolExecutor() as executor:
                    return list(executor.map(run_single, n, seeds))
            else:
                return [run_single(nv, sv) for nv, sv in zip(n, seeds)]

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
