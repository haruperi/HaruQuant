# Backtest Performance Optimization Roadmap

This document outlines actionable optimization tasks to make the HaruQuant backtesting engine blazing fast. Tasks are organized by priority and expected impact.

---

## Overview

**Current State:** Event-driven backtest with pure Python loops, pandas DataFrame access in hot paths, and redundant data structures.

**Target State:** NumPy-based simulation core with optional Numba JIT compilation, achieving 50-100x speedup on large datasets.

**Benchmark Target:**
- 1 year daily data (252 bars): < 10ms
- 10 years daily data (2,520 bars): < 100ms
- 1 year minute data (98,280 bars): < 1 second
- 10 years minute data (982,800 bars): < 10 seconds

---

## Phase 1: Quick Wins (1-2 days) ✅ COMPLETED

These changes require minimal refactoring and provide immediate performance gains.

### 1.1 Convert DataFrames to NumPy Arrays Before Main Loop ✅

**File:** `apps/backtest/engine/event_driven.py`, `apps/backtest/engine/vectorized.py`
**Location:** `_run_backtest_loop()` and `_simulate_trades()`
**Impact:** 10-20x speedup
**Effort:** Low
**Status:** ✅ IMPLEMENTED

- [x] Extract OHLCV + spread columns to NumPy arrays before the loop
- [x] Replace `execution_data.iloc[i]` with `_get_bar_from_arrays(i)` helper
- [x] Update all bar access patterns to use arrays
- [x] Added spread column support for broker spread simulation

**Implementation:**
```python
# Before main loop, add:
self._closes = self.execution_data["close"].values
self._highs = self.execution_data["high"].values
self._lows = self.execution_data["low"].values
self._opens = self.execution_data["open"].values
self._volumes = self.execution_data["volume"].values if "volume" in self.execution_data.columns else None
self._timestamps = self.execution_data.index.values

# In loop, replace:
# bar = execution_data.iloc[i]
# With:
# close, high, low, open_ = self._closes[i], self._highs[i], self._lows[i], self._opens[i]
```

---

### 1.2 Pre-Index Signals by Bar Index ✅

**File:** `apps/backtest/engine/vectorized.py`
**Location:** `_extract_signals()` and `_process_bar_signals()`
**Impact:** O(n) → O(1) per bar lookup
**Effort:** Low
**Status:** ✅ IMPLEMENTED

- [x] Build signal index dictionary during setup phase
- [x] Replace list comprehension filter with dictionary lookup
- [x] `_signal_index` dict provides O(1) signal lookup by bar index

**Implementation:**
```python
# During setup (after signal generation):
from collections import defaultdict
self._signal_index = defaultdict(list)
for s in self._signals:
    self._signal_index[s["bar_index"]].append(s)

# In loop, replace:
# bar_signals = [s for s in self._signals if s["bar_index"] == i]
# With:
# bar_signals = self._signal_index.get(i, [])
```

---

### 1.3 Use itertuples() Instead of iloc[] (Fallback) ⏭️

**File:** `apps/backtest/engine/event_driven.py`
**Location:** Lines 448-450
**Impact:** 3-5x speedup (if NumPy conversion not possible)
**Effort:** Low
**Status:** ⏭️ SKIPPED - NumPy array approach (1.1) is faster

- [x] Not needed - we implemented the better NumPy array approach instead
- [x] `_get_bar_from_arrays()` helper is 10-20x faster than itertuples()

---

### 1.4 Pre-Allocate Equity Curve Array ✅

**File:** `apps/backtest/engine/base.py`
**Location:** `__init__()`, `_record_equity_point()`, `_build_result()`
**Impact:** Reduces GC pressure, ~2x speedup on equity tracking
**Effort:** Low
**Status:** ✅ IMPLEMENTED

- [x] Pre-allocate NumPy array for equity curve at start (`_equity_array`)
- [x] Replace `_equity_points.append()` with array assignment
- [x] Convert to EquityPoint objects only at the end in `_build_result()`
- [x] Added fallback for edge cases where array overflows

**Implementation:**
```python
# Setup:
n_bars = len(self.execution_data)
self._equity_array = np.zeros((n_bars, 3), dtype=np.float64)  # [timestamp_idx, balance, equity]

# In loop:
self._equity_array[i] = [i, self._balance, self._equity]

# After loop (if EquityPoint objects needed):
self._equity_points = [
    EquityPoint(self._timestamps[int(row[0])], row[1], row[2])
    for row in self._equity_array
]
```

---

### 1.5 Remove Debug Logging from Hot Path ✅

**File:** `apps/backtest/engine/event_driven.py`
**Location:** Hot path debug logging calls
**Impact:** 5-10% speedup
**Effort:** Low
**Status:** ✅ IMPLEMENTED

- [x] Use `__debug__` flag (Python optimizes out in `-O` mode) before debug logging
- [x] Updated signal skip logging in main loop
- [x] Updated progress logging
- [x] Updated P&L calculation debug logging

**Implementation:**
```python
# Use __debug__ flag which Python optimizes out when running with -O
# This avoids f-string formatting overhead in production

# Replace:
# logger.debug(f"Processing signal at {timestamp}: {signal_details}")

# With:
if __debug__:
    logger.debug(f"Processing signal at {timestamp}: {signal_details}")
```

**Note:** Running Python with `-O` flag completely removes these debug blocks at compile time.

---

## Phase 2: Data Structure Refactoring (2-3 days) ✅ COMPLETED

These changes require moderate refactoring but significantly improve maintainability and performance.

### 2.1 Consolidate Position State into Single Data Structure ✅

**Files:** `apps/backtest/engine/position.py` (NEW), `apps/backtest/engine/event_driven.py`
**Location:** New `Position` dataclass and `PositionManager` class
**Impact:** 50% memory reduction, eliminates sync bugs, cleaner code
**Effort:** Medium
**Status:** ✅ IMPLEMENTED

- [x] Create `Position` dataclass with all required fields
- [x] Use `slots=True` for memory efficiency (~40% less memory)
- [x] Created `PositionManager` class with NumPy arrays for vectorized P&L
- [x] Integrated with EventDrivenEngine (maintains backward compatibility)
- [x] Legacy `_open_positions` kept for gradual migration

**Implementation:**
```python
from dataclasses import dataclass
from typing import Optional
from datetime import datetime

@dataclass(slots=True)
class Position:
    ticket: int
    symbol: str
    direction: int  # 1=long, -1=short
    volume: float
    price_open: float
    entry_time: datetime
    price_current: float = 0.0
    sl: Optional[float] = None
    tp: Optional[float] = None
    profit: float = 0.0
    highest_price: float = 0.0
    lowest_price: float = float('inf')
    entry_slippage: float = 0.0
    margin_required: float = 0.0
    equity_at_entry: float = 0.0
    spread_at_entry: float = 0.0
    magic: int = 0
    comment: str = ""

    def update_pnl(self, current_price: float, contract_size: float = 1.0) -> float:
        self.price_current = current_price
        self.profit = (current_price - self.price_open) * self.direction * self.volume * contract_size
        self.highest_price = max(self.highest_price, current_price)
        self.lowest_price = min(self.lowest_price, current_price)
        return self.profit
```

---

### 2.2 Standardize Type Representations ✅

**Files:** `apps/backtest/engine/position.py`, `apps/backtest/engine/event_driven.py`
**Impact:** Eliminates conversion overhead, reduces bugs
**Effort:** Medium
**Status:** ✅ IMPLEMENTED

- [x] Use consistent direction representation: `1` for long, `-1` for short everywhere
- [x] `Position` dataclass uses `direction` (1/-1) as canonical representation
- [x] Added `type` property for backward compatibility (returns 0/1)
- [x] Helper functions `direction_from_type()` and `type_from_direction()` for conversion

**New standard:**
- `direction = 1` → Long/Buy
- `direction = -1` → Short/Sell
- Legacy `type = 0` → Buy, `type = 1` → Sell (via property)

---

### 2.3 Vectorize Position P&L Updates ✅

**File:** `apps/backtest/engine/position.py`, `apps/backtest/engine/event_driven.py`
**Location:** `PositionManager.update_all_pnl()` and `_update_positions()`
**Impact:** O(n) → O(1) for position updates with NumPy
**Effort:** Medium
**Status:** ✅ IMPLEMENTED

- [x] Store position data in parallel NumPy arrays in `PositionManager`
- [x] Use vectorized operations for P&L calculation
- [x] Arrays: `_entries`, `_volumes`, `_directions`, `_pnls`, `_highest`, `_lowest`
- [x] `update_all_pnl()` method updates all positions in single NumPy operation
- [x] Automatic array expansion when capacity exceeded

**Implementation:**
```python
class PositionArrays:
    """Vectorized position storage for fast updates."""
    def __init__(self, max_positions: int = 100):
        self.entries = np.zeros(max_positions, dtype=np.float64)
        self.volumes = np.zeros(max_positions, dtype=np.float64)
        self.directions = np.zeros(max_positions, dtype=np.int8)
        self.pnls = np.zeros(max_positions, dtype=np.float64)
        self.count = 0

    def update_all_pnl(self, current_price: float, contract_size: float = 1.0):
        """Vectorized P&L update for all positions."""
        active = slice(0, self.count)
        self.pnls[active] = (
            (current_price - self.entries[active]) *
            self.volumes[active] *
            self.directions[active] *
            contract_size
        )
```

---

### 2.4 Eliminate Backward Compatibility Sync Loops ✅

**File:** `apps/backtest/engine/event_driven.py`, `apps/backtest/engine/position.py`
**Location:** `_update_positions()`, `_check_stops()`, `_handle_exit_signal()`, `_process_entry_signal()`
**Impact:** Restores O(1) vectorized updates, fixes performance regression
**Effort:** Medium
**Status:** ✅ IMPLEMENTED

The initial Phase 2 implementation had O(n) sync loops that synced data back to legacy
`_trade_provider._positions` and `_open_positions` dictionaries on every bar, negating
the vectorized P&L benefits.

**Fix applied:**
- [x] Removed O(n) sync loops from `_update_positions()`
- [x] Updated `_check_stops()` to iterate over `PositionManager` directly
- [x] Created `_close_position_at_price_v2()` using Position objects
- [x] Created `_record_position_close_v2()` using Position objects
- [x] Updated `_handle_exit_signal()` to use PositionManager
- [x] Updated `_process_entry_signal()` to use PositionManager
- [x] Updated `_close_all_positions()` to use PositionManager
- [x] Added `entry_bar_index` field to Position dataclass
- [x] Added `sync_position()` method for lazy sync when closing positions

**Performance comparison (10,000 bars):**
- Phase 2 (broken with sync loops): 5,375ms
- Phase 2 (fixed, no sync loops): 3,458ms
- **Improvement: 1.6x faster**

---

## Phase 3: Core Simulation Engine (3-5 days) ✅ COMPLETED

Major refactoring to create a blazing fast simulation core.

**Status:** Core module completed and integrated with VectorizedEngine.

### 3.1 Create Fast Simulation Core Module ✅

**New Files:**
- `apps/backtest/engine/core/__init__.py`
- `apps/backtest/engine/core/simulator.py`
- `apps/backtest/engine/core/types.py`
- `apps/backtest/engine/core/signals.py`

**Impact:** Foundation for 50-100x speedup
**Effort:** High
**Status:** ✅ IMPLEMENTED

- [x] Create `core/` directory structure
- [x] Define NumPy-friendly data types in `types.py`
- [x] Implement pure-NumPy simulation loop in `simulator.py`
- [x] Design clean interface for engine integration

**Directory Structure:**
```
apps/backtest/engine/
├── core/
│   ├── __init__.py
│   ├── simulator.py      # Pure NumPy simulation
│   └── types.py          # Data structures
├── event_driven.py       # Uses core.simulator
├── vectorized.py         # Uses core.simulator
└── base.py
```

---

### 3.2 Implement Numba JIT-Compiled Simulation ✅

**File:** `apps/backtest/engine/core/simulator.py`
**Impact:** 50-100x speedup on core loop
**Effort:** High
**Status:** ✅ IMPLEMENTED

- [x] Add `numba` to project dependencies (numba 0.63.1)
- [x] Implement JIT-compiled `_simulate_core()` function with `@njit(cache=True)`
- [x] Handle edge cases (no positions, single bar, end-of-data positions)
- [x] Add fallback for systems without Numba (pure Python/NumPy)

**Benchmark Results:**
- Core simulator: ~2,000,000 bars/sec
- EventDrivenEngine: ~2,500 bars/sec
- **Speedup: 800x faster** (raw core simulation)

**Implementation:**
```python
from numba import njit
import numpy as np

@njit(cache=True)
def run_simulation(
    opens: np.ndarray,
    highs: np.ndarray,
    lows: np.ndarray,
    closes: np.ndarray,
    signals: np.ndarray,
    stop_losses: np.ndarray,
    take_profits: np.ndarray,
    sizes: np.ndarray,
    initial_balance: float,
    commission_pct: float,
    slippage_pct: float,
) -> tuple:
    """
    JIT-compiled trade simulation.

    Args:
        opens/highs/lows/closes: OHLC price arrays
        signals: 1=buy, -1=sell, 0=hold for each bar
        stop_losses/take_profits: SL/TP prices per bar
        sizes: Position size per bar
        initial_balance: Starting capital
        commission_pct: Commission as percentage
        slippage_pct: Slippage as percentage

    Returns:
        (equity_curve, trades_array, final_balance)
    """
    n = len(closes)
    equity = np.zeros(n, dtype=np.float64)
    trades = np.zeros((n, 8), dtype=np.float64)
    # [entry_bar, exit_bar, direction, entry_price, exit_price, pnl, sl, tp]
    trade_count = 0

    balance = initial_balance
    position = 0.0
    entry_bar = 0
    entry_price = 0.0
    current_sl = 0.0
    current_tp = 0.0

    for i in range(n):
        # Exit logic
        if position != 0:
            exit_price = 0.0
            should_exit = False

            if position > 0:  # Long
                if lows[i] <= current_sl and current_sl > 0:
                    exit_price = current_sl
                    should_exit = True
                elif highs[i] >= current_tp and current_tp > 0:
                    exit_price = current_tp
                    should_exit = True
                elif signals[i] == -1:
                    exit_price = closes[i] * (1 - slippage_pct)
                    should_exit = True
            else:  # Short
                if highs[i] >= current_sl and current_sl > 0:
                    exit_price = current_sl
                    should_exit = True
                elif lows[i] <= current_tp and current_tp > 0:
                    exit_price = current_tp
                    should_exit = True
                elif signals[i] == 1:
                    exit_price = closes[i] * (1 + slippage_pct)
                    should_exit = True

            if should_exit:
                pnl = (exit_price - entry_price) * position
                pnl -= abs(pnl) * commission_pct
                balance += pnl

                trades[trade_count, 0] = entry_bar
                trades[trade_count, 1] = i
                trades[trade_count, 2] = 1.0 if position > 0 else -1.0
                trades[trade_count, 3] = entry_price
                trades[trade_count, 4] = exit_price
                trades[trade_count, 5] = pnl
                trades[trade_count, 6] = current_sl
                trades[trade_count, 7] = current_tp
                trade_count += 1
                position = 0.0

        # Entry logic
        if position == 0 and signals[i] != 0:
            direction = signals[i]
            slippage = opens[i] * slippage_pct
            entry_price = opens[i] + slippage * direction
            position = sizes[i] * direction
            current_sl = stop_losses[i]
            current_tp = take_profits[i]
            entry_bar = i
            balance -= abs(position * entry_price) * commission_pct

        # Mark-to-market
        if position != 0:
            unrealized = (closes[i] - entry_price) * position
            equity[i] = balance + unrealized
        else:
            equity[i] = balance

    return equity, trades[:trade_count], balance
```

---

### 3.3 Signal Preparation Module ✅

**File:** `apps/backtest/engine/core/signals.py`
**Impact:** Clean signal → array conversion
**Effort:** Medium
**Status:** ✅ IMPLEMENTED

- [x] Create function to convert strategy signals to NumPy arrays
- [x] Handle multiple signal types (entry, exit, SL, TP)
- [x] Support both vectorized and event-driven signal formats
- [x] `prepare_signals_from_dataframe()` - for DataFrame signals
- [x] `prepare_signals_from_list()` - for list of signal dicts
- [x] `prepare_simulation_inputs()` - combines OHLC and signals

**Implementation:**
```python
import numpy as np
import pandas as pd

def prepare_signal_arrays(
    data: pd.DataFrame,
    signals: pd.DataFrame,
    default_sl_pct: float = 0.02,
    default_tp_pct: float = 0.04,
    default_size: float = 1.0,
) -> dict:
    """
    Convert strategy signals to NumPy arrays for fast simulation.

    Returns dict with:
        - signals: int8 array (1=buy, -1=sell, 0=hold)
        - stop_losses: float64 array
        - take_profits: float64 array
        - sizes: float64 array
    """
    n = len(data)
    result = {
        'signals': np.zeros(n, dtype=np.int8),
        'stop_losses': np.zeros(n, dtype=np.float64),
        'take_profits': np.zeros(n, dtype=np.float64),
        'sizes': np.full(n, default_size, dtype=np.float64),
    }

    closes = data['close'].values

    # Map signals
    if 'entry_long' in signals.columns:
        long_mask = signals['entry_long'].values.astype(bool)
        result['signals'][long_mask] = 1
        result['stop_losses'][long_mask] = closes[long_mask] * (1 - default_sl_pct)
        result['take_profits'][long_mask] = closes[long_mask] * (1 + default_tp_pct)

    if 'entry_short' in signals.columns:
        short_mask = signals['entry_short'].values.astype(bool)
        result['signals'][short_mask] = -1
        result['stop_losses'][short_mask] = closes[short_mask] * (1 + default_sl_pct)
        result['take_profits'][short_mask] = closes[short_mask] * (1 - default_tp_pct)

    if 'exit_long' in signals.columns:
        result['signals'][signals['exit_long'].values.astype(bool)] = -1

    if 'exit_short' in signals.columns:
        result['signals'][signals['exit_short'].values.astype(bool)] = 1

    # Override with explicit SL/TP if provided
    if 'sl' in signals.columns:
        mask = ~signals['sl'].isna()
        result['stop_losses'][mask] = signals.loc[mask, 'sl'].values

    if 'tp' in signals.columns:
        mask = ~signals['tp'].isna()
        result['take_profits'][mask] = signals.loc[mask, 'tp'].values

    return result
```

---

### 3.4 Integrate Core Simulator with Existing Engines ✅

**Files:** `vectorized.py`
**Impact:** Unified fast simulation for VectorizedEngine
**Effort:** Medium
**Status:** ✅ COMPLETED

- [x] Core simulator module created and tested
- [x] VectorizedEngine refactored to use core simulator
- [x] EventDrivenEngine remains full-featured (uses Phase 1 & 2 optimizations)
- [x] Legacy `run_legacy()` method preserved for comparison

**Architecture:**
```
┌─────────────────────────────────────────────────────────────┐
│                    Backtest Engines                          │
├─────────────────────────────┬───────────────────────────────┤
│     EventDrivenEngine       │      VectorizedEngine         │
│  (Full-featured, accurate)  │   (Fast, for optimization)    │
├─────────────────────────────┼───────────────────────────────┤
│  - Swap calculation         │  - Uses core/ simulator       │
│  - Pending orders           │  - Numba JIT compiled         │
│  - Accurate slippage        │  - ~60,000 bars/sec           │
│  - on_tick() callback       │  - Simplified cost model      │
│  - Phase 1 & 2 optimized    │  - 15-22x faster than legacy  │
│  - ~2,700 bars/sec          │                               │
└─────────────────────────────┴───────────────────────────────┘
```

**VectorizedEngine Benchmark Results:**
| Bars | Core Simulator | Legacy Python | EventDriven | Speedup |
|------|----------------|---------------|-------------|---------|
| 1,000 | 28ms (35k/s) | 258ms | 344ms | **12x** |
| 10,000 | 213ms (47k/s) | 2,468ms | 3,611ms | **17x** |
| 50,000 | 839ms (60k/s) | 13,228ms | 18,485ms | **22x** |

**Usage:**
```python
from apps.backtest.engine.vectorized import VectorizedEngine

# Fast mode (default) - uses Numba JIT core simulator
result = engine.run()

# Legacy mode - uses Python loop (for comparison/debugging)
result = engine.run_legacy()
```

---

## Phase 4: Advanced Optimizations (1-2 weeks) ✅ COMPLETED

Long-term improvements for maximum performance.

**Status:** Core optimizations completed. Optional GPU and Cython features deferred.

### 4.1 Parallel Backtesting Support ✅

**File:** `apps/backtest/parallel.py`
**Impact:** Linear speedup with CPU cores (6-7x on 8 cores expected)
**Effort:** High
**Status:** ✅ IMPLEMENTED

- [x] Implement `concurrent.futures` based parallel execution
- [x] Add `multiprocessing` option for true parallelism
- [x] Create `ParallelBacktester` class
- [x] Handle result aggregation efficiently
- [x] Created example usage script (`tests/usage/backtest/12_parallel_execution.py`)

**Implementation:**
```python
from apps.backtest.parallel import ParallelBacktester, BacktestTask

# Initialize parallel backtester
parallel = ParallelBacktester(max_workers=4)

# Run parameter sweep
results = parallel.run_parameter_sweep(
    strategy_class=MyStrategy,
    data=data,
    parameter_grid={
        "fast_period": [10, 20, 30],
        "slow_period": [50, 100, 200]
    },
    engine_type="vectorized"
)

# Find best parameters
best_params = parallel.get_best_parameters(results, metric="total_return_pct")
```

**Features:**
- `run_batch()` - Execute multiple backtests in parallel
- `run_parameter_sweep()` - Optimize strategy parameters
- `run_portfolio()` - Backtest multiple symbols simultaneously
- Automatic worker pool management
- Exception handling and error reporting
- Progress tracking with tqdm

---

### 4.2 GPU Acceleration with CuPy (Optional) ⏭️

**New File:** `apps/backtest/engine/core/gpu_simulator.py`
**Impact:** 10-100x speedup for massive datasets
**Effort:** Very High
**Status:** ⏭️ DEFERRED - Not needed for current use cases

- [ ] Add optional CuPy dependency
- [ ] Implement GPU-accelerated simulation kernel
- [ ] Add automatic CPU/GPU selection based on data size
- [ ] Handle GPU memory management

**Note:** Only beneficial for datasets > 1M bars or batch optimization. Current Numba JIT implementation (Phase 3) provides sufficient performance.

---

### 4.3 Cython Compilation for Critical Paths ⏭️

**New Files:** `apps/backtest/engine/core/_simulator.pyx`
**Impact:** Alternative to Numba, ~50x speedup
**Effort:** High
**Status:** ⏭️ DEFERRED - Numba provides equivalent performance

- [ ] Identify functions that can't be Numba-compiled
- [ ] Create Cython versions of critical functions
- [ ] Add build configuration for Cython compilation
- [ ] Benchmark against Numba implementation

**Note:** Numba JIT (Phase 3) already provides 800x speedup on core simulation. Cython would add build complexity without significant additional benefit.

---

### 4.4 Memory-Mapped Data Loading ✅

**File:** `apps/backtest/data_loader.py`
**Impact:** Handle datasets larger than RAM
**Effort:** Medium
**Status:** ✅ IMPLEMENTED

- [x] Implement memory-mapped file reading with `np.memmap`
- [x] Add chunked processing for very large datasets
- [x] Support streaming data for live simulation testing
- [x] Support multiple formats (CSV, Parquet, HDF5)
- [x] Automatic caching and preprocessing

**Implementation:**
```python
from apps.backtest.data_loader import MemoryMappedDataLoader

# Initialize loader
loader = MemoryMappedDataLoader(cache_dir=".cache/backtest_data")

# Load large dataset with memory mapping
data = loader.load_mmap("large_dataset.csv")

# Or iterate in chunks
for chunk in loader.load_chunked("large_dataset.csv", chunk_size=10000):
    result = engine.run(chunk)
```

**Features:**
- `load_mmap()` - Load data as memory-mapped array
- `load_chunked()` - Iterator for chunk-based processing
- `preprocess_and_cache()` - Pre-process and cache for fast access
- Automatic format detection (CSV, Parquet, HDF5)
- Cache management with size limits

---

### 4.5 Result Caching and Incremental Updates ✅

**Files:** `apps/backtest/cache.py`, `apps/backtest/result.py`
**Impact:** Avoid redundant calculations, 10-100x speedup for repeated runs
**Effort:** Medium
**Status:** ✅ IMPLEMENTED

- [x] Cache intermediate results (equity curve, trade stats)
- [x] Implement incremental metric updates
- [x] Add result serialization for fast reload
- [x] Use `functools.lru_cache` for expensive calculations
- [x] Created `ResultCache` class with LRU eviction
- [x] Added serialization methods to `BacktestResult`

**Implementation:**
```python
from apps.backtest.cache import ResultCache, compute_data_hash

# Initialize cache
cache = ResultCache(max_size_mb=1000, max_age_days=30)

# Try to get cached result
data_hash = compute_data_hash(data)
result = cache.get(
    strategy_name="MyStrategy",
    symbol="EURUSD",
    params={"fast_period": 10},
    data_hash=data_hash
)

if result is None:
    # Run backtest
    result = engine.run()

    # Cache for future use
    cache.put(result, strategy_name="MyStrategy", symbol="EURUSD", params={"fast_period": 10}, data_hash=data_hash)
```

**Features:**
- Disk-based cache with LRU eviction
- Configurable cache size limits
- Cache statistics and monitoring
- Automatic cleanup of stale entries
- `BacktestResult.to_pickle()` / `from_pickle()` - Fast serialization
- `BacktestResult.to_json()` / `from_json()` - Human-readable format
- Cached metric calculations with `@lru_cache`

---

## Phase 5: Benchmarking and Validation ✅ COMPLETED

Comprehensive benchmarking and validation suite for tracking performance and ensuring accuracy.

**Status:** Core benchmarking and validation infrastructure completed.

### 5.1 Create Performance Benchmark Suite ✅

**Files:** `tests/benchmarks/test_backtest_performance.py`, `tests/benchmarks/fixtures.py`
**Impact:** Track performance regressions and establish baselines
**Effort:** Medium
**Status:** ✅ IMPLEMENTED

- [x] Create standardized benchmark datasets (1K, 10K, 100K, 1M bars)
- [x] Implement pytest-benchmark integration
- [x] Add memory usage tracking (`test_memory_usage.py`)
- [x] Create throughput benchmarks (bars/second)
- [x] Add strategy complexity benchmarks
- [ ] Optional: Create comparison benchmarks vs `backtesting.py`

**Implementation:**
```bash
# Run all benchmarks
pytest tests/benchmarks/test_backtest_performance.py --benchmark-only

# Save baseline
pytest tests/benchmarks/test_backtest_performance.py --benchmark-only --benchmark-save=baseline

# Compare against baseline
pytest tests/benchmarks/test_backtest_performance.py --benchmark-only --benchmark-compare=baseline
```

**Regression focus:**
Phase 5 benchmarks are intended to prove performance gains or guard against
regressions. Use the baseline compare run as the primary signal, and add a
regression threshold in CI via pytest-benchmark comparison options if desired.

**Features:**
- Standardized test fixtures for 1K-1M bars
- EventDrivenEngine and VectorizedEngine benchmarks
- Memory usage profiling with psutil
- Throughput measurements (bars/second)
- Memory leak detection tests
- Baseline comparison support

---

### 5.2 Validation Against Reference Implementation ✅

**Files:** `tests/validation/test_accuracy.py`, `tests/validation/test_engine_parity.py`
**Impact:** Ensure optimizations don't change results
**Effort:** Medium
**Status:** ✅ IMPLEMENTED

- [x] Create reference results from current implementation
- [x] Compare optimized vs reference for numerical accuracy
- [x] Test edge cases (no trades, single trade, many positions)
- [x] Verify trade-by-trade matching
- [x] Add engine parity tests (EventDriven vs Vectorized)

**Implementation:**
```bash
# Run accuracy validation
pytest tests/validation/test_accuracy.py -v

# Run engine parity tests
pytest tests/validation/test_engine_parity.py -v
```

**Features:**
- Deterministic result validation
- Reference result comparison (JSON-based)
- Edge case testing (no trades, single trade, etc.)
- Trade-level validation (entry/exit prices, P&L)
- Engine parity verification
- Numerical tolerance checking (0.01% for returns, $1 for balances)

---

---

## Implementation Priority Matrix

| Task | Impact | Effort | Priority | Dependencies |
|------|--------|--------|----------|--------------|
| 1.1 NumPy Arrays | High | Low | **P0** | None |
| 1.2 Pre-Index Signals | High | Low | **P0** | None |
| 1.4 Pre-Allocate Equity | Medium | Low | **P1** | None |
| 1.5 Remove Debug Logging | Low | Low | **P1** | None |
| 2.1 Consolidate Positions | High | Medium | **P1** | None |
| 2.3 Vectorize P&L Updates | High | Medium | **P1** | 2.1 |
| 3.1 Core Simulator Module | High | High | **P2** | 1.1, 1.2 |
| 3.2 Numba JIT | Very High | High | **P2** | 3.1 |
| 3.3 Signal Preparation | Medium | Medium | **P2** | 3.1 |
| 3.4 Engine Integration | High | Medium | **P2** | 3.2, 3.3 |
| 4.1 Parallel Backtesting | High | High | **P3** | 3.4 |
| 5.1 Benchmark Suite | Medium | Medium | **P1** | None |

---

## Dependencies to Add

```toml
# pyproject.toml or requirements.txt additions

# Required for Phase 3
numba = "^0.59.0"

# Optional for Phase 4
cupy-cuda12x = { version = "^13.0.0", optional = true }  # GPU support
cython = { version = "^3.0.0", optional = true }  # Alternative to Numba

# For benchmarking
pytest-benchmark = "^4.0.0"
memory-profiler = "^0.61.0"
```

---

## Success Metrics

After implementing Phases 1-3, the backtest engine achieved:

| Metric | Baseline | Target | **Achieved** | Improvement |
|--------|----------|--------|--------------|-------------|
| EventDrivenEngine 10K bars | ~5,000ms | <2,000ms | **~3,500ms** | ~1.4x |
| EventDrivenEngine bars/sec | ~2,000 | ~5,000 | **~2,800** | ~1.4x |
| Core simulator (standalone) | - | - | **~2M bars/sec** | **800x** |

**Architecture:**
- **EventDrivenEngine**: Full-featured, accurate simulation (swap, pending orders, etc.)
  - Optimized via Phase 1 (NumPy arrays) and Phase 2 (PositionManager)
  - ~2,800 bars/sec - suitable for validation and final testing

- **VectorizedEngine**: Fast simulation for optimization (pending core integration)
  - Will use the Numba JIT-compiled core simulator
  - Target: ~2M bars/sec for rapid parameter sweeps

| Metric | Current (Est.) | Target | Status |
|--------|----------------|--------|--------|
| Memory per 100K bars | ~500MB | <100MB | Pending |
| Parallel speedup (8 cores) | 1x | 6-7x | Phase 4 |
| VectorizedEngine integration | - | ~2M bars/sec | Pending |

---

## References

- [backtesting.py source](https://github.com/kernc/backtesting.py) - Reference implementation
- [Numba documentation](https://numba.readthedocs.io/) - JIT compilation
- [NumPy performance tips](https://numpy.org/doc/stable/user/basics.performance.html)
- [Pandas optimization guide](https://pandas.pydata.org/docs/user_guide/enhancingperf.html)
