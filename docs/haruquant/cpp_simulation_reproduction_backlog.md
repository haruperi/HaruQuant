# C++ Simulation Reproduction Backlog (apps/simulation -> cpp)

## Goal
Replace `apps/simulation` runtime hot-path with a C++ engine while preserving Python-facing behavior and MT5-style semantics.

## Delivery Strategy
- Keep PRs small and independently testable.
- Maintain Python compatibility during migration via backend selector.
- Prefer additive changes first, then switch defaults after parity gates pass.

## Conventions
- New C++ simulation code lives in `cpp/include/sim/*` and `cpp/src/sim/*`.
- New C++ tests live in `cpp/tests/test_sim_*.cpp`.
- Python bridge updates live in `bridge/src/*`.
- Python compatibility layer stays in `apps/simulation/*`.

## PR-001: Simulation Module Scaffold
**Scope**
- Create simulation module skeleton in C++ and wire into CMake.

**Target files**
- `cpp/include/sim/simulator_state.hpp` (new)
- `cpp/src/sim/simulator_state.cpp` (new)
- `cpp/CMakeLists.txt` (update: add sim source files)
- `cpp/tests/CMakeLists.txt` (update: include new test)
- `cpp/tests/test_simulator_state.cpp` (new)

**Acceptance tests**
- `python scripts/build_cpp.py --test`
- New test `SimulatorStateTest.DefaultConstruction` passes.

---

## PR-002: MT5-like Data Containers in C++
**Scope**
- Port core simulator data shapes from `apps/simulation/data.py` to C++ DTOs.

**Target files**
- `cpp/include/sim/sim_data.hpp` (new)
- `cpp/src/sim/sim_data.cpp` (new)
- `cpp/tests/test_sim_data.cpp` (new)

**Acceptance tests**
- `python scripts/build_cpp.py --test`
- Tests validate default values and `_asdict`-equivalent serialization mapping.

---

## PR-003: SimulatorClient Read API Parity
**Scope**
- Implement non-mutating API methods:
  - `account_info`, `symbol_info`, `symbol_info_tick`, `positions_get`, `orders_get`, `history_orders_get`, `history_deals_get`, `last_error`, `trade_retcode_description`.

**Target files**
- `cpp/include/sim/simulator_client.hpp` (new)
- `cpp/src/sim/simulator_client.cpp` (new)
- `cpp/tests/test_simulator_client_getters.cpp` (new)

**Acceptance tests**
- `python scripts/build_cpp.py --test`
- Tests cover filters by `ticket` and `symbol` and empty-container behavior.

---

## PR-004: Margin and Profit Calculation Parity
**Scope**
- Port `order_calc_margin` and `order_calc_profit` logic from `apps/simulation/data.py`.

**Target files**
- `cpp/include/sim/calculators.hpp` (new)
- `cpp/src/sim/calculators.cpp` (new)
- `cpp/src/sim/simulator_client.cpp` (update)
- `cpp/tests/test_sim_calculators.cpp` (new)

**Acceptance tests**
- `python scripts/build_cpp.py --test`
- Tests verify all supported `trade_calc_mode` branches and buy/sell symmetry.

---

## PR-005: Trade Gateway for Market Orders
**Scope**
- Implement `order_send` minimal flow for market actions using existing `CTrade`.
- Map MT5-like request/result fields and retcodes.

**Target files**
- `cpp/include/sim/trade_gateway.hpp` (new)
- `cpp/src/sim/trade_gateway.cpp` (new)
- `cpp/src/sim/simulator_client.cpp` (update)
- `cpp/tests/test_sim_order_send_market.cpp` (new)

**Acceptance tests**
- `python scripts/build_cpp.py --test`
- Tests verify successful buy/sell open and invalid request retcodes.

---

## PR-006: Pending Orders + History Archival
**Scope**
- Implement pending order placement/modify/delete flows and history transitions.

**Target files**
- `cpp/src/sim/simulator_client.cpp` (update)
- `cpp/include/sim/order_lifecycle.hpp` (new)
- `cpp/src/sim/order_lifecycle.cpp` (new)
- `cpp/tests/test_sim_pending_orders.cpp` (new)

**Acceptance tests**
- `python scripts/build_cpp.py --test`
- Tests verify:
  - pending order creation fields
  - modify/delete behavior
  - history state (`filled/canceled/expired`) archival.

---

## PR-007: Single-Symbol Backtest Engine (trading_timeframe)
**Scope**
- Implement single-symbol run loop equivalent for `trading_timeframe` mode.
- Support per-bar tick update + signal processing callback hook.

**Target files**
- `cpp/include/sim/backtest_engine.hpp` (new)
- `cpp/src/sim/backtest_engine.cpp` (new)
- `cpp/tests/test_sim_backtest_single_symbol.cpp` (new)

**Acceptance tests**
- `python scripts/build_cpp.py --test`
- Tests verify deterministic event order and open/close sequencing from synthetic signals.

---

## PR-008: Position Monitoring + SL/TP Auto-Close + Account Monitor
**Scope**
- Port `monitor_positions` and `monitor_account` behavior.
- Ensure SL/TP triggers close positions correctly for buy/sell.

**Target files**
- `cpp/src/sim/backtest_engine.cpp` (update)
- `cpp/include/sim/account_monitor.hpp` (new)
- `cpp/src/sim/account_monitor.cpp` (new)
- `cpp/tests/test_sim_position_monitor.cpp` (new)

**Acceptance tests**
- `python scripts/build_cpp.py --test`
- Tests verify equity/margin updates and SL/TP close reasons.

---

## PR-009: Pending Trigger Monitoring in Engine Loop
**Scope**
- Port pending trigger checks (`buy/sell limit/stop`) and expiry handling in run loop.

**Target files**
- `cpp/src/sim/backtest_engine.cpp` (update)
- `cpp/tests/test_sim_pending_trigger_monitor.cpp` (new)

**Acceptance tests**
- `python scripts/build_cpp.py --test`
- Tests verify trigger conditions and expirations by timestamp.

---

## PR-010: Tick Modelling Modes
**Scope**
- Port modeling helpers:
  - M1 OHLC 4-point
  - synthetic ticks (`_support_point_split`, `_expand_ticks` behavior)
  - real tick passthrough.

**Target files**
- `cpp/include/sim/tick_model.hpp` (new)
- `cpp/src/sim/tick_model.cpp` (new)
- `cpp/src/sim/backtest_engine.cpp` (update)
- `cpp/tests/test_sim_tick_models.cpp` (new)

**Acceptance tests**
- `python scripts/build_cpp.py --test`
- Tests verify generated sequence length/order and deterministic output.

---

## PR-011: Trade Record Tracking (MAE/MFE/Bars/R)
**Scope**
- Port `TradeRecord` and tracking updates from `apps/simulation/records.py`.

**Target files**
- `cpp/include/sim/trade_record.hpp` (new)
- `cpp/src/sim/trade_record.cpp` (new)
- `cpp/src/sim/backtest_engine.cpp` (update)
- `cpp/tests/test_sim_trade_record.cpp` (new)

**Acceptance tests**
- `python scripts/build_cpp.py --test`
- Tests verify MAE/MFE, time-in-trade, bars-in-trade, and r-multiple.

---

## PR-012: Portfolio Engine in C++
**Scope**
- Implement multi-symbol synchronized loop and allocation-adjusted volume.
- Start with equal-weight allocation support.

**Target files**
- `cpp/include/sim/portfolio_engine.hpp` (new)
- `cpp/src/sim/portfolio_engine.cpp` (new)
- `cpp/tests/test_sim_portfolio_engine.cpp` (new)

**Acceptance tests**
- `python scripts/build_cpp.py --test`
- Tests verify multi-symbol trade execution and allocation application.

---

## PR-013: Metrics and Result Aggregation
**Scope**
- Implement single-symbol and portfolio result metrics matching Python behavior.

**Target files**
- `cpp/include/sim/result_metrics.hpp` (new)
- `cpp/src/sim/result_metrics.cpp` (new)
- `cpp/tests/test_sim_result_metrics.cpp` (new)

**Acceptance tests**
- `python scripts/build_cpp.py --test`
- Tests verify total return, win rate, drawdown, profit factor, sharpe.

---

## PR-014: Nanobind Bindings for Simulation API
**Scope**
- Expose C++ simulator/backtest API and DTOs to Python.

**Target files**
- `bridge/src/module.cpp` (update)
- `bridge/src/sim_bindings.cpp` (new)
- `bridge/CMakeLists.txt` (update)

**Acceptance tests**
- `python scripts/build_cpp.py --test`
- `python scripts/build_cpp.py --install`
- New Python smoke test imports `hqt_engine` and opens/runs a basic sim.

---

## PR-015: Python Backend Selector + Adapter Layer
**Scope**
- Add backend switch without breaking API (default remains Python backend initially).

**Target files**
- `apps/simulation/backend.py` (new)
- `apps/simulation/__init__.py` (update)
- `apps/simulation/simulator.py` (minimal adapter hook)
- `apps/simulation/engine.py` (minimal adapter hook)

**Acceptance tests**
- Existing simulation tests pass with `SIM_ENGINE=python`.
- New smoke tests pass with `SIM_ENGINE=cpp` for basic open/close flow.

---

## PR-016: Session Integration with C++ Backend
**Scope**
- Route `SimulatorSession` execution paths through backend selector.

**Target files**
- `apps/simulation/session.py` (update)
- `apps/simulation/data.py` (minimal compatibility updates if needed)
- `apps/simulation/utils.py` (minimal compatibility updates if needed)

**Acceptance tests**
- Session-level manual trade + pending order scenarios pass for both backends.

---

## PR-017: Golden-Master Parity Harness
**Scope**
- Add deterministic fixtures and parity runner comparing Python backend vs C++ backend outputs.

**Target files**
- `tests/parity/test_sim_parity_single_symbol.py` (new)
- `tests/parity/test_sim_parity_pending.py` (new)
- `tests/parity/test_sim_parity_portfolio.py` (new)
- `tests/parity/fixtures/*.json` (new)

**Acceptance tests**
- Parity assertions pass within defined tolerances for pnl/metrics/trade counts.

---

## PR-018: Cutover + Documentation
**Scope**
- Flip default backend to C++ after parity gates pass.
- Document architecture and migration status.

**Target files**
- `apps/simulation/backend.py` (update default)
- `docs/haruquant/architecture.md` (update, full runtime architecture)
- `docs/haruquant/cpp_simulation_reproduction_backlog.md` (update status checklist)

**Acceptance tests**
- Full test suite green with default C++ backend.
- Manual fallback to Python backend still works.

---

## Gate Criteria
Before default cutover:
1. PR-001 to PR-017 merged.
2. Parity suite green on CI.
3. No known critical divergence in order lifecycle, SL/TP behavior, or account metrics.
4. Measured speedup documented against Python baseline.

## Notes
- Volume constraints currently have hardcoded fallback in C++ engine (`TODO` already added); keep that until MT5 metadata sourcing is wired.
- Keep changes additive and localized per PR to minimize merge risk.
