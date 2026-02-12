# Implementation Plan — Incremental Full Rewrite

## Hybrid C++/Python Quantitative Trading & Backtesting System

| Field               | Detail                                      |
|---------------------|---------------------------------------------|
| **Document ID**     | IMP-HQTBS-001                               |
| **Version**         | 1.0.0                                       |
| **Date**            | 2026-02-12                                  |
| **Status**          | Active — Phase 0 Pending                    |
| **SRS Reference**   | SRS-HQTBS-001 v1.0.0                       |
| **SDD Reference**   | SDD-HQTBS-001 v1.0.0                       |

---

## Table of Contents

1. [Overview](#1-overview)
2. [Guiding Principles](#2-guiding-principles)
3. [Architecture Mapping](#3-architecture-mapping)
4. [Phase Overview](#4-phase-overview)
5. [Phase 0: C++ Build System](#phase-0-c-build-system)
6. [Phase 1: C++ Data Types + Position Kernel](#phase-1-c-data-types--position-kernel)
7. [Phase 2: Foundation Layer](#phase-2-foundation-layer)
8. [Phase 3: Data Infrastructure](#phase-3-data-infrastructure)
9. [Phase 4: C++ Event Loop + State Manager](#phase-4-c-event-loop--state-manager)
10. [Phase 5: C++ Matching Engine + Execution Models](#phase-5-c-matching-engine--execution-models)
11. [Phase 6: C++ Order/Position/Margin/Currency](#phase-6-c-orderpositionmargincurrency)
12. [Phase 7: Trading Framework Unification](#phase-7-trading-framework-unification)
13. [Phase 8: Strategy Framework Enhancement](#phase-8-strategy-framework-enhancement)
14. [Phase 9: Backtesting Engine Rewrite](#phase-9-backtesting-engine-rewrite)
15. [Phase 10: Optimization Engine](#phase-10-optimization-engine)
16. [Phase 11: Risk Management System](#phase-11-risk-management-system)
17. [Phase 12: Live Trading System](#phase-12-live-trading-system)
18. [Phase 13: Paper Trading System](#phase-13-paper-trading-system)
19. [Phase 14: Notification System](#phase-14-notification-system)
20. [Phase 15: API Layer Enhancement](#phase-15-api-layer-enhancement)
21. [Phase 16: Database Migration](#phase-16-database-migration)
22. [Phase 17: Observability, CI/CD, Polish](#phase-17-observability-cicd-polish)
23. [Progress Tracking](#progress-tracking)

---

## 1. Overview

**Goal:** Incrementally rewrite HaruQuant from pure Python to a C++20/Python hybrid architecture matching SRS-HQTBS-001 and SDD-HQTBS-001, replacing one component at a time. At the end of every phase, the full system remains functional and all tests pass.

**Approach:** "Strangler Fig" pattern — new C++ components wrap/replace old Python components via adapters. Old code is removed only after the replacement is proven correct.

**Key Decisions:**
- Keep `apps/` namespace (focus on functionality, not naming)
- Apache Parquet only for time-series storage
- Fixed-point arithmetic (int64_t) from Phase 1
- Database migration (SQLAlchemy) happens late
- Parallelism: `multiprocessing` first, Ray adapter later
- React UI stays; PySide6 desktop is a future addition

---

## 2. Guiding Principles

1. **Never break the working system.** All 98+ existing tests must pass at every phase boundary.
2. **One component at a time.** Each phase replaces exactly one functional boundary.
3. **Test before, during, after.** Run full test suite before starting, write new tests during, run everything after.
4. **Graceful fallback.** If C++ module unavailable (`import hqt_engine` fails), fall back to Numba/Python.
5. **Old imports work.** Compatibility re-exports maintained until all dependents are migrated.
6. **Bit-identical verification.** C++ output must match Python output for the same inputs.

---

## 3. Architecture Mapping

### Current → Target

```
CURRENT (Pure Python)                    TARGET (C++/Python Hybrid)
─────────────────────                    ──────────────────────────
apps/simulation/engine.py           →    cpp/src/core/     (C++ event loop, state)
  numba_position_update()           →    cpp/src/matching/  (C++ position kernel)
  _calc_profit/_calc_margin         →    cpp/src/matching/  (C++ execution models)
  monitor_positions()               →    cpp/src/state/     (C++ state manager)
  monitor_pending_orders()          →    cpp/src/matching/  (C++ matching engine)
apps/simulation/data.py             →    cpp/src/data/ + bridge/ (C++ structs)
apps/simulation/simulator.py        →    apps/simulation/   (thin Python orchestrator)
apps/trade/trade.py                 →    apps/trading/      (unified ITradingContext)
apps/strategy/base.py               →    apps/strategy/     (enhanced with parameters)
apps/optimization/                  →    apps/optimization/ (multiprocessing + Ray)
apps/live/                          →    apps/live/         (C++ engine + ZMQ gateway)
apps/sqlite/                        →    apps/database/     (SQLAlchemy, Phase 16)
apps/finance/                       →    apps/backtesting/metrics/ (reorganized)
apps/utils/data_*.py                →    apps/data/         (Parquet + validation)
(no config files)                   →    config/*.toml      (TOML + schema validation)
(no C++ code)                       →    cpp/ + bridge/     (C++20 core + Nanobind)
```

### New Directory Structure (Built Incrementally)

```
HaruQuant/
├── cpp/                              # C++ Core Engine (Phases 0-6)
│   ├── CMakeLists.txt
│   ├── vcpkg.json
│   ├── include/hqt/
│   │   ├── core/                     # Event loop, engine facade, global clock
│   │   ├── matching/                 # Matching engine, execution models
│   │   ├── state/                    # Account, position, order, deal, state manager
│   │   ├── market/                   # Symbol info, market state, currency converter
│   │   ├── margin/                   # Margin calculator
│   │   ├── data/                     # Tick, bar, data feed, mmap reader
│   │   ├── io/                       # ZMQ broadcaster, broker gateway
│   │   ├── journal/                  # Write-ahead log
│   │   └── util/                     # Fixed-point, timestamp, random, exceptions
│   ├── src/                          # .cpp implementation files
│   ├── tests/                        # Google Test unit tests
│   └── benchmarks/                   # Google Benchmark micro-benchmarks
│
├── bridge/                           # Nanobind Bridge (Phases 0-6)
│   ├── CMakeLists.txt
│   └── src/
│       ├── module.cpp                # Module definition
│       ├── bind_engine.cpp           # Engine exposure
│       ├── bind_state.cpp            # State types
│       ├── bind_market.cpp           # Market data types
│       ├── bind_kernel.cpp           # Position kernel
│       └── bind_commands.cpp         # Command interface
│
├── config/                           # TOML Configuration (Phase 2)
│   ├── base.toml
│   ├── development.toml
│   ├── testing.toml
│   └── production.toml
│
├── apps/                             # Python Packages (enhanced incrementally)
│   ├── foundation/                   # Phase 2: config, logging, exceptions, security
│   ├── data/                         # Phase 3: models, validation, providers, storage
│   ├── trading/                      # Phase 7: unified interface, mode router
│   ├── backtesting/                  # Phase 9: engines, metrics, visualization
│   ├── optimization/                 # Phase 10: grid, bayesian, WFO, MC, edge lab
│   ├── risk/                         # Phase 11: governor, sizing, regime, allocation
│   ├── live/                         # Phase 12: engine, gateway, reconciliation
│   ├── paper/                        # Phase 13: paper trading context
│   ├── notifications/                # Phase 14: telegram, email, manager
│   ├── api/                          # Phase 15: FastAPI routes, websocket, auth
│   ├── database/                     # Phase 16: SQLAlchemy ORM, Alembic
│   │
│   ├── simulation/                   # EXISTING (kept as compat layer, then removed)
│   ├── strategy/                     # EXISTING (enhanced in Phase 8)
│   ├── indicator/                    # EXISTING (reorganized in Phase 8)
│   ├── trade/                        # EXISTING (replaced by trading/ in Phase 7)
│   ├── sqlite/                       # EXISTING (replaced by database/ in Phase 16)
│   ├── finance/                      # EXISTING (replaced by backtesting/metrics/)
│   ├── edge/                         # EXISTING (replaced by optimization/edge_lab/)
│   ├── mt5/                          # EXISTING (kept, enhanced in Phase 12)
│   ├── utils/                        # EXISTING (partially moved to foundation/)
│   ├── logger/                       # EXISTING (replaced by foundation/logging/)
│   └── plotting/                     # EXISTING (connected to new BacktestResult)
│
├── mql5/                             # Phase 12: MQL5 Bridge EA source
├── strategies/                       # User strategy files
├── scripts/                          # Build and dev scripts
├── tests/                            # Python tests
├── docs/                             # Documentation
└── data/                             # Data storage (Parquet)
```

---

## 4. Phase Overview

| # | Phase | Duration | Cumulative Speedup | Status |
|---|-------|----------|--------------------|--------|
| 0 | C++ Build System | 2-3 wk | — | [ ] Not Started |
| 1 | C++ Data Types + Position Kernel | 3-4 wk | 2-5x | [ ] Not Started |
| 2 | Foundation Layer | 2-3 wk | 2-5x | [ ] Not Started |
| 3 | Data Infrastructure | 3-4 wk | 2-5x | [ ] Not Started |
| 4 | C++ Event Loop + State Manager | 4-6 wk | 10-30x | [ ] Not Started |
| 5 | C++ Matching Engine + Execution Models | 3-4 wk | 30-50x | [ ] Not Started |
| 6 | C++ Order/Position/Margin/Currency | 3-4 wk | 50-100x | [ ] Not Started |
| 7 | Trading Framework Unification | 2-3 wk | 50-100x | [ ] Not Started |
| 8 | Strategy Framework Enhancement | 2-3 wk | 50-100x | [ ] Not Started |
| 9 | Backtesting Engine Rewrite | 3-4 wk | 50-100x | [ ] Not Started |
| 10 | Optimization Engine | 3-4 wk | 100-500x (opt) | [ ] Not Started |
| 11 | Risk Management System | 2-3 wk | — | [ ] Not Started |
| 12 | Live Trading System | 4-5 wk | — | [ ] Not Started |
| 13 | Paper Trading System | 2-3 wk | — | [ ] Not Started |
| 14 | Notification System | 1-2 wk | — | [ ] Not Started |
| 15 | API Layer Enhancement | 2-3 wk | — | [ ] Not Started |
| 16 | Database Migration | 3-4 wk | — | [ ] Not Started |
| 17 | Observability, CI/CD, Polish | 2-3 wk | — | [ ] Not Started |

**Critical Path:** 0 → 1 → 4 → 5 → 6 → 7 → 9 → 10
**Parallel Tracks:** Phases 2, 3, 8, 11, 14 can overlap with C++ phases

---

## Phase 0: C++ Build System

**Duration:** 2-3 weeks
**Depends On:** None
**SRS Coverage:** CPP-FR-025 through CPP-FR-028
**Risk Level:** HIGH (build system issues can block everything)

### Tasks

- [ ] **0.1** Install prerequisites
  - [ ] 0.1.1 Install Visual Studio 2022 with C++ workload (MSVC)
  - [ ] 0.1.2 Install CMake 3.25+
  - [ ] 0.1.3 Clone and bootstrap vcpkg
  - [ ] 0.1.4 Install Python development headers (for Nanobind)
  - [ ] 0.1.5 Verify all tools: `cmake --version`, `cl`, `vcpkg --version`

- [ ] **0.2** Create C++ project structure
  - [ ] 0.2.1 Create `cpp/CMakeLists.txt` — top-level with C++20, vcpkg toolchain
  - [ ] 0.2.2 Create `cpp/vcpkg.json` — manifest with dependencies: nanobind, spdlog, cppzmq, tomlplusplus, gtest, benchmark
  - [ ] 0.2.3 Create `cpp/include/hqt/util/version.hpp` — version constants
  - [ ] 0.2.4 Create `cpp/src/util/version.cpp` — version implementation
  - [ ] 0.2.5 Create `cpp/tests/CMakeLists.txt` — Google Test setup
  - [ ] 0.2.6 Create `cpp/tests/test_version.cpp` — minimal test
  - [ ] 0.2.7 Create `cpp/benchmarks/CMakeLists.txt` — Google Benchmark setup

- [ ] **0.3** Create Nanobind bridge
  - [ ] 0.3.1 Create `bridge/CMakeLists.txt` — Nanobind module build
  - [ ] 0.3.2 Create `bridge/src/module.cpp` — `NB_MODULE(hqt_engine, m)` with `hello()` function
  - [ ] 0.3.3 Verify `import hqt_engine` works from Python

- [ ] **0.4** Create build scripts
  - [ ] 0.4.1 Create `scripts/build_cpp.bat` — Windows build script (configure + build)
  - [ ] 0.4.2 Create `scripts/build_cpp.sh` — Linux build script (future)
  - [ ] 0.4.3 Create `scripts/install_cpp_deps.bat` — vcpkg dependency installation
  - [ ] 0.4.4 Document build steps in `docs/04_developer_setup.md`

- [ ] **0.5** Verify full pipeline
  - [ ] 0.5.1 CMake configure succeeds
  - [ ] 0.5.2 CMake build succeeds (Debug + Release)
  - [ ] 0.5.3 Google Test runs and passes
  - [ ] 0.5.4 `import hqt_engine; hqt_engine.hello()` works from Python
  - [ ] 0.5.5 Existing Python tests still pass (no interference)

### Unit Tests

```
cpp/tests/test_version.cpp:
  - test_version_string_not_empty
  - test_version_major_minor_patch

tests/unit/bridge/test_import.py:
  - test_hqt_engine_imports
  - test_hello_returns_string
  - test_version_accessible
```

### Usage Example

```python
# tests/usage/bridge/usage_hello.py
"""Verify C++ bridge is working."""
import hqt_engine

print(f"HQT Engine Version: {hqt_engine.version()}")
print(f"Hello: {hqt_engine.hello()}")
assert hqt_engine.hello() == "HQT Engine v0.1.0"
print("Phase 0 verification: PASSED")
```

### Commit Message
```
feat(cpp): initialize C++ build system with CMake, vcpkg, and Nanobind

- Set up CMake 3.25+ with C++20 standard and vcpkg toolchain
- Add vcpkg.json manifest with dependencies (nanobind, spdlog, gtest, etc.)
- Create minimal Nanobind bridge module (hqt_engine) with hello() function
- Add Google Test infrastructure with version test
- Add build scripts for Windows (scripts/build_cpp.bat)
- Add developer setup documentation (docs/04_developer_setup.md)

SRS: CPP-FR-025, CPP-FR-026, CPP-FR-027, CPP-FR-028
```

### Documentation
- `docs/04_developer_setup.md` — Build prerequisites, setup steps, troubleshooting
- `cpp/README.md` — C++ project overview, build instructions

### Verification Checklist
- [ ] `cmake -B build` succeeds
- [ ] `cmake --build build --config Release` succeeds
- [ ] `cd build && ctest` — all C++ tests pass
- [ ] `python -c "import hqt_engine"` — no errors
- [ ] `python -m pytest tests/unit/simulation/ -v --no-cov` — all 98 tests pass

---

## Phase 1: C++ Data Types + Position Kernel

**Duration:** 3-4 weeks
**Depends On:** Phase 0
**SRS Coverage:** DAT-FR-001 through DAT-FR-004, CPP-FR-015 through CPP-FR-018
**Risk Level:** MEDIUM

### Tasks

- [ ] **1.1** Implement fixed-point arithmetic utilities
  - [ ] 1.1.1 Create `cpp/include/hqt/util/fixed_point.hpp` — `to_double()`, `from_double()`, arithmetic helpers
  - [ ] 1.1.2 Create `cpp/tests/test_fixed_point.cpp` — edge cases: zero, negative, large values, all digit counts (0-6)
  - [ ] 1.1.3 Benchmark fixed-point vs double arithmetic

- [ ] **1.2** Define core C++ data structures
  - [ ] 1.2.1 Create `cpp/include/hqt/data/tick.hpp` — `Tick` struct (aligned, fixed-point prices)
  - [ ] 1.2.2 Create `cpp/include/hqt/data/bar.hpp` — `Bar` struct (aligned, fixed-point OHLC)
  - [ ] 1.2.3 Create `cpp/include/hqt/market/symbol_info.hpp` — `SymbolInfo` struct
  - [ ] 1.2.4 Create `cpp/include/hqt/state/position.hpp` — `Position` struct
  - [ ] 1.2.5 Create `cpp/include/hqt/state/order.hpp` — `Order` struct
  - [ ] 1.2.6 Create `cpp/include/hqt/state/deal.hpp` — `Deal` struct (closed trade)
  - [ ] 1.2.7 Create `cpp/include/hqt/state/account_state.hpp` — `AccountState` struct
  - [ ] 1.2.8 Create `cpp/tests/test_data_types.cpp` — construction, field access, serialization

- [ ] **1.3** Implement C++ position kernel
  - [ ] 1.3.1 Create `cpp/include/hqt/matching/position_kernel.hpp` — function declaration
  - [ ] 1.3.2 Create `cpp/src/matching/position_kernel.cpp` — implementation (profit, margin, SL/TP hits for all 6 margin modes)
  - [ ] 1.3.3 Create `cpp/tests/test_position_kernel.cpp` — comprehensive tests
  - [ ] 1.3.4 Create `cpp/benchmarks/bench_position_kernel.cpp` — benchmark vs expected performance

- [ ] **1.4** Expose via Nanobind bridge
  - [ ] 1.4.1 Create `bridge/src/bind_data.cpp` — expose Tick, Bar, SymbolInfo to Python
  - [ ] 1.4.2 Create `bridge/src/bind_kernel.cpp` — expose `position_update()` accepting NumPy arrays
  - [ ] 1.4.3 Update `bridge/src/module.cpp` — register new bindings
  - [ ] 1.4.4 Verify zero-copy: Python NumPy array → C++ pointer (no data copy)

- [ ] **1.5** Integrate with existing simulation engine
  - [ ] 1.5.1 Add `CPP_AVAILABLE` flag to `apps/simulation/utils.py`
  - [ ] 1.5.2 Modify `apps/simulation/engine.py` `_monitor_positions_arrays()` — add C++ path before Numba
  - [ ] 1.5.3 Add conversion layer: Python float arrays ↔ C++ fixed-point (at bridge boundary)
  - [ ] 1.5.4 Verify: C++ kernel output matches Numba kernel output for identical inputs
  - [ ] 1.5.5 Run all 98 existing tests with C++ kernel active

- [ ] **1.6** Performance benchmarking
  - [ ] 1.6.1 Create `tests/benchmarks/bench_position_kernel.py` — Python benchmark comparing C++, Numba, pure Python
  - [ ] 1.6.2 Measure: 1000 positions × 100k ticks — time for each path
  - [ ] 1.6.3 Document results in benchmark report

### Unit Tests

```
cpp/tests/test_fixed_point.cpp:
  - test_to_double_5_digits (EURUSD: 110523 → 1.10523)
  - test_to_double_2_digits (XAUUSD: 235050 → 2350.50)
  - test_from_double_5_digits (1.10523 → 110523)
  - test_from_double_rounding (1.105235 rounds correctly)
  - test_zero_value
  - test_negative_value
  - test_large_value (USDJPY: 15023500 → 150.235)

cpp/tests/test_data_types.cpp:
  - test_tick_construction
  - test_bar_construction
  - test_symbol_info_fields
  - test_position_construction
  - test_account_state_defaults

cpp/tests/test_position_kernel.cpp:
  - test_buy_profit_positive (price above entry)
  - test_buy_profit_negative (price below entry)
  - test_sell_profit_positive (price below entry)
  - test_sell_profit_negative (price above entry)
  - test_margin_mode_0 (forex: volume * contract / leverage)
  - test_margin_mode_1 (futures: volume * contract)
  - test_margin_mode_2 (exchange: volume * contract * price)
  - test_margin_mode_3 (leveraged exchange)
  - test_margin_mode_4 (tick-value based)
  - test_margin_mode_5_6 (CFD)
  - test_sl_hit_buy (price <= SL)
  - test_sl_hit_sell (price >= SL)
  - test_tp_hit_buy (price >= TP)
  - test_tp_hit_sell (price <= TP)
  - test_no_sl_set (SL=0, no hit)
  - test_no_tp_set (TP=0, no hit)
  - test_invalid_position (valid=false, skipped)
  - test_multiple_positions (batch of 100)
  - test_matches_numba_output (bit-identical comparison)

tests/unit/bridge/test_position_kernel.py:
  - test_cpp_kernel_buy_profit
  - test_cpp_kernel_sell_profit
  - test_cpp_kernel_margin_modes
  - test_cpp_kernel_sl_tp_detection
  - test_cpp_matches_numba_exactly
  - test_cpp_numpy_zero_copy
  - test_cpp_kernel_performance (faster than Numba)

tests/unit/simulation/ (existing 98 tests):
  - ALL must pass with CPP_AVAILABLE=True
```

### Usage Example

```python
# tests/usage/bridge/usage_position_kernel.py
"""Compare C++ position kernel with Numba kernel."""
import numpy as np
import time

# Setup: 50 positions
count = 50
current_prices = np.random.uniform(1.09, 1.11, count)
price_open = np.random.uniform(1.09, 1.11, count)
volume = np.full(count, 0.1)
direction = np.random.choice([1, -1], count).astype(np.int8)
sl = price_open - direction * 0.005
tp = price_open + direction * 0.010
valid = np.ones(count, dtype=bool)
contract_size = np.full(count, 100000.0)
tick_size = np.full(count, 0.00001)
tick_value = np.full(count, 1.0)
margin_mode = np.zeros(count)
leverage = np.full(count, 100.0)

# C++ kernel
import hqt_engine
profit_cpp = np.zeros(count)
margin_cpp = np.zeros(count)
sl_hit_cpp = np.zeros(count, dtype=bool)
tp_hit_cpp = np.zeros(count, dtype=bool)

start = time.perf_counter()
for _ in range(100_000):
    hqt_engine.position_update(
        current_prices, price_open, volume, direction,
        sl, tp, valid, contract_size, tick_size, tick_value,
        margin_mode, leverage,
        profit_cpp, margin_cpp, sl_hit_cpp, tp_hit_cpp
    )
cpp_time = time.perf_counter() - start

# Numba kernel
from apps.simulation.utils import numba_position_update
start = time.perf_counter()
for _ in range(100_000):
    numba_position_update(
        current_prices, price_open, volume, direction,
        sl, tp, valid, contract_size, tick_size, tick_value,
        margin_mode, leverage
    )
numba_time = time.perf_counter() - start

print(f"C++ kernel:   {cpp_time:.3f}s for 100k iterations")
print(f"Numba kernel: {numba_time:.3f}s for 100k iterations")
print(f"Speedup:      {numba_time/cpp_time:.1f}x")

# Verify identical results
assert np.allclose(profit_cpp, profit_numba, atol=1e-10)
assert np.array_equal(sl_hit_cpp, sl_hit_numba)
print("Phase 1 verification: PASSED")
```

### Commit Message
```
feat(cpp): add C++ data types and position kernel with Nanobind bridge

- Define core C++ structs: Tick, Bar, SymbolInfo, Position, Order, Deal, AccountState
- Implement fixed-point arithmetic utilities (int64_t with implicit scaling)
- Implement position_update() kernel: profit, margin, SL/TP hit detection
- Support all 6 MT5 margin calculation modes
- Expose position_update() via Nanobind accepting NumPy arrays (zero-copy)
- Integrate as highest-priority path in simulation engine (C++ > Numba > Python)
- Add comprehensive C++ tests (Google Test) and Python bridge tests
- Add performance benchmark: C++ vs Numba comparison

SRS: DAT-FR-001, DAT-FR-002, DAT-FR-003, CPP-FR-015, CPP-FR-016, CPP-FR-017
```

### Documentation
- `cpp/include/hqt/data/README.md` — Data type reference with fixed-point examples
- `cpp/include/hqt/matching/README.md` — Position kernel API documentation
- Update `docs/04_developer_setup.md` — How to run C++ tests and benchmarks

### Verification Checklist
- [ ] All C++ tests pass (`cd build && ctest`)
- [ ] All Python bridge tests pass
- [ ] All 98 existing simulation tests pass with `CPP_AVAILABLE=True`
- [ ] All 98 existing simulation tests pass with `CPP_AVAILABLE=False` (fallback)
- [ ] C++ output matches Numba output (bit-identical for same inputs)
- [ ] C++ kernel is faster than Numba (benchmark proves it)

---

## Phase 2: Foundation Layer

**Duration:** 2-3 weeks
**Depends On:** Phase 0 (can run in parallel with Phase 1)
**SRS Coverage:** FND-FR-001 through FND-FR-030
**Risk Level:** LOW

### Tasks

- [ ] **2.1** TOML configuration system
  - [ ] 2.1.1 Create `config/base.toml` — all configuration sections with defaults
  - [ ] 2.1.2 Create `config/development.toml`, `config/testing.toml`, `config/production.toml` — environment overrides
  - [ ] 2.1.3 Create `apps/foundation/__init__.py`
  - [ ] 2.1.4 Create `apps/foundation/config/manager.py` — `ConfigManager` class: load, merge, resolve, validate
  - [ ] 2.1.5 Create `apps/foundation/config/schema.py` — Pydantic models for each config section
  - [ ] 2.1.6 Create `apps/foundation/config/secrets.py` — `${secret:key}` and `${env:VAR}` resolution via OS keyring
  - [ ] 2.1.7 Create C++ config reader (`cpp/include/hqt/util/config_reader.hpp`) — read TOML via toml++

- [ ] **2.2** Exception hierarchy
  - [ ] 2.2.1 Create `apps/foundation/exceptions/__init__.py` — Python exception classes
  - [ ] 2.2.2 Create `cpp/include/hqt/util/exceptions.hpp` — C++ exception hierarchy
  - [ ] 2.2.3 Create `bridge/src/bind_exceptions.cpp` — C++ → Python exception mapping
  - [ ] 2.2.4 Update `bridge/src/module.cpp` — register exception bindings

- [ ] **2.3** Dual logging system
  - [ ] 2.3.1 Create `apps/foundation/logging/setup.py` — Python logging configuration
  - [ ] 2.3.2 Create `apps/foundation/logging/redaction.py` — secret masking filter
  - [ ] 2.3.3 Create `apps/foundation/logging/bridge_handler.py` — spdlog → Python forwarder
  - [ ] 2.3.4 Create C++ async logger setup (`cpp/src/util/logger.cpp`) — spdlog with 8192-slot queue
  - [ ] 2.3.5 Log format: `[timestamp] [LEVEL] [module] [tid] Message`

- [ ] **2.4** Secrets management
  - [ ] 2.4.1 Create `apps/foundation/security/keyring.py` — OS keyring integration
  - [ ] 2.4.2 Migrate `apps/utils/security.py` functionality
  - [ ] 2.4.3 Add automatic redaction of API keys, tokens, passwords in logs

- [ ] **2.5** Compatibility layer
  - [ ] 2.5.1 Update `apps/logger/__init__.py` — re-export from `apps.foundation.logging`
  - [ ] 2.5.2 Update `apps/utils/security.py` — re-export from `apps.foundation.security`
  - [ ] 2.5.3 Verify all existing imports still work

### Unit Tests

```
tests/unit/foundation/test_config.py:
  - test_load_base_config
  - test_environment_overlay_merge
  - test_secret_resolution
  - test_env_var_resolution
  - test_pydantic_validation_valid
  - test_pydantic_validation_invalid_raises
  - test_frozen_config_immutable
  - test_cpp_config_reader_loads_toml

tests/unit/foundation/test_exceptions.py:
  - test_exception_hierarchy
  - test_exception_carries_context (code, message, module, timestamp)
  - test_cpp_exception_becomes_python_exception
  - test_all_exception_types_instantiate

tests/unit/foundation/test_logging.py:
  - test_python_logging_to_console
  - test_python_logging_to_file
  - test_log_rotation (50MB, 10 files)
  - test_secret_redaction_in_logs
  - test_log_format_includes_timestamp_level_module

tests/unit/foundation/test_security.py:
  - test_store_and_retrieve_secret
  - test_secret_not_in_plain_text
```

### Usage Example

```python
# tests/usage/foundation/usage_config.py
"""Demonstrate TOML configuration system."""
from apps.foundation.config import ConfigManager

config = ConfigManager().load(env="development")

print(f"Engine config: {config.engine}")
print(f"Data config:   {config.data}")
print(f"Broker config: {config.broker}")
print(f"Risk config:   {config.risk}")

# Access typed values
print(f"Initial balance: {config.engine.initial_balance}")
print(f"Max drawdown:    {config.risk.max_drawdown_pct}%")
print("Phase 2 verification: PASSED")
```

### Commit Message
```
feat(foundation): add TOML configuration, exception hierarchy, dual logging, and secrets management

- Create TOML-based configuration system with environment overlays
- Add Pydantic schema validation for all config sections
- Implement ${secret:key} and ${env:VAR} resolution via OS keyring
- Define cross-language exception hierarchy (Python + C++)
- Map C++ exceptions to Python exceptions at Nanobind bridge boundary
- Set up dual logging: spdlog (C++ async) + Python logging with bridge handler
- Add automatic secret redaction in all log output
- Add compatibility re-exports from old import paths

SRS: FND-FR-001 through FND-FR-030
```

### Documentation
- Update `docs/04_developer_setup.md` — Configuration file reference
- `apps/foundation/README.md` — Foundation layer overview

### Verification Checklist
- [ ] Config loads from TOML, validates, resolves secrets
- [ ] C++ can read engine config from same TOML files
- [ ] Logging works in both C++ and Python
- [ ] Secrets never appear in log output
- [ ] All existing tests pass (old imports work via re-exports)

---

## Phase 3: Data Infrastructure

**Duration:** 3-4 weeks
**Depends On:** Phase 2
**SRS Coverage:** DAT-FR-006 through DAT-FR-029
**Risk Level:** LOW

### Tasks

- [ ] **3.1** Data models
  - [ ] 3.1.1 Create `apps/data/__init__.py`
  - [ ] 3.1.2 Create `apps/data/models/tick.py` — Pydantic `TickModel`
  - [ ] 3.1.3 Create `apps/data/models/bar.py` — Pydantic `BarModel`
  - [ ] 3.1.4 Create `apps/data/models/symbol_spec.py` — Pydantic `SymbolSpecification`
  - [ ] 3.1.5 Create `apps/data/models/converters.py` — Pydantic ↔ C++ struct ↔ pandas DataFrame

- [ ] **3.2** Data validation pipeline
  - [ ] 3.2.1 Create `apps/data/validation/pipeline.py` — orchestrates all checks
  - [ ] 3.2.2 Create `apps/data/validation/price_sanity.py` — bid > 0, ask >= bid, bounds check
  - [ ] 3.2.3 Create `apps/data/validation/gap_detector.py` — gaps > 10x average range
  - [ ] 3.2.4 Create `apps/data/validation/spike_detector.py` — bars > 5x ATR
  - [ ] 3.2.5 Create `apps/data/validation/missing_timestamps.py` — expected frequency vs actual
  - [ ] 3.2.6 Create `apps/data/validation/duplicate_detector.py` — detect and remove duplicates
  - [ ] 3.2.7 Create `apps/data/validation/spread_analyzer.py` — abnormal spread > 3x median
  - [ ] 3.2.8 Create `apps/data/validation/report.py` — `ValidationReport` with counts, timestamps, severity

- [ ] **3.3** Parquet storage layer
  - [ ] 3.3.1 Create `apps/data/storage/parquet_store.py` — read/write via PyArrow
  - [ ] 3.3.2 Create `apps/data/storage/catalog.py` — SQLite data catalog (symbol, timeframe, date range, count, hash)
  - [ ] 3.3.3 Implement columnar access (read only close prices without full OHLCV)
  - [ ] 3.3.4 Implement data compaction (merge incremental downloads)
  - [ ] 3.3.5 File layout: `data/parquet/{SYMBOL}/{timeframe}/{year}.parquet`

- [ ] **3.4** Data providers refactor
  - [ ] 3.4.1 Create `apps/data/providers/base.py` — `DataProvider` ABC
  - [ ] 3.4.2 Create `apps/data/providers/mt5.py` — refactor from `apps/mt5/`
  - [ ] 3.4.3 Create `apps/data/providers/dukascopy.py` — refactor from `apps/dukascopy/`
  - [ ] 3.4.4 Implement incremental downloads (only newer than latest stored)
  - [ ] 3.4.5 Progress callback support for UI integration

- [ ] **3.5** Data versioning
  - [ ] 3.5.1 Create `apps/data/versioning/hasher.py` — SHA-256 content hash per file
  - [ ] 3.5.2 Create `apps/data/versioning/lineage.py` — backtest records data hashes
  - [ ] 3.5.3 Hash stored in catalog, recorded with every backtest result

- [ ] **3.6** Integration
  - [ ] 3.6.1 Update `apps/utils/data_getters.py` — add Parquet loading path
  - [ ] 3.6.2 Update simulation to load from Parquet when available
  - [ ] 3.6.3 Create migration script: existing CSV → Parquet conversion

### Unit Tests

```
tests/unit/data/test_validation.py:
  - test_price_sanity_valid_data
  - test_price_sanity_negative_bid_detected
  - test_price_sanity_ask_less_than_bid_detected
  - test_gap_detector_finds_gaps
  - test_spike_detector_finds_spikes
  - test_missing_timestamp_detected
  - test_duplicate_detected_and_removed
  - test_spread_analyzer_abnormal_detected
  - test_validation_report_summary
  - test_configurable_thresholds_per_symbol

tests/unit/data/test_parquet_store.py:
  - test_write_and_read_bars
  - test_write_and_read_ticks
  - test_columnar_access_close_only
  - test_incremental_append
  - test_data_compaction
  - test_catalog_entry_created

tests/unit/data/test_versioning.py:
  - test_content_hash_deterministic
  - test_hash_changes_on_data_change
  - test_lineage_query_returns_hashes

tests/unit/data/test_providers.py:
  - test_mt5_provider_interface
  - test_dukascopy_provider_interface
  - test_incremental_download
```

### Usage Example

```python
# tests/usage/data/usage_parquet_pipeline.py
"""Demonstrate data download → validate → store → load pipeline."""
from apps.data.providers.mt5 import MT5DataProvider
from apps.data.validation.pipeline import ValidationPipeline
from apps.data.storage.parquet_store import ParquetStore

# 1. Download
provider = MT5DataProvider()
bars = provider.fetch_bars("EURUSD", "H1", start="2024-01-01", end="2024-12-31")

# 2. Validate
pipeline = ValidationPipeline(symbol="EURUSD")
report = pipeline.validate(bars)
print(f"Issues found: {report.total_issues}")
print(f"Severity breakdown: {report.severity_counts}")

# 3. Store
store = ParquetStore()
store.write_bars("EURUSD", "H1", bars)

# 4. Load
loaded = store.read_bars("EURUSD", "H1", start="2024-06-01", end="2024-12-31")
print(f"Loaded {len(loaded)} bars")

# 5. Version
print(f"Data hash: {store.get_hash('EURUSD', 'H1')}")
print("Phase 3 verification: PASSED")
```

### Commit Message
```
feat(data): add Parquet storage, data validation pipeline, and data versioning

- Create Pydantic data models for Tick, Bar, SymbolSpecification
- Implement sequential validation pipeline: price sanity, gaps, spikes, missing timestamps, duplicates, spread
- Add Parquet storage layer with columnar access and incremental append
- Refactor MT5 and Dukascopy data providers with common DataProvider interface
- Add data versioning with SHA-256 content hashes stored in catalog
- Add data catalog (SQLite) tracking symbol, timeframe, date range, record count
- Support incremental downloads (only fetch newer data)

SRS: DAT-FR-006 through DAT-FR-029
```

### Documentation
- `apps/data/README.md` — Data infrastructure overview, validation thresholds, Parquet schema

### Verification Checklist
- [ ] Download → validate → store → load produces identical data
- [ ] Validation catches all planted issues in test dataset
- [ ] Parquet files smaller than CSV equivalents
- [ ] Columnar reads are faster than full-row reads
- [ ] Existing backtests produce same results when loading from Parquet
- [ ] All existing tests pass

---

## Phase 4: C++ Event Loop + State Manager

**Duration:** 4-6 weeks
**Depends On:** Phase 1
**SRS Coverage:** CPP-FR-001 through CPP-FR-014
**Risk Level:** HIGH

### Tasks

- [ ] **4.1** C++ Event Loop
  - [ ] 4.1.1 Create `cpp/include/hqt/core/event.hpp` — Event struct (timestamp, type, symbol_id, payload)
  - [ ] 4.1.2 Create `cpp/include/hqt/core/event_loop.hpp` — priority queue, run/pause/resume/stop/step
  - [ ] 4.1.3 Create `cpp/src/core/event_loop.cpp` — implementation
  - [ ] 4.1.4 Create `cpp/tests/test_event_loop.cpp` — ordering, pause/resume, step-forward

- [ ] **4.2** C++ Global Clock
  - [ ] 4.2.1 Create `cpp/include/hqt/core/global_clock.hpp` — multi-asset time synchronization
  - [ ] 4.2.2 Enforce: no symbol advances past T1 until all complete
  - [ ] 4.2.3 Create `cpp/tests/test_global_clock.cpp` — multi-symbol ordering correctness

- [ ] **4.3** C++ State Manager
  - [ ] 4.3.1 Create `cpp/include/hqt/state/state_manager.hpp` — account, positions, orders, deals
  - [ ] 4.3.2 Create `cpp/src/state/state_manager.cpp` — implementation
  - [ ] 4.3.3 Equity recalculation on every tick: `balance + sum(unrealized PnL)`
  - [ ] 4.3.4 MAE/MFE tracking per position (moved from Python `_update_trade_tracker`)
  - [ ] 4.3.5 Create `cpp/tests/test_state_manager.cpp`

- [ ] **4.4** C++ Engine Facade
  - [ ] 4.4.1 Create `cpp/include/hqt/core/engine.hpp` — top-level Engine class
  - [ ] 4.4.2 Create `cpp/src/core/engine.cpp` — implementation
  - [ ] 4.4.3 `load_bars()` — accept NumPy data, populate event queue
  - [ ] 4.4.4 `set_on_bar()` — register Python callback for strategy signals
  - [ ] 4.4.5 `run()` — process all events, release GIL, acquire for callbacks
  - [ ] 4.4.6 `run_steps(n)` — process n events for debugging
  - [ ] 4.4.7 Read-only accessors: `account()`, `positions()`, `pending_orders()`, `history_deals()`

- [ ] **4.5** Nanobind Engine exposure
  - [ ] 4.5.1 Create `bridge/src/bind_engine.cpp` — Engine class exposed to Python
  - [ ] 4.5.2 Create `bridge/src/bind_state.cpp` — state types exposed as read-only properties
  - [ ] 4.5.3 GIL management: release during `run()`, acquire for `on_bar` callback
  - [ ] 4.5.4 `load_bars()` accepts NumPy arrays via `nb::ndarray` (zero-copy)

- [ ] **4.6** Integration adapter
  - [ ] 4.6.1 Create `apps/simulation/cpp_adapter.py` — wraps `hqt_engine.Engine` as `SimulationEngine`-compatible
  - [ ] 4.6.2 Modify `apps/simulation/simulator.py` — detect C++ engine, use adapter
  - [ ] 4.6.3 Strategy callback: C++ calls Python `strategy.get_signal()` once per bar
  - [ ] 4.6.4 All per-tick work (positions, SL/TP, margin, account) stays in C++

- [ ] **4.7** Verification
  - [ ] 4.7.1 Single-symbol backtest: C++ engine vs Python engine → identical results
  - [ ] 4.7.2 Multi-symbol backtest: C++ GlobalClock ordering correctness
  - [ ] 4.7.3 Benchmark: 10-30x faster than Numba path for full backtest

### Unit Tests

```
cpp/tests/test_event_loop.cpp:
  - test_events_ordered_by_timestamp
  - test_multi_symbol_interleaving
  - test_pause_resume
  - test_step_forward_n_events
  - test_stop_clears_queue
  - test_empty_queue_finishes

cpp/tests/test_global_clock.cpp:
  - test_two_symbols_synchronized
  - test_three_symbols_no_advance_past_lagging
  - test_mixed_granularity (M1 + H1)

cpp/tests/test_state_manager.cpp:
  - test_initial_balance
  - test_equity_calculation (balance + unrealized PnL)
  - test_add_position_updates_margin
  - test_close_position_updates_balance
  - test_mae_mfe_tracking
  - test_multiple_positions_equity

cpp/tests/test_engine.cpp:
  - test_engine_runs_all_bars
  - test_engine_calls_on_bar_callback
  - test_engine_buy_command
  - test_engine_sell_command
  - test_engine_close_position
  - test_engine_full_backtest_simple_strategy

tests/unit/bridge/test_engine.py:
  - test_engine_import_and_create
  - test_load_bars_from_numpy
  - test_on_bar_callback_called
  - test_account_state_accessible
  - test_positions_accessible
  - test_full_backtest_matches_python_engine
```

### Usage Example

```python
# tests/usage/bridge/usage_cpp_engine.py
"""Run a simple backtest through the C++ engine."""
import numpy as np
import hqt_engine

# Create engine
config = hqt_engine.EngineConfig()
config.initial_balance = 10000.0
config.leverage = 100
engine = hqt_engine.Engine(config)

# Load EURUSD data (OHLCV as NumPy array)
data = np.loadtxt("data/EURUSD_H1.csv", delimiter=",", skiprows=1)
engine.load_bars(symbol_id=0, ohlcv=data)

# Simple callback: buy when close > open, sell when close < open
def on_bar(symbol_id, bar):
    if bar.close > bar.open:
        engine.buy(symbol_id, volume=0.1)
    elif bar.close < bar.open:
        if len(engine.positions()) > 0:
            engine.close_position(engine.positions()[0].ticket)

engine.set_on_bar(on_bar)
engine.run()

print(f"Final balance: {engine.account().balance:.2f}")
print(f"Total trades:  {len(engine.history_deals())}")
print("Phase 4 verification: PASSED")
```

### Commit Message
```
feat(cpp): implement C++ event loop, state manager, and engine facade

- Implement priority-queue event loop with pause/resume/step-forward support
- Implement GlobalClock for multi-asset time synchronization
- Implement StateManager with account, position, order, and deal tracking
- Implement Engine facade: load_bars(), set_on_bar(), run(), buy(), sell()
- Equity recalculated on every tick: balance + sum(unrealized PnL)
- MAE/MFE tracking moved from Python to C++ (eliminates per-tick Python calls)
- GIL released during C++ execution, acquired for Python strategy callbacks
- Zero-copy NumPy data loading via Nanobind
- Add Python adapter for backwards-compatible integration with existing simulator

SRS: CPP-FR-001 through CPP-FR-014
```

### Documentation
- `cpp/include/hqt/core/README.md` — Engine architecture, event flow diagram
- Update `docs/04_developer_setup.md` — How to use C++ engine from Python

### Verification Checklist
- [ ] All C++ tests pass
- [ ] All Python bridge tests pass
- [ ] Single-symbol backtest: C++ results match Python results
- [ ] Multi-symbol backtest: C++ GlobalClock orders correctly
- [ ] All 98 existing simulation tests pass (via adapter)
- [ ] Benchmark shows 10-30x speedup over Python/Numba

---

## Phase 5: C++ Matching Engine + Execution Models

**Duration:** 3-4 weeks
**Depends On:** Phase 4
**SRS Coverage:** CPP-FR-006 through CPP-FR-010, CPP-FR-015 through CPP-FR-018

### Tasks

- [ ] **5.1** Slippage model interface + implementations
  - [ ] 5.1.1 Create `cpp/include/hqt/matching/slippage_model.hpp` — `ISlippageModel` interface
  - [ ] 5.1.2 Implement: `ZeroSlippage`, `FixedSlippage`, `RandomSlippage`, `LatencyProfileSlippage`
  - [ ] 5.1.3 Create `cpp/tests/test_slippage.cpp`

- [ ] **5.2** Commission model interface + implementations
  - [ ] 5.2.1 Create `cpp/include/hqt/matching/commission_model.hpp` — `ICommissionModel`
  - [ ] 5.2.2 Implement: `FixedPerLot`, `FixedPerTrade`, `SpreadMarkup`, `PercentageOfValue`
  - [ ] 5.2.3 Maintain round-trip commission on close model (matching current behavior)
  - [ ] 5.2.4 Create `cpp/tests/test_commission.cpp`

- [ ] **5.3** Swap model interface + implementations
  - [ ] 5.3.1 Create `cpp/include/hqt/matching/swap_model.hpp` — `ISwapModel`
  - [ ] 5.3.2 Implement: points-based, percentage-based, money-based
  - [ ] 5.3.3 Rollover time configuration
  - [ ] 5.3.4 Create `cpp/tests/test_swap.cpp`

- [ ] **5.4** Spread model interface + implementations
  - [ ] 5.4.1 Create `cpp/include/hqt/matching/spread_model.hpp` — `ISpreadModel`
  - [ ] 5.4.2 Implement: `FixedSpread`, `HistoricalSpread`, `TimeOfDaySpread`
  - [ ] 5.4.3 Create `cpp/tests/test_spread.cpp`

- [ ] **5.5** Matching engine
  - [ ] 5.5.1 Create `cpp/include/hqt/matching/matching_engine.hpp`
  - [ ] 5.5.2 Evaluate pending orders against each tick
  - [ ] 5.5.3 Calculate fill price (base + slippage + spread)
  - [ ] 5.5.4 Apply commission on close
  - [ ] 5.5.5 Gap handling: fill at gap price, not stop level
  - [ ] 5.5.6 Create `cpp/tests/test_matching_engine.cpp`

- [ ] **5.6** Integration
  - [ ] 5.6.1 Wire matching engine into Engine facade
  - [ ] 5.6.2 Configure execution models via EngineConfig
  - [ ] 5.6.3 Verify: results match current Python simulation for all order types

### Unit Tests

```
cpp/tests/test_slippage.cpp:
  - test_zero_slippage
  - test_fixed_slippage_buy (price + N points)
  - test_fixed_slippage_sell (price - N points)
  - test_random_slippage_within_range
  - test_random_slippage_seeded_deterministic

cpp/tests/test_commission.cpp:
  - test_fixed_per_lot
  - test_round_trip_on_close_only
  - test_balance_unchanged_on_entry
  - test_commission_deducted_on_close

cpp/tests/test_matching_engine.cpp:
  - test_market_buy_fills_at_ask
  - test_market_sell_fills_at_bid
  - test_limit_buy_fills_at_or_below
  - test_limit_sell_fills_at_or_above
  - test_stop_buy_triggers_above
  - test_stop_sell_triggers_below
  - test_gap_past_sl_fills_at_gap_price
  - test_gap_past_tp_fills_at_gap_price
  - test_expired_order_removed
```

### Commit Message
```
feat(cpp): implement matching engine with slippage, commission, swap, and spread models

- Add ISlippageModel interface with 4 implementations (zero, fixed, random, latency)
- Add ICommissionModel with round-trip on close model (matching current Python behavior)
- Add ISwapModel with points/percentage/money modes
- Add ISpreadModel with fixed/historical/time-of-day modes
- Implement MatchingEngine: order evaluation, fill price calculation, gap handling
- Gap scenarios: price gaps past SL/TP → fill at gap price, not stop level
- All models configurable via EngineConfig
- Seeded PRNG for deterministic slippage (reproducible backtests)

SRS: CPP-FR-006 through CPP-FR-010, CPP-FR-015 through CPP-FR-018
```

### Verification Checklist
- [ ] All C++ matching tests pass
- [ ] Market, limit, stop orders fill correctly
- [ ] Gap past SL fills at gap price
- [ ] Round-trip commission model matches current Python behavior
- [ ] Deterministic: same seed = same slippage = same results
- [ ] All existing simulation tests pass

---

## Phase 6: C++ Order/Position/Margin/Currency

**Duration:** 3-4 weeks
**Depends On:** Phase 5
**SRS Coverage:** TRD-FR-001 through TRD-FR-023

### Tasks

- [ ] **6.1** Order manager
  - [ ] 6.1.1 Create `cpp/include/hqt/state/order_manager.hpp` — all 8 order types
  - [ ] 6.1.2 Order parameters: symbol, volume, price, SL, TP, deviation, filling, expiration
  - [ ] 6.1.3 Trailing stop: fixed distance, ATR-based, step trailing
  - [ ] 6.1.4 Create `cpp/tests/test_order_manager.cpp`

- [ ] **6.2** Currency conversion engine
  - [ ] 6.2.1 Create `cpp/include/hqt/market/currency_converter.hpp` — dependency graph
  - [ ] 6.2.2 Auto-resolve: EURJPY profit in USD account → USDJPY rate
  - [ ] 6.2.3 Rates update on every tick
  - [ ] 6.2.4 ConfigError if conversion path missing at init
  - [ ] 6.2.5 Create `cpp/tests/test_currency_converter.cpp`

- [ ] **6.3** Margin calculator
  - [ ] 6.3.1 Create `cpp/include/hqt/margin/margin_calculator.hpp` — all 6 MT5 modes
  - [ ] 6.3.2 Total margin, free margin, margin level tracking
  - [ ] 6.3.3 Margin call enforcement (reject orders at <100%)
  - [ ] 6.3.4 Stop-out simulation (close largest loser at <50%)
  - [ ] 6.3.5 Create `cpp/tests/test_margin_calculator.cpp`

- [ ] **6.4** Write-ahead log
  - [ ] 6.4.1 Create `cpp/include/hqt/journal/write_ahead_log.hpp` — binary WAL with CRC32
  - [ ] 6.4.2 Every state-changing operation journaled before execution
  - [ ] 6.4.3 Crash recovery: replay uncommitted entries
  - [ ] 6.4.4 Create `cpp/tests/test_wal.cpp`

- [ ] **6.5** Bridge exposure
  - [ ] 6.5.1 Create `bridge/src/bind_commands.cpp` — buy, sell, modify, close, cancel
  - [ ] 6.5.2 Expose account, positions, orders, deals as read-only Python properties
  - [ ] 6.5.3 Fixed-point → double conversion at bridge boundary

- [ ] **6.6** Full integration
  - [ ] 6.6.1 C++ Engine now handles complete simulation lifecycle
  - [ ] 6.6.2 Python `SimulationEngine` becomes thin wrapper
  - [ ] 6.6.3 Full backtest with all features via C++ engine

### Unit Tests

```
cpp/tests/test_order_manager.cpp:
  - test_all_8_order_types
  - test_trailing_stop_fixed
  - test_trailing_stop_atr
  - test_order_expiration_gtc
  - test_order_expiration_today
  - test_order_expiration_specified

cpp/tests/test_currency_converter.cpp:
  - test_eurusd_profit_in_usd (direct)
  - test_eurjpy_profit_in_usd (cross: needs USDJPY)
  - test_xauusd_profit_in_usd
  - test_missing_conversion_pair_raises_error
  - test_rates_update_on_tick

cpp/tests/test_margin_calculator.cpp:
  - test_margin_mode_0_through_6
  - test_margin_call_blocks_new_orders
  - test_stop_out_closes_largest_loser
  - test_free_margin_calculation
  - test_margin_level_calculation

cpp/tests/test_wal.cpp:
  - test_write_and_read_entries
  - test_crc32_checksum_validation
  - test_crash_recovery_replays_uncommitted
  - test_committed_entries_not_replayed
```

### Commit Message
```
feat(cpp): complete C++ trading engine with orders, margin, currency conversion, and WAL

- Implement OrderManager supporting all 8 MT5 order types with trailing stops
- Implement CurrencyConverter with dependency graph for cross-pair PnL calculation
- Implement MarginCalculator with all 6 MT5 margin modes, margin call, and stop-out
- Implement WriteAheadLog with CRC32 checksums for crash recovery
- C++ Engine now handles complete simulation lifecycle
- Python SimulationEngine becomes thin orchestrator over C++ core
- Fixed-point prices converted to double at Nanobind bridge boundary

SRS: TRD-FR-001 through TRD-FR-023, FND-FR-040 through FND-FR-042
```

### Verification Checklist
- [ ] Full backtest with all features matches Python engine output
- [ ] Currency conversion: cross-pair profits calculated correctly
- [ ] Margin call blocks orders, stop-out closes positions
- [ ] WAL: kill mid-backtest, restart, state recovered
- [ ] All existing simulation tests pass
- [ ] Benchmark: 50-100x faster than original Python

---

## Phase 7: Trading Framework Unification

**Duration:** 2-3 weeks
**Depends On:** Phase 6
**SRS Coverage:** TRD-FR-001 through TRD-FR-008

### Tasks

- [ ] **7.1** Define unified interface
  - [ ] 7.1.1 Create `apps/trading/__init__.py`
  - [ ] 7.1.2 Create `apps/trading/interfaces.py` — `ITradingContext` ABC
  - [ ] 7.1.3 Create `apps/trading/types.py` — `OrderResult`, `OrderRequest`, `OrderType`, etc.

- [ ] **7.2** Implement backtest context
  - [ ] 7.2.1 Create `apps/trading/backtest_context.py` — wraps C++ Engine
  - [ ] 7.2.2 Implements all `ITradingContext` methods via C++ bridge

- [ ] **7.3** Mode router
  - [ ] 7.3.1 Create `apps/trading/mode_router.py` — `ModeRouter.create_context(mode, config)`
  - [ ] 7.3.2 Register: "backtest" → `BacktestContext`
  - [ ] 7.3.3 Stubs for "paper" and "live" (implemented in Phases 12-13)

- [ ] **7.4** Compatibility layer
  - [ ] 7.4.1 Update `apps/trade/__init__.py` — re-export from `apps.trading`
  - [ ] 7.4.2 Ensure all modules importing from `apps.trade` still work

### Unit Tests

```
tests/unit/trading/test_interfaces.py:
  - test_itradingcontext_is_abstract
  - test_backtest_context_implements_interface
  - test_buy_returns_order_result
  - test_sell_returns_order_result
  - test_account_property_returns_account_info
  - test_positions_property_returns_list

tests/unit/trading/test_mode_router.py:
  - test_backtest_mode_returns_backtest_context
  - test_paper_mode_returns_paper_context (after Phase 13)
  - test_live_mode_returns_live_context (after Phase 12)
  - test_invalid_mode_raises_error
```

### Commit Message
```
feat(trading): implement unified ITradingContext interface with mode router

- Define ITradingContext ABC: buy, sell, close_position, modify_order, etc.
- Implement BacktestContext wrapping C++ Engine
- Add ModeRouter: create_context("backtest"/"paper"/"live") returns appropriate backend
- Strategy code works identically across all trading modes
- Add compatibility re-exports in apps/trade/ for backwards compatibility

SRS: TRD-FR-001 through TRD-FR-008
```

### Verification Checklist
- [ ] Strategy code unchanged, works through new interface
- [ ] Backtest results identical via new `BacktestContext`
- [ ] Old `apps.trade` imports still work
- [ ] All existing tests pass

---

## Phase 8: Strategy Framework Enhancement

**Duration:** 2-3 weeks
**Depends On:** Phase 7
**SRS Coverage:** STR-FR-001 through STR-FR-014

### Tasks

- [ ] **8.1** Enhanced strategy base class
  - [ ] 8.1.1 Update `apps/strategy/base.py` — add `on_tick()`, `on_trade()`, `on_deinit()`
  - [ ] 8.1.2 Add `ITradingContext` injection via constructor
  - [ ] 8.1.3 Add `get_bars(symbol, timeframe, count, shift)` — PIT-safe multi-timeframe access
  - [ ] 8.1.4 Add `symbols` and `timeframes` class attributes

- [ ] **8.2** Strategy parameters
  - [ ] 8.2.1 Create `apps/strategy/parameter.py` — `StrategyParameter` descriptor
  - [ ] 8.2.2 Auto-discovery of parameters via introspection
  - [ ] 8.2.3 Generate parameter grid from descriptors

- [ ] **8.3** Indicator reorganization
  - [ ] 8.3.1 Create `apps/indicator/base.py` — `Indicator` ABC with `calculate()`, `update()`, `reset()`, `ready`
  - [ ] 8.3.2 Reorganize into: `trend.py`, `momentum.py`, `volatility.py`, `volume.py`
  - [ ] 8.3.3 Add utility functions: crossover detection, divergence detection
  - [ ] 8.3.4 Keep existing indicator functions as aliases

- [ ] **8.4** Strategy registry
  - [ ] 8.4.1 Create `apps/strategy/registry.py` — auto-discover strategy classes
  - [ ] 8.4.2 Register by name for API and UI access

- [ ] **8.5** Migration
  - [ ] 8.5.1 Keep old `BaseStrategy` as compatibility alias
  - [ ] 8.5.2 Migrate existing strategies to new framework
  - [ ] 8.5.3 Verify optimizer discovers `StrategyParameter` descriptors

### Unit Tests

```
tests/unit/strategy/test_enhanced_strategy.py:
  - test_strategy_receives_trading_context
  - test_buy_delegates_to_context
  - test_get_bars_pit_safe
  - test_on_tick_called_per_tick
  - test_on_bar_called_per_bar
  - test_on_trade_called_on_fill

tests/unit/strategy/test_parameters.py:
  - test_parameter_declaration
  - test_parameter_auto_discovery
  - test_parameter_grid_generation
  - test_parameter_bounds_validation

tests/unit/indicator/test_base_indicator.py:
  - test_indicator_calculate
  - test_indicator_incremental_update
  - test_indicator_ready_after_warmup
  - test_crossover_detection
```

### Commit Message
```
feat(strategy): enhance strategy framework with parameters, multi-timeframe, and indicator base

- Add on_tick(), on_trade(), on_deinit() lifecycle methods to Strategy
- Add ITradingContext injection (strategies use buy/sell via context)
- Add StrategyParameter descriptor for optimization integration
- Add PIT-safe get_bars() for multi-timeframe data access
- Add Indicator base class with calculate(), update(), reset(), ready
- Reorganize indicators by category with utility functions
- Add strategy registry for auto-discovery

SRS: STR-FR-001 through STR-FR-014
```

### Verification Checklist
- [ ] Existing strategies work with enhanced framework
- [ ] Optimizer auto-discovers StrategyParameter descriptors
- [ ] PIT correctness: D1 bars during intraday only show completed bars
- [ ] Indicator incremental update matches full recalculation
- [ ] All existing tests pass

---

## Phase 9: Backtesting Engine Rewrite

**Duration:** 3-4 weeks
**Depends On:** Phases 7, 8
**SRS Coverage:** BKT-FR-001 through BKT-FR-046

### Tasks

- [ ] **9.1** Event-driven engine
  - [ ] 9.1.1 Create `apps/backtesting/__init__.py`
  - [ ] 9.1.2 Create `apps/backtesting/engine/event_driven.py` — orchestrates C++ core
  - [ ] 9.1.3 Load data → init strategy → register callbacks → run → collect results
  - [ ] 9.1.4 Running equity curve at configurable intervals

- [ ] **9.2** Vectorized engine
  - [ ] 9.2.1 Create `apps/backtesting/engine/vectorized.py` — accepts signal arrays
  - [ ] 9.2.2 No per-bar callbacks, maximum speed
  - [ ] 9.2.3 Compatible `BacktestResult` output

- [ ] **9.3** Multi-asset portfolio engine
  - [ ] 9.3.1 Create `apps/backtesting/engine/portfolio.py` — wraps C++ Engine with GlobalClock
  - [ ] 9.3.2 Multiple symbols, shared account state
  - [ ] 9.3.3 Replace `apps/simulation/portfolio.py`

- [ ] **9.4** Performance metrics
  - [ ] 9.4.1 Create `apps/backtesting/metrics/` — reorganize `apps/finance/`
  - [ ] 9.4.2 Returns, risk, trade, ratios, efficiency, distribution, benchmark metrics
  - [ ] 9.4.3 `MetricsCalculator.calculate(result) -> MetricsReport`

- [ ] **9.5** Visualization integration
  - [ ] 9.5.1 Connect `apps/plotting/` to new `BacktestResult`
  - [ ] 9.5.2 Equity curve, drawdown, monthly heatmap, trade distribution

- [ ] **9.6** Storage & reproducibility
  - [ ] 9.6.1 Create `apps/backtesting/storage/` — store all backtest artifacts
  - [ ] 9.6.2 Record: strategy version, params, config, data hashes, seed, metrics, trade log
  - [ ] 9.6.3 `reproduce(backtest_id)` retrieves all and re-runs

- [ ] **9.7** Compatibility
  - [ ] 9.7.1 Keep `apps/simulation/` as compatibility layer
  - [ ] 9.7.2 `TradeSimulator.run()` delegates to new backtesting engine

### Commit Message
```
feat(backtesting): rewrite backtesting engine with event-driven, vectorized, and portfolio modes

- Implement EventDrivenEngine orchestrating C++ core
- Implement VectorizedEngine for signal-array-based fast simulation
- Implement PortfolioEngine with C++ GlobalClock for multi-asset backtesting
- Reorganize performance metrics from apps/finance/ to apps/backtesting/metrics/
- Add backtest storage with full reproducibility (strategy version, data hashes, seed)
- Add reproduce(backtest_id) command for deterministic replay
- Connect visualization pipeline to new BacktestResult

SRS: BKT-FR-001 through BKT-FR-046
```

---

## Phase 10: Optimization Engine

**Duration:** 3-4 weeks
**Depends On:** Phase 9
**SRS Coverage:** BKT-FR-024 through BKT-FR-052

### Tasks

- [ ] **10.1** Parallel execution framework
  - [ ] 10.1.1 Create `apps/optimization/parallel/executor.py` — `ParallelExecutor` ABC
  - [ ] 10.1.2 Create `apps/optimization/parallel/multiprocessing_executor.py` — `ProcessPoolExecutor` with C++ engines
  - [ ] 10.1.3 Create `apps/optimization/parallel/ray_executor.py` — Ray remote functions (optional)
  - [ ] 10.1.4 Workers share read-only Parquet data via mmap

- [ ] **10.2** Grid search
  - [ ] 10.2.1 Create `apps/optimization/grid.py` — exhaustive parameter search
  - [ ] 10.2.2 Configurable objective functions (Sharpe, Sortino, Calmar, profit factor, custom)

- [ ] **10.3** Bayesian optimization
  - [ ] 10.3.1 Create `apps/optimization/bayesian.py` — Optuna integration

- [ ] **10.4** Walk-forward optimization
  - [ ] 10.4.1 Create `apps/optimization/wfo.py` — rolling/anchored windows
  - [ ] 10.4.2 Combined OOS equity curve, walk-forward efficiency

- [ ] **10.5** Monte Carlo simulation
  - [ ] 10.5.1 Create `apps/optimization/monte_carlo.py` — trade resampling + parameter perturbation
  - [ ] 10.5.2 Percentile distributions (5th, 25th, 50th, 75th, 95th)

- [ ] **10.6** Edge Lab
  - [ ] 10.6.1 Create `apps/optimization/edge_lab/` — EDS-0 through EDS-3
  - [ ] 10.6.2 Statistical reports with confidence intervals, p-values

### Commit Message
```
feat(optimization): implement distributed optimization with multiprocessing and Ray support

- Add ParallelExecutor abstraction with multiprocessing (default) and Ray (optional) backends
- Implement grid search, Bayesian optimization (Optuna), walk-forward optimization
- Implement Monte Carlo simulation with trade resampling and parameter perturbation
- Implement Edge Lab (EDS-0 through EDS-3) for statistical edge discovery
- Each worker runs independent C++ Engine instance (true parallelism, no GIL)
- Workers share read-only Parquet data via mmap

SRS: BKT-FR-024 through BKT-FR-052
```

---

## Phase 11: Risk Management System

**Duration:** 2-3 weeks
**Depends On:** Phase 7
**SRS Coverage:** RSK-FR-001 through RSK-FR-018

### Tasks

- [ ] **11.1** Risk governor — final gatekeeper for all orders
- [ ] **11.2** Position sizing — FixedLot, RiskPercent, Kelly, ATRBased, FixedCapital, Milestone
- [ ] **11.3** Regime detection — HMM-based market state classification
- [ ] **11.4** Portfolio allocation — equal weight, risk parity, inverse volatility
- [ ] **11.5** Risk monitoring — real-time dashboard data
- [ ] **11.6** Circuit breakers and equity kill switch

### Commit Message
```
feat(risk): implement risk management with governor, position sizing, and regime detection

SRS: RSK-FR-001 through RSK-FR-018
```

---

## Phase 12: Live Trading System

**Duration:** 4-5 weeks
**Depends On:** Phases 7, 11
**SRS Coverage:** LIV-FR-001 through LIV-FR-022

### Tasks

- [ ] **12.1** MQL5 Bridge EA (`mql5/HQT_Bridge.mq5`) — ZMQ PUB ticks, ZMQ REP orders
- [ ] **12.2** C++ ZMQ broadcaster — non-blocking PUB, topic-based routing
- [ ] **12.3** C++ ZMQ broker gateway — REQ/REP for order execution
- [ ] **12.4** Live trading engine — C++ engine with live data from ZMQ
- [ ] **12.5** `LiveTradingContext` implementing `ITradingContext`
- [ ] **12.6** Emergency shutdown — cancel → close → halt → notify
- [ ] **12.7** State reconciliation — compare local vs broker state
- [ ] **12.8** Auto-reconnection with exponential backoff

### Commit Message
```
feat(live): implement live trading with C++ engine, ZMQ broker gateway, and emergency shutdown

SRS: LIV-FR-001 through LIV-FR-022
```

---

## Phase 13: Paper Trading System

**Duration:** 2-3 weeks
**Depends On:** Phase 12
**SRS Coverage:** PAP-FR-001 through PAP-FR-005

### Tasks

- [ ] **13.1** `PaperTradingContext` — simulated fills on live data
- [ ] **13.2** Same slippage/commission/spread models as backtesting
- [ ] **13.3** Account snapshots at configurable intervals
- [ ] **13.4** Switch via config: `mode = "paper"` vs `mode = "live"`

### Commit Message
```
feat(paper): implement paper trading with simulated execution on live data

SRS: PAP-FR-001 through PAP-FR-005
```

---

## Phase 14: Notification System

**Duration:** 1-2 weeks
**Depends On:** Phase 2
**SRS Coverage:** NTF-FR-001 through NTF-FR-007

### Tasks

- [ ] **14.1** Notification models and manager
- [ ] **14.2** Telegram channel (Bot API)
- [ ] **14.3** Email channel (SMTP/TLS)
- [ ] **14.4** Rate limiting and routing rules
- [ ] **14.5** Database storage for audit trail

### Commit Message
```
feat(notifications): implement Telegram and email notifications with rate limiting

SRS: NTF-FR-001 through NTF-FR-007
```

---

## Phase 15: API Layer Enhancement

**Duration:** 2-3 weeks
**Depends On:** Phases 9, 12
**SRS Coverage:** API-FR-001 through API-FR-005

### Tasks

- [ ] **15.1** REST endpoints for all backend functionality
- [ ] **15.2** WebSocket endpoints for real-time streaming
- [ ] **15.3** JWT authentication on all endpoints
- [ ] **15.4** Auto-generated OpenAPI documentation

### Commit Message
```
feat(api): enhance FastAPI layer with full backend access, WebSocket, and JWT auth

SRS: API-FR-001 through API-FR-005
```

---

## Phase 16: Database Migration

**Duration:** 3-4 weeks
**Depends On:** Phase 15
**SRS Coverage:** FND-FR-031 through FND-FR-036

### Tasks

- [ ] **16.1** SQLAlchemy 2.x ORM models for all tables
- [ ] **16.2** Alembic migration scripts (initial schema + data migration)
- [ ] **16.3** Migrate existing data from current SQLite
- [ ] **16.4** Connection pooling configuration
- [ ] **16.5** Optional PostgreSQL support
- [ ] **16.6** Replace `apps/sqlite/` with `apps/database/`

### Commit Message
```
feat(database): migrate to SQLAlchemy ORM with Alembic migrations

SRS: FND-FR-031 through FND-FR-036
```

---

## Phase 17: Observability, CI/CD, Polish

**Duration:** 2-3 weeks
**Depends On:** All previous phases
**SRS Coverage:** XCC-FR-001 through XCC-FR-020

### Tasks

- [ ] **17.1** Health metrics (tick rate, bridge latency, memory usage, queue depth)
- [ ] **17.2** Composite versioning: `{version}+cpp.{hash}.py.{version}`
- [ ] **17.3** Deterministic replay: `reproduce(backtest_id)`
- [ ] **17.4** GitHub Actions CI: Windows MSVC + Linux GCC build matrix
- [ ] **17.5** Static analysis: clang-tidy (C++), mypy + ruff (Python)
- [ ] **17.6** Memory sanitizers: AddressSanitizer, UBSan on C++ tests
- [ ] **17.7** Developer onboarding documentation
- [ ] **17.8** Remove all deprecated compatibility layers
- [ ] **17.9** Final cleanup of old modules (`apps/simulation/`, `apps/trade/`, `apps/finance/`, `apps/edge/`, `apps/sqlite/`)

### Commit Message
```
feat(observability): add health monitoring, CI/CD pipeline, and cleanup deprecated modules

SRS: XCC-FR-001 through XCC-FR-020
```

---

## Progress Tracking

### Phase Completion Log

| Phase | Started | Completed | Tests Added | Tests Passing | Notes |
|-------|---------|-----------|-------------|---------------|-------|
| 0 | — | — | — | — | |
| 1 | — | — | — | — | |
| 2 | — | — | — | — | |
| 3 | — | — | — | — | |
| 4 | — | — | — | — | |
| 5 | — | — | — | — | |
| 6 | — | — | — | — | |
| 7 | — | — | — | — | |
| 8 | — | — | — | — | |
| 9 | — | — | — | — | |
| 10 | — | — | — | — | |
| 11 | — | — | — | — | |
| 12 | — | — | — | — | |
| 13 | — | — | — | — | |
| 14 | — | — | — | — | |
| 15 | — | — | — | — | |
| 16 | — | — | — | — | |
| 17 | — | — | — | — | |

### Cumulative Test Count Target

| After Phase | C++ Tests | Bridge Tests | Python Tests | Total |
|-------------|-----------|--------------|--------------|-------|
| 0 | 2 | 3 | 98 | 103 |
| 1 | 25 | 10 | 98 | 133 |
| 2 | 30 | 12 | 115 | 157 |
| 3 | 30 | 12 | 145 | 187 |
| 4 | 55 | 20 | 155 | 230 |
| 5 | 80 | 25 | 165 | 270 |
| 6 | 110 | 30 | 175 | 315 |
| 7 | 110 | 30 | 190 | 330 |
| 8 | 110 | 30 | 215 | 355 |
| 9 | 110 | 30 | 245 | 385 |
| 10 | 110 | 30 | 280 | 420 |
| 11 | 110 | 30 | 300 | 440 |
| 12 | 120 | 35 | 330 | 485 |
| 13 | 120 | 35 | 345 | 500 |
| 14 | 120 | 35 | 355 | 510 |
| 15 | 120 | 35 | 375 | 530 |
| 16 | 120 | 35 | 395 | 550 |
| 17 | 125 | 35 | 400 | 560 |

### Performance Benchmark Targets

| After Phase | Backtest Speed (1yr H1) | Optimization (1000 combos) |
|-------------|------------------------|---------------------------|
| Current | ~40s | ~11 hours |
| 1 | ~20s | ~5.5 hours |
| 4 | ~2s | ~33 min |
| 5 | ~1s | ~17 min |
| 6 | ~0.5s | ~8 min |
| 10 | ~0.5s | ~30 sec (16 cores) |

---

*End of Document — IMP-HQTBS-001 v1.0.0*
