# Performance Optimization Guide

This document details the high-performance architectural upgrades implemented in HaruQuant's Simulation Engine and Analytics Service, inspired by the design principles of `VectorBT`.

## Core Philosophy: Kernel-Resident Architecture

To achieve state-of-the-art backtesting speeds (e.g., filling 1,000,000 orders in under 1 second), the system has transitioned from a Python-orchestrated execution model to a **Kernel-Resident Architecture**.

### Key Principles:
1.  **Zero-Object Hot Loops**: During the core simulation or calculation pass, no Python objects (like class instances, dicts, or lists) are created. This eliminates garbage collection overhead and Python interpreter latency.
2.  **Pre-allocated NumPy Buffers**: All state—including active positions, completed trades, and equity curves—is written into pre-allocated, contiguous NumPy arrays (`float64[:, :]`).
3.  **JIT Compilation (Numba)**: Hot loops are compiled into machine code using `@njit`.
4.  **Batch Reconstruction**: Python objects (`TradeRecord`, `EquityPoint`) are only reconstructed at the very end of a simulation for reporting purposes.

---

## 1. Simulation Engine Upgrades

The simulator now supports two highly optimized execution paths:

### Vectorized Backend (`vectorized.py`)
- **Behemoth Kernel**: The `_run_turbo_sim_numba` kernel handles the entire simulation in a single compiled pass.
- **Active Slot Tracker**: Instead of scanning all possible position slots (e.g., 200) every tick, the kernel uses a tracker array to only iterate over active indices. Complexity is reduced from $O(Ticks \times MaxPositions)$ to $O(Ticks \times ActivePositions)$.
- **IPC Fast Mode**: When `engine.fast_mode = True`, the simulator skips expensive MetaTrader 5 IPC calls for profit recalculation, enabling pure NumPy speeds.

### Event-Driven Backend (`event_driven.py`)
- **Turbo Fast-Path**: Introduced `_run_event_driven_turbo_kernel`. When a simulation uses standard signal processing without complex Python-level callbacks or custom risk rules, it automatically switches to this fully compiled kernel.
- **Reconstruction Parity**: Uses the same JIT-compiled reconstruction logic as the vectorized backend, ensuring high performance even for 1M+ ticks.

---

## 2. Analytics Service Upgrades

The analytics engine (`backend/services/analytics/`) has been optimized to handle massive datasets from high-frequency or multi-asset backtests.

### Optimized Metrics (`metrics.py` & `returns.py`)
- **Concurrency Analysis**: `max_size_held` uses a JIT-compiled event processor to calculate peak portfolio exposure.
- **Interval Merging**: `_merge_intervals` uses a compiled kernel to merge overlapping trade windows for time-in-market calculations.
- **Equity Curve Generation**: `_equity_curve_kernel` provides C-level speed for cumulative P&L and balance curve generation.
- **Outlier Removal**: Optimized 3-sigma filtering via jitted boolean masks.

### Drawdown & Robustness (`drawdowns.py` & `statistical_tests.py`)
- **Close-to-Close Drawdown**: Fully vectorized MFE/MAE-based drawdown calculations, eliminating slow `iterrows()` loops.
- **Monte Carlo Simulations**: `risk_of_ruin` now runs thousands of simulations in milliseconds using `_risk_of_ruin_kernel`.
- **Statistical Tests**: `White's Reality Check`, `Bootstrap Confidence Intervals`, and `Permutation Tests` now execute their resampling loops inside compiled kernels.

---

## Performance Benchmarks

| Task | Previous (Python-heavy) | Current (Kernel-Resident) | Speedup |
| :--- | :--- | :--- | :--- |
| 1M Ticks Vectorized Sim | ~16,000ms | ~700ms | **~23x** |
| 100k Trades Reconstruction | ~2,500ms | ~150ms | **~16x** |
| 10k Monte Carlo Runs | ~5,000ms | ~20ms | **~250x** |

---

## Developer Guidelines

To maintain these performance levels, follow these rules when extending analytics or simulation kernels:
1.  **Keep it JIT-friendly**: Avoid using Pandas, Scipy, or complex Python features inside functions decorated with `@njit`.
2.  **Array-First Design**: Pass raw NumPy arrays to internal kernels. Convert Pandas objects only at the entry point.
3.  **Avoid Allocation in Loops**: Use `np.empty()` to pre-allocate result buffers before starting a hot loop.
4.  **Minimize IPC**: Always check for `fast_mode` before calling external APIs (like MT5) during post-processing.
