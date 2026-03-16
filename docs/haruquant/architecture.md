# HaruQuant Architecture Notes

## Edge Lab Metrics Boundary

- `apps/edge` no longer has a dedicated metrics module.
- Shared 1D performance math now lives directly in the existing finance modules:
  - `apps/finance/ratios.py` for ratio-style metrics
  - `apps/finance/drawdowns.py` for returns drawdown metrics
  - `apps/finance/metrics.py` for Edge-oriented summary helpers such as `median_mae_mfe()` and `compute_trade_metrics()`
- Edge runners import those finance functions directly so the metric logic is centralized without adding new files.

## Edge Lab Dataset Pipeline

- `apps/edge/data/validation.py` wraps the existing utility validator in `apps/utils/data_validator.py` to validate schema, OHLC logic, continuity, duplicates, spread, and volume.
- `apps/edge/data/cleaning.py` applies policy-driven cleaning for timezone normalization, missing bars, weekend/holiday filtering, and spread anomaly handling.
- `apps/edge/data/enrichment.py` adds analysis columns such as pip metadata, bar geometry, returns, direction labels, session fields, and rollover-hour flags.
- `apps/edge/datasets.py -> prepare_ohlcvs_dataset(...)` is the end-to-end orchestration entrypoint and returns a prepared DataFrame plus a report that separates warnings from fatal errors.

## Edge Lab Core Metric MVP

- `apps/edge/core_metrics/base.py` defines the normalized metric contract used by the MVP:
  - `MetricValue` for persisted metric rows
  - `MetricContext` for prepared dataset execution
  - `MetricCalculator` as the family interface
- `apps/edge/core_metrics/registry.py` keeps a small family registry so the profile builder can stay declarative.
- `apps/edge/core_metrics/service.py -> build_core_metric_profile(...)` builds the first descriptive pair profile from a prepared OHLCVS dataset.
- The initial metric families are:
  - `returns`
  - `roc`
  - `candles`
  - `ranges`
  - `volatility`
  - `spread`
  - `volume_activity`
- Persistence is intentionally normalized and reuses the existing SQLite edge manager:
  - `edge_core_metric_runs` stores one profile header plus validation/cleaning report JSON
  - `edge_core_metric_values` stores one row per metric (`family`, `metric_key`, numeric/text value, context JSON)
- API integration stays inside `apps/api/routes/edge.py`:
  - `POST /api/edge-lab/core-metrics/run`
  - `GET /api/edge-lab/core-metrics/runs`
  - `GET /api/edge-lab/core-metrics/runs/{run_id}`
- UI integration stays inside the existing Edge Lab surface:
  - `ui/src/app/(dashboard)/edge-lab/core-metric/page.tsx`
  - `ui/src/components/edge-lab/edge-lab-nav.tsx`

## Edge Lab Shared Dataset Flow

- Edge Lab now has a shared dataset-first UI flow similar to the Performance area.
- `ui/src/contexts/edge-lab-data-context.tsx` holds the active prepared dataset in React state and mirrors it to `sessionStorage`.
- `ui/src/app/(dashboard)/edge-lab/layout.tsx` wraps all Edge Lab tabs with that provider.
- `ui/src/app/(dashboard)/edge-lab/page.tsx` is the canonical place to:
  - fetch market data
  - run validation / cleaning / enrichment
  - inspect report state
  - preview the prepared dataset
- Backend support stays inside `apps/api/routes/edge.py`:
  - `POST /api/edge-lab/dataset/prepare`
  - `POST /api/edge-lab/seasonality` can now consume a serialized prepared dataset
  - `POST /api/edge-lab/core-metrics/run` can now consume a serialized prepared dataset
- First migrated consumers are:
  - `ui/src/app/(dashboard)/edge-lab/discovery/page.tsx`
  - `ui/src/app/(dashboard)/edge-lab/core-metric/page.tsx`
  - `ui/src/app/(dashboard)/edge-lab/seasonality/page.tsx`
- This removes repeated data-download forms from those tabs and keeps one session-scoped dataset across navigation.

## Trading Engine Tick Loop (Python Skeleton)

## API Backtest Runtime

- `apps/api/routes/simulator.py` now owns both `/api/simulator` and `/api/backtest` routes and uses the current trading engine path instead of the removed `apps.simulation` package.
- API backtests follow the same flow as the trading examples:
  - load bars
  - run `strategy.on_bar(...)`
  - generate ticks with `TicksGenerator`
  - execute ticks through `apps/trading/main.py -> Engine.run(...)`
  - save completed trades and equity curve through the SQLite backtest tables
- Multi-symbol portfolio API backtests merge per-symbol tick streams into one stable chronological DataFrame before calling `Engine.run(...)`.
- API backtests now also consume the projected Example 15 execution settings directly in the Python simulator path:
  - account seeding applies `initial_capital`, `leverage`, and per-lot `commission`
  - execution settings apply backtest slippage in `core.order_send(...)`
  - position sizing names are normalized at the route boundary (`fixed_percent -> fixed_risk`, `kelly_criterion -> kelly`, `volatility_adjusted_atr -> volatility`)
  - non-`fixed_lot` position sizing is wired through `Engine.configure_position_sizing(...)` without enabling the broader portfolio risk governor path

- Runtime entrypoint: `apps/trading/main.py -> Engine.run(data)`.
- Current skeleton expects tick-like DataFrame input with `bid` and `ask` columns.
- Hot loop path uses:
  - DataFrame -> NumPy conversion for `bid`/`ask` (`float64`, `copy=False`)
  - `_process_ticks_numba(...)` for a compiled per-tick loop when `numba` is available
  - an internal pure-Python fallback loop when `numba` is unavailable
- This keeps orchestration in Python while preparing the inner tick loop for future per-tick monitoring/risk logic.
- `Engine.configure_run_schedule(...)` enables optional callback scheduling in `Engine.run(...)`:
  - `positions_every`, `pending_orders_every`, `account_every`, `portfolio_every`, `risk_every`
  - `None` disables callback; positive integer runs callback every N ticks
  - when all schedule entries are `None`, `run(...)` stays on the fast Numba counting path
  - simulator-mode guards skip `monitor_positions` when there are no open positions and skip `monitor_pending_orders` when there are no pending orders
  - account/portfolio/risk scheduled callbacks are gated by a lightweight dirty flag and run only after state-changing monitor passes
- `Engine.run(...)` now executes trading signals directly from tick columns when present:
  - `entry_signal`: `1` buy / `-1` sell market entry (`ask` for buy, `bid` for sell; aligned with trade example behavior)
  - `exit_signal` (and alias `exit_trade`): `1` exit buy-side positions / `-1` exit sell-side positions
  - `pending_signal`: `1` buy stop, `-1` sell stop, `2` buy limit, `-2` sell limit
  - `cancel_pending_signal`: cancels matching pending order type for the same symbol
- `Engine.run(data, position_size=...)` can override per-run signal order volume (fallback is engine default `0.01`).
- `Engine.run(..., monitor_verbose=...)` controls verbosity passed to scheduled monitor callbacks (`monitor_positions`, `monitor_pending_orders`, `monitor_account`, `monitor_portfolio`, `monitor_risk`).
- `Engine.run(..., show_progress=True, progress_desc="Tester Progress")` can render a `tqdm` progress bar while the Python orchestration loop processes ticks.
- Tick signal schema now supports an optional second pending leg for breakout-style strategies:
  - `pending_signal_2`, `cancel_pending_signal_2`, `price_2`
  - `Engine.run(...)` applies both legs in the same tick, after cancel signals and before scheduled monitors
  - `TicksGenerator` propagates these columns from bars to generated ticks
- `core.monitor_pending_orders(...)` now enforces one-symbol breakout behavior when a pending triggers:
  - closes any existing open position for that symbol before opening the triggered side
  - removes sibling pending orders for that symbol after a successful trigger
- Signal execution uses `core.order_send(...)` and keeps scheduler callbacks unchanged.
- In `Engine` simulation flow, profit/margin calculations are now strict MT5-based:
  - uses `client.order_calc_profit(...)` and `client.order_calc_margin(...)`
  - no approximation fallback in Engine-driven execution paths; missing/failed access raises runtime error.
- Tick generation path (`apps/utils/data_manipulator.py -> TicksGenerator._generate_timeframe_ticks`) now builds output columns from NumPy arrays (4 ticks per bar) instead of Python `iterrows()` + dict appends, preserving the same output schema while reducing generation overhead.

## API Live Runtime

- `apps/api/routes/dashboard/market_hours.py` now uses stdlib `zoneinfo` instead of `pytz`, so dashboard market-hours no longer depends on an extra package at API startup.
- `apps/api/routes/optimization.py` now lazy-imports heavy optimization workers so the optimization router can load at startup even though deeper optimization internals still need migration off the removed `apps.simulation` package.
- `apps/api/routes/live.py` now imports cleanly against the current MT5/trading stack instead of the removed MT5 wrapper classes.
- Live modules under `apps/live` now use:
  - raw `client.account_info()` account snapshots
  - raw `client.symbol_info(symbol)` symbol snapshots
  - `apps/trading/trade.py -> Trade` for order execution helpers
- `apps/live/mt5_compat.py` provides the small compatibility accessors used by the live layer so the rest of the live flow can stay structurally unchanged.

## Simulator Risk Integration

- `apps/trading/main.py -> Engine.configure_risk_management(...)` enables optional simulator-side reuse of the existing `apps/risk` module.
- Risk integration is adapter-based:
  - `_SimulationRiskAdapter` exposes MT5-like methods expected by `RiskGovernor` / `PositionSizer`
  - account equity comes from simulator state
  - symbol info comes from simulator symbol state
  - historical bars come from preloaded backtest data caches passed into `configure_risk_management(...)`
- When risk management is enabled, `Engine.run(...)` changes only the new-entry path:
  - exits and pending cancellations still execute immediately per tick
  - entry and pending-entry signals at the same timestamp are collected into one batch
  - the batch then flows through:
    - `PositionSizer`
    - `RiskRegimeDetector`
    - `RiskBudgetAllocator` (optional)
    - `RiskGovernor`
    - existing order execution helpers
- This keeps `run(...)` as the single chronological execution loop while allowing portfolio-aware approval of simultaneous signals across symbols.
- Multi-timeframe strategy logic remains outside the engine:
  - each symbol strategy prepares its own final signalized bars first
  - those bars are converted to ticks
  - merged ticks are then executed by the engine with optional portfolio risk gating
- `examples/trading/trade_example.py -> example_14_portfolio_backtest_with_risk()` demonstrates this risk-enabled merged portfolio flow.

## BacktestState Deal Model (Refactor)

- `BacktestState` now uses:
  - `trading_deals` as the open-position source of truth
  - `trading_history_deals` as the closed-position/deal history store
- `trading_positions` was removed.
- Position lifecycle:
  - open position -> row is created in `trading_deals` with `entry=0`
  - close position (manual or monitored) -> row is removed from `trading_deals` and moved to `trading_history_deals` with `entry=1`
- `positions_get/positions_total` resolve from open rows in `trading_deals`.
- `history_deals_get/history_deals_total` resolve from `trading_history_deals`.

## Core Bridge Account Initialization

- `haruquant.core.AccountInfo` is backed by the existing C++ trading MT5-style type (`cpp/include/trading/account_info.hpp`).
- `AccountInfo` now has a single source of truth for state:
  - one shared `BacktestState` (`std::shared_ptr<haruquant::core::BacktestState>`)
  - no dual-mode internal/external state storage
- Python initialization supports object or dict input:
  - `account = haruquant.core.AccountInfo(mt5_account)`
  - `account = haruquant.core.AccountInfo(mt5_account_dict)`
- Parsed fields include common MT5 account keys:
  - identity/meta: `login`, `name`, `server`, `currency`, `company`
  - account settings: `trade_mode`, `leverage`, `limit_orders`, `margin_mode`, `trade_allowed`, `trade_expert`
  - financial snapshot: `balance`, `credit`, `profit`, `equity`, `margin`, `margin_free`, `margin_level`, `margin_so_call`, `margin_so_so`
- `haruquant.core.BacktestSimulator` now supports:
  - default construction: `BacktestSimulator()`
  - account-seeded construction: `BacktestSimulator(account)`
- `BacktestSimulator(account)` keeps the same logical account state by copying the `AccountInfo` wrapper that shares the same `BacktestState`.

## Core Bridge Deal Initialization

- `haruquant.core.DealInfo` is backed by `cpp/include/trading/deal_info.hpp`.
- `DealInfo` now uses one shared `BacktestState` source (`std::shared_ptr<haruquant::core::BacktestState>`).
- Python initialization supports:
  - default constructor: `deal = haruquant.core.DealInfo()`
  - object/dict constructor: `deal = haruquant.core.DealInfo(mt5_deal_or_dict)`
- MT5-style getters and `Set...` mutators are exposed in `haruquant.core` for direct tester-side overrides.
- In tester flows, initialize account-backed core simulator first:
  - `account = haruquant.core.AccountInfo(mt5_account)`
  - `simulator = haruquant.core.BacktestSimulator(account)`

## Core Bridge HistoryOrder Initialization

- `haruquant.core.HistoryOrderInfo` is backed by `cpp/include/trading/history_order_info.hpp`.
- `HistoryOrderInfo` now uses one shared `BacktestState` source (`std::shared_ptr<haruquant::core::BacktestState>`).
- Python initialization supports:
  - default constructor: `row = haruquant.core.HistoryOrderInfo()`
  - object/dict constructor: `row = haruquant.core.HistoryOrderInfo(mt5_order_or_dict)`
- MT5-style getters and `Set...` mutators are exposed in `haruquant.core`.
- For consistent reporting across live/tester paths, live MT5 rows can be populated into `haruquant.core.HistoryOrderInfo` first, then processed with the same downstream logic.

## Core Bridge Order Initialization

- `haruquant.core.OrderInfo` is backed by `cpp/include/trading/order_info.hpp`.
- `OrderInfo` uses one shared `BacktestState` source (`std::shared_ptr<haruquant::core::BacktestState>`).
- Python initialization supports:
  - default constructor: `row = haruquant.core.OrderInfo()`
  - object/dict constructor: `row = haruquant.core.OrderInfo(mt5_order_or_dict)`
- MT5-style getters and `Set...` mutators are exposed in `haruquant.core`.
- For consistent reporting across live/tester paths, live MT5 rows can be populated into `haruquant.core.OrderInfo` first, then processed with the same reporting flow.

## Core Bridge Position Initialization

- `haruquant.core.PositionInfo` is backed by `cpp/include/trading/position_info.hpp`.
- `PositionInfo` uses one shared `BacktestState` source (`std::shared_ptr<haruquant::core::BacktestState>`).
- Python initialization supports:
  - default constructor: `row = haruquant.core.PositionInfo()`
  - object/dict constructor: `row = haruquant.core.PositionInfo(mt5_position_or_dict)`
- MT5-style getters and `Set...` mutators are exposed in `haruquant.core`.
- For consistent reporting across live/tester paths, live MT5 rows can be populated into `haruquant.core.PositionInfo` first, then processed with the same reporting flow.

## Core Bridge Symbol Initialization

- `haruquant.core.SymbolInfo` is backed by `cpp/include/trading/symbol_info.hpp`.
- `SymbolInfo` uses one shared `BacktestState` source (`std::shared_ptr<haruquant::core::BacktestState>`).
- Python initialization supports:
  - default constructor: `row = haruquant.core.SymbolInfo()`
  - object/dict constructor: `row = haruquant.core.SymbolInfo(mt5_symbol_or_dict)`
- MT5-style getters and `Set...` mutators are exposed in `haruquant.core`.
- For consistent reporting across live/tester paths, live MT5 rows can be populated into `haruquant.core.SymbolInfo` first, then processed with the same reporting flow.
- Access pattern remains account-centric for MT5 compatibility:
  - Use `account.Login()` (not `simulator.Login()`).
  - Simulator keeps the seeded account via `simulator.account_info()`.

## Core Bridge Trade Initialization

- `haruquant.core.Trade` is backed by `cpp/include/trading/trade.hpp`.
- `Trade` now uses one shared `BacktestState` source (`std::shared_ptr<haruquant::core::BacktestState>`), aligned with `AccountInfo`.
- Python initialization supports:
  - default constructor: `trade = haruquant.core.Trade()`
  - account-seeded constructor: `trade = haruquant.core.Trade(account)`
- `Trade(account)` shares the same state as `AccountInfo`, so account/trade data stays consistent in one source of truth.
- Exposed core methods cover request configuration, execution calls, and result accessors:
  - `RequestMagic`, `RequestDeviation`, `RequestTypeFilling`, `RequestSymbol`
  - `PositionOpen`, `Buy`, `Sell`, `PositionModify`
  - `ResultDeal`, `ResultOrder`, `ResultRetcode`, `ResultRetcodeDescription`, `ResultComment`

## Core Bridge Terminal Initialization

- `haruquant.core.TerminalInfo` is backed by `cpp/include/trading/terminal_info.hpp`.
- `TerminalInfo` uses one shared `BacktestState` source (`std::shared_ptr<haruquant::core::BacktestState>`).
- Python initialization supports:
  - default constructor: `row = haruquant.core.TerminalInfo()`
  - object/dict constructor: `row = haruquant.core.TerminalInfo(mt5_terminal_or_dict)`
- MT5-style getters and `Set...` mutators are exposed in `haruquant.core`.
- For consistent reporting across live/tester paths, MT5 terminal rows can be populated into `haruquant.core.TerminalInfo` and then optionally overridden in tester mode via setters.

## Engine Data Model Consistency

- The C++ simulation engine now uses MT5-style classes as the single source of truth:
  - `hqt::AccountInfo`
  - `hqt::SymbolInfo`
- Legacy DTOs `AccountInfoData` and `SymbolInfoData` were removed from:
  - `cpp/include/engine/engine.hpp`
  - `cpp/src/engine/*`
  - `bridge/src/sim_bindings.cpp`
- Python bridge surfaces account/symbol objects directly as `haruquant.sim.AccountInfo` and `haruquant.sim.SymbolInfo`.

## Trade Container Boundary

- Public Python/C++ bridge usage should use MT5-style trade containers directly:
  - `haruquant.sim.PositionInfo`
  - `haruquant.sim.OrderInfo`
  - `haruquant.sim.HistoryOrderInfo`
  - `haruquant.sim.DealInfo`
 - MT5-style query naming is now the compatibility contract for simulator/live interchange:
  - `positions_get(symbol=None, group=None, ticket=None)`
  - `positions_total()`
  - `orders_get(symbol=None, group=None, ticket=None)`
  - `orders_total()`
  - `history_orders_get(ticket=None)`
  - `history_orders_total()`
  - `history_deals_get(ticket=None)`
  - `history_deals_total()`
  - `symbol_select(symbol, enable=True)`
  - `symbols_get(group=None)`
  - `symbols_total()`
 - Query behavior is implemented in trading layer (`hqt::CTrade` in `cpp/include/trading/trade.hpp` and `cpp/src/trading/trade.cpp`) and consumed by engine layer (`TradeSimulator`) to keep engine focused on orchestration.
- `TradeRecordData` has been removed from C++ engine internals.
- New usage examples and bindings should prefer direct MT5-style classes to avoid adapter/mapping layers.

## Trade Execution Boundary

- C++ simulator execution path:
  - `haruquant.sim.CTrade` (for simulation/backtest)
- Live MT5 execution path:
  - `apps.mt5.Trade` (Python MT5 transport)
- Usage split:
  - `tests/usage/trade/trade_cpp_example.py` -> C++ simulator execution
  - `tests/usage/trade/trade_example.py` -> live MT5 execution
- Cleanup status:
  - `apps/trade/{account_info,symbol_info,position_info,order_info,history_order_info,deal_info,terminal_info}.py`
    are now explicitly marked legacy wrappers and should not be used for new simulation/backtest code.

## C++ Logging Backend

- C++ logging API remains `hqt::util` (`cpp/include/util/logger.hpp`) to keep bridge and Python integrations stable.
- Backend implementation uses `spdlog` async logger in `cpp/src/engine/logger.cpp`.
- Logging path:
  - Structured `LogRecord` is built in-process for callback forwarding (`set_log_sink`).
  - Stderr emission is handled asynchronously via `spdlog::async_logger` to avoid blocking hot paths.
- Runtime controls:
  - `set_log_level(...)` updates filtering level.
  - `set_component_log_level(component, level)` overrides filtering for one component.
  - `clear_component_log_level(component)` removes one component override.
  - `clear_all_component_log_levels()` resets all component overrides.
  - `set_stderr_logging(...)` toggles async stderr output.
  - `set_log_sink(...)` controls structured callback forwarding.

## Python Logging Adapter

- Default Python logger export is `apps.utils.logger.logger` (Structlog adapter).
- Existing import pattern `from apps.utils.logger import logger` remains unchanged.
- Default file sinks are configured at import time under `logs/`:
  - `logs/app.log` (INFO and above)
  - `logs/debug.log` (DEBUG and above)
  - `logs/errors.log` (ERROR and above)
  - `logs/access.log` (records tagged as access/http style events)
- Rotation policy for default Python file sinks:
  - rotate at UTC midnight or at 50 MB, whichever comes first
  - retain 30 rotated files per log stream
- Compatibility support is preserved for commonly used APIs:
  - level methods (`debug/info/success/warning/error/critical/exception`)
  - `bind(...)`
  - `add(...)` / `remove(...)` sink management for runtime callbacks (including raw callback mode)
- Sensitive fields and free-form text are redacted before dispatch using `apps/utils/redaction.py`.
- If `structlog` is unavailable in the environment, adapter falls back to stdlib logging while preserving the same call interface.

## Log Schema IDs

- Normalized identifier fields included in log schema:
  - `correlation_id`
  - `run_id`
  - `trace_id`

- Behavior:
  - Python adapter (`apps.utils.logger`) injects these keys into every record `extra` payload.
  - C++ logger (`hqt::util::LogRecord`) includes these fields explicitly and mirrors them in bridge callback payloads.
  - If not provided by caller context, values default to empty strings to keep schema stable.

## Severity Contract (Normalized)

- Canonical severity levels across C++ and Python:
  - `DEBUG` (10)
  - `INFO` (20)
  - `WARNING` (30)
  - `ERROR` (40)
  - `CRITICAL` (50)

- Accepted aliases (normalized to canonical):
  - `warn` -> `WARNING`
  - `fatal` -> `CRITICAL`

- C++ bridge input (`haruquant.set_log_level`, `haruquant.emit_log`) accepts:
  - `debug`, `info`, `warning|warn`, `error`, `critical|fatal`

- Python adapter (`apps.utils.logger`) accepts:
  - canonical names above plus aliases `WARN`, `FATAL`

## Runtime Filtering (FR-UTIL-006)

- Runtime filtering is supported in both C++ and Python by:
  - global minimum severity threshold
  - per-component severity overrides
- Component resolution order:
  - `extra["component"]` if present
  - logger/module name fallback
- Bridge controls exposed via `haruquant`:
  - `set_log_level(level)`
  - `set_component_log_level(component, level)`
  - `clear_component_log_level(component)`
  - `clear_all_component_log_levels()`
- Python adapter controls (`apps.utils.logger.StructlogAdapter`):
  - `set_min_level(level)` / `get_min_level()`
  - `set_component_level(component, level)`
  - `clear_component_level(component)`
  - `clear_all_component_levels()`

## Sensitive Data Redaction (FR-UTIL-008)

- Redaction is automatic in both logger stacks:
  - Python: `apps/utils/redaction.py` + `apps/utils/logger.py`
  - C++: `cpp/src/engine/logger.cpp`
- Redaction behavior:
  - sensitive key/value fields in structured metadata are replaced with `***REDACTED***`
  - free-form message patterns such as `password=...`, `token=...`, `api_key=...`, and `Bearer ...` are redacted
- Redaction happens before sink/callback dispatch and before stderr output to prevent accidental secret leakage in downstream handlers.

## Password Hashing

- User password hashing and verification live in `apps/utils/security.py`.
- The auth flow uses Passlib with bcrypt-backed hashes for:
  - user creation and password updates
  - login verification in `apps/api/auth_utils.py`
- Runtime compatibility note:
  - this project pins `bcrypt==4.0.1` in `requirements.txt`
  - newer `bcrypt` 5.x changes long-password handling and can break verification for existing accounts created under older behavior

## Dashboard Equity Curve

- Dashboard equity data is served by `GET /api/dashboard/equity-curve`.
- The endpoint reuses the authenticated MT5 connection flow from `apps/api/routes/dashboard/broker.py`.
- Equity points are derived from historical deals ordered by timestamp using:
  - `profit`
  - `commission`
  - `swap`
- The UI groups returned points by history span:
  - `< 1 day`: hours
  - `1-31 days`: days
  - `32 days-< 6 months`: weeks
  - `6-12 months`: months
  - `> 12 months`: years

## Dashboard Summary Cards

- Dashboard summary card data is served by `GET /api/dashboard/summary`.
- The endpoint combines:
  - MT5 deal history for:
    - 7-day daily PnL
    - win rate across closed deals with non-zero net result
  - live session configuration data for:
    - active strategy count
    - active strategy rows shown on the dashboard
- Active strategy rows are sourced from configured strategies in live sessions with status `running` or `paused`.
- The dashboard intentionally does not invent per-strategy PnL because the current live-session API does not expose reliable strategy-level account attribution.

## Schema Validators (FR-UTIL-003)

- Schema contract validation is C++-owned and exposed through the bridge.
- C++ schema primitives are implemented in:
  - `cpp/include/util/schema_validator.hpp`
  - `cpp/src/engine/schema_validator.cpp`
- C++/bridge schema entry points exposed via `haruquant`:
  - `validate_market_schema(payload)`
  - `validate_trade_schema(payload)`
  - `validate_config_schema(payload)`
- Bridge payload handling supports nested config dictionaries by flattening keys into schema paths (e.g., `logging.level`, `risk.max_positions`).

## Trade Validation Consolidation

- Trade execution pre-checks for simulator/backtest now have a single shared C++ implementation:
  - `cpp/include/util/validators.hpp`
  - `cpp/src/util/validators.cpp`
- Python validator module `apps/utils/validate.py` has been removed.
- The simulator execution path validates in `TradeGateway::order_send(...)` before forwarding into `CTrade` execution.
- Validation scope consolidated in C++:
  - action/type compatibility
  - symbol/quote availability
  - volume constraints
  - margin sufficiency checks
- Bridge-facing validator calls are centralized through dispatcher routing in `haruquant.TradeValidator`:
  - `validate(type, value, **kwargs)` resolves handlers via `_get_validation_dispatcher()` and invokes the corresponding C++ validator.
- `CTrade::CheckRequest(...)` now delegates to the same shared validator implementation to keep validation rules consistent for direct `CTrade` callers.

## C++ Coverage Gates

- C++ coverage instrumentation can be enabled with `-DHQT_ENABLE_COVERAGE=ON` (GCC/Clang).
- File-level coverage thresholds are configured in `cpp/coverage_thresholds.json`.
- Current enforced gate:
  - `cpp/src/util/validators.cpp` must remain at or above `80%` line coverage.
- Local coverage gate entry point:
  - `scripts/check_cpp_coverage.py`
  - Linux/macOS convenience path: `scripts/build_cpp.sh --coverage`
  - Windows convenience path: `python scripts/build_cpp.py --coverage`
- Note:
  - MSVC toolchain does not emit gcov artifacts. Coverage mode on Windows uses Clang/Ninja.
- CI coverage gate workflow:
  - `.github/workflows/cpp_coverage.yml`

## Date/Time Normalization (FR-UTIL-004)

- Centralized helpers are implemented in `apps/utils/datetime_utils.py`.
- Core entry points:
  - `parse_datetime(value, assume_tz="UTC")`
  - `to_utc(dt, assume_tz="UTC")`
  - `to_naive_utc(dt, assume_tz="UTC")`
  - `normalize_timestamp(value, output=...)`
  - `normalize_timezone_for_series(series_or_index, target_tz=..., make_naive=...)`
- Input support includes `datetime`, ISO-8601 strings (including `Z`), and unix epoch seconds/milliseconds.
- Default normalization policy is UTC with explicit `assume_tz` behavior for naive datetimes.

## Path Handling (NFR-PERF-001 Constraint)

- Platform-independent path helpers are centralized in `apps/utils/path_utils.py`.
- Core helpers:
  - `normalize_path(path, base=None)`
  - `ensure_parent_dir(path)`
  - `ensure_dir(path)`
- Utility modules use `pathlib.Path` semantics for file/dir operations to avoid OS-specific path branching.

## Configuration Layering (IP-04)

- Config loader entry point: `apps/live/config.py::load_config_mapping(...)`
- Supported file formats:
  - TOML (primary)
  - JSON (supported for compatibility)
- Effective precedence:
  - base file config
  - profile overlay (`profiles.<dev|backtest|paper|live>`)
  - env overlay (`HQT_...` keys with `__` nesting)
  - runtime overrides (dotted keys)
- Versioning:
  - `schema_version` is validated against supported versions before startup parsing.
- Runtime reload:
  - `Config.reload_non_critical()` updates non-critical knobs (logging level and safety/risk limits) without full restart.
- Self-documenting schema metadata:
  - Exposed by `get_schema_spec()` with `description`, `safeguards`, and `units`.

## Event/Time Engine (IP-06)

- Clock service:
  - `cpp/include/engine/clock_service.hpp`
  - Supports explicit event-time vs processing-time canonical mode selection.
  - Exposes timezone normalization policies:
    - `UTC_ONLY`
    - `APPLY_OFFSET`
    - `REJECT_NON_UTC`
  - Exposes explicit DST handling policy:
    - `NO_DST`
    - `APPLY_ONE_HOUR`
    - `REJECT`
- Event sequencing:
  - `cpp/include/engine/event_sequencer.hpp`
  - Deterministic merged ordering and per-symbol ordering.
  - Stable tie-breaker chain:
    1. `timestamp_us`
    2. `symbol_id`
    3. `stream_id`
    4. insertion sequence
- Validation:
  - `cpp/tests/test_clock_service.cpp`
  - `cpp/tests/test_event_sequencer.cpp`

## Session Calendar (IP-07)

- Core class:
  - `cpp/include/engine/session_calendar.hpp`
- Capabilities:
  - weekday session windows (`start_minute`/`end_minute`)
  - holiday exclusion by session id
  - timezone offset and DST policy-aware gate checks
  - deterministic next-open timestamp lookup
- Symbol metadata mapping:
  - reuses `cpp/include/trading/symbol_info.hpp` (`SymbolInfo`) instead of duplicating symbol metadata structs
  - calendar maps `symbol_id -> SymbolInfo + session_id`
- Runtime exposure:
  - `can_trade_symbol(symbol_id, ts, is_dst)` returns allow/deny + reason
  - `is_market_open(...)` and `next_open_time(...)` support strategy and live-controller gating flows
- Validation:
  - `cpp/tests/test_session_calendar.cpp`

## Replay Clock (IP-08)

- Core class:
  - `cpp/include/engine/replay_clock.hpp`
- Capabilities:
  - deterministic timeline playback cursor over event/bar timestamps
  - replay controls: `pause()`, `resume()`, `advance()`, `step_by_bar(n)`
  - deterministic replay signature (`timeline_signature`) and reproducible cursor snapshot (`state()`)
- Replay hooks:
  - Python reproducibility helpers in `apps/simulation/replay_hooks.py`
  - deterministic fingerprint comparison for baseline vs candidate replay runs
- Validation:
  - `cpp/tests/test_replay_clock.cpp`
  - `tests/replay/test_replay_clock_consistency.py`

## Replay Certification + WFO/WFM (IP-40)

- Core C++ APIs:
  - `cpp/include/engine/engine.hpp::ReplayCertifier`
  - `cpp/include/engine/engine.hpp::WfoWfmOrchestrator`
  - `cpp/include/engine/engine.hpp::EdgeDetector`
- Scope:
  - deterministic replay run fingerprint comparison for certification
  - walk-forward window generation and orchestration
  - walk-forward matrix orchestration across train/test specs
  - edge summary report (mean test score + p-value + verdict)
- Bridge exposure (`haruquant.sim`):
  - `ReplayTradeEvent`, `ReplayCertifier`
  - `WfoSpec`, `WfoWindow`, `WfoWindowResult`, `WfoSummary`, `WfmCellResult`
  - `WfoWfmOrchestrator`, `EdgeDetector`
- Validation:
  - `cpp/tests/test_replay_certification.cpp`
  - `cpp/tests/test_wfo_wfm.cpp`
  - `docs/haruquant/usage/research/wfo_wfm.md`

## Experiment Manager and Registry (IP-41)

- Core C++ APIs:
  - `cpp/include/engine/engine.hpp::ExperimentRegistry`
  - `cpp/include/engine/engine.hpp::SymbolClassifier`
  - `cpp/include/engine/engine.hpp::SeasonalPatternAnalyzer`
- Scope:
  - searchable experiment registry by strategy/symbol/period
  - symbol classification by asset class and volatility regime
  - seasonal pattern analysis by day-of-week and holiday/non-holiday buckets
- Bridge exposure (`haruquant.sim`):
  - `ExperimentRecord`, `ExperimentRegistry`
  - `SymbolClassification`, `SymbolClassifier`
  - `SeasonalBucket`, `SeasonalAnalysis`, `SeasonalPatternAnalyzer`
- Validation:
  - `cpp/tests/test_experiment_registry.cpp`
  - `docs/haruquant/usage/research/experiment_registry.md`

## Optimization Runners (IP-42)

- Core C++ APIs:
  - `cpp/include/engine/engine.hpp::GridSearchRunner`
  - `cpp/include/engine/engine.hpp::RandomSearchRunner`
  - `cpp/include/engine/engine.hpp::GeneticSearchRunner`
  - `cpp/include/engine/engine.hpp::BayesianSearchRunner`
  - `cpp/include/engine/engine.hpp::DistributedOptimizationRunner`
- Trial contract:
  - `cpp/include/engine/engine.hpp::OptimizationTrial`
  - fields: `params`, `score`, `iteration`, `generation`
  - worker policy/health:
    - `OptimizationWorkerPolicy`
    - `OptimizationWorkerHealth`
    - `DistributedOptimizationResult`
- Bridge exposure (`haruquant.sim`):
  - `GridSearchRunner`
  - `RandomSearchRunner`
  - `GeneticSearchRunner`
  - `BayesianSearchRunner`
  - `OptimizationTrial`
  - `DistributedOptimizationRunner`
  - `OptimizationWorkerPolicy`
  - `OptimizationWorkerHealth`
  - `DistributedOptimizationResult`
- Design:
  - optimization orchestration runs in C++
  - Python objective callbacks are invoked through nanobind for scoring
  - distributed worker execution, health monitoring, timeout retry, and restart policy are implemented in C++
- Validation:
  - `cpp/tests/test_optimization_runners.cpp`
  - `cpp/tests/test_distributed_optimization_runner.cpp`
  - `docs/haruquant/usage/research/optimization_runner.md`
  - `tests/usage/research/usage_optimization_runners.py`
  - `tests/usage/research/usage_distributed_optimization_runner.py`

## Monte Carlo and Sensitivity (IP-43)

- Core C++ APIs:
  - `cpp/include/engine/engine.hpp::MonteCarloAnalyzer`
  - `cpp/include/engine/engine.hpp::SensitivityAnalyzer`
  - `cpp/include/engine/engine.hpp::MonteCarloSummary`
  - `cpp/include/engine/engine.hpp::SensitivityReport`
- Scope:
  - Monte Carlo perturbation workflows over PnL series
  - sensitivity report over parameter-space perturbations
  - stability score and normalized sensitivity map for reproducibility metadata
- Bridge exposure (`haruquant.sim`):
  - `MonteCarloMode`, `MonteCarloAnalyzer`, `MonteCarloSummary`
  - `SensitivityAnalyzer`, `SensitivityPoint`, `SensitivityReport`
- Validation:
  - `cpp/tests/test_monte_carlo_sensitivity.cpp`
  - `docs/haruquant/usage/research/monte_carlo_sensitivity.md`
  - `tests/usage/research/usage_monte_carlo_sensitivity.py`

## Data Adapters and Normalization Pipeline (IP-09)

- Python adapters:
  - `apps/adapters/mt5_zmq_adapter.py`
  - `apps/adapters/dukascopy_adapter.py`
- Normalization layer:
  - `apps/adapters/normalization.py`
- Pipeline wrapper:
  - `apps/adapters/pipeline.py`
- Scope:
  - Subscribe to MQL5 EA `PUB` stream via `SUB` socket.
  - Decode one-frame or two-frame (`topic`, `json`) messages.
  - Fetch Dukascopy historical bars via adapter abstraction.
  - Normalize provider payloads into canonical `tick` and `bar` schemas.
  - Support ingestion progress callbacks `(done, total, percent)`.
- Topic convention:
  - `tick.<symbol>`
  - `bar.<symbol>.<timeframe>`
  - `heartbeat`
  - `status`
- Canonical contracts:
  - `CanonicalTick` fields include: `provider`, `schema_version`, `symbol`, `timestamp`, `bid`, `ask`, `volume`.
  - `CanonicalBar` fields include: `provider`, `schema_version`, `symbol`, `timeframe`, `timestamp`, `open`, `high`, `low`, `close`, `volume`.
- Validation evidence:
  - contract tests: `tests/contracts/test_tick_bar_contract.py`
  - integration tests: `tests/integration/test_data_adapter_normalization.py` (includes real local ZMQ PUB/SUB when `pyzmq` is installed)

## Data Quality Guardrails (IP-10)

- Core module:
  - `apps/utils/data_validator.py`
- Covered checks:
  - price sanity (`High >= Low`, `Open/Close in [Low, High]`, negative/zero prices)
  - missing intervals (`gaps`, `missing_timestamps`)
  - ordering/duplication (`monotonic_timestamps`, `duplicates`)
  - spike/outlier detection (`zscore|iqr|mad`)
  - zero-volume bars
  - spread anomaly checks (`negative_spread`, `wide_spread`)
- Remediation reporting:
  - each issue is annotated with:
    - `severity`
    - `remediation_action`
    - `remediation_required`
  - summary includes:
    - `summary.remediation.severity_counts`
    - `summary.remediation.actions`
    - `summary.remediation.needs_immediate_action`
- Evidence:
  - `tests/integration/test_data_quality_alerts.py`
  - `artifacts/evidence/data_quality/sample_report.json`
  - `docs/haruquant/usage/ops/data_quality_runbook.md`

## Multi-Symbol Ingestion (IP-11)

- Core module:
  - `apps/adapters/multisymbol_ingestion.py`
- Capabilities:
  - synchronized multi-symbol timeline ingestion (`synchronize`)
  - incremental download compaction (`compact_incremental`)
  - memory-mapped lazy historical reads (`MemmapHistoricalStore.read_memmap`)
- Synchronization implementation reuses:
  - `apps/simulation/synchronizer.py` (`DataSynchronizer`)
- Evidence:
  - `tests/integration/test_multisymbol_sync.py`
  - `docs/haruquant/usage/ops/multisymbol_ingestion.md`
  - `artifacts/benchmarks/ingestion/multisymbol_sync_perf.md`

## Message Contracts and Schema Registry (IP-12)

- Core module:
  - `apps/contracts/schema_registry.py`
- Provides:
  - versioned in-memory schema registry with lookup and payload validation
  - backward-compatibility guard for schema evolution
- Canonical contracts:
  - events: `TickMessage`, `BarMessage`
  - API: `OrderMessage`, `FillMessage`
  - storage: `PositionMessage`, `RunManifestSchema`, `RunReportSchema`
- Default registry entries:
  - `event.tick:1.0`, `event.bar:1.0`
  - `api.order:1.0`, `api.fill:1.0`
  - `storage.position:1.0`
  - `storage.run_manifest:1.0`, `storage.run_report:1.0`
- Compatibility policy (conservative):
  - old fields cannot be removed
  - optional old fields cannot become required
  - field type changes are rejected
- Evidence:
  - `tests/contracts/test_schema_registry.py`
  - `tests/migrations/test_schema_backward_compat.py`
  - `docs/haruquant/usage/ops/schema_registry.md`

## Feature Pipeline (IP-13)

- Core module:
  - `apps/features/pipeline.py`
- Capabilities:
  - versioned feature pipeline metadata (`pipeline_version`)
  - batch feature computation (`compute_batch`)
  - incremental streaming feature updates (`compute_incremental`)
  - inspectable feature dependency graph (`inspect_graph`)
- Uses existing indicator library:
  - trend: `sma`, `ema`, `wma`
  - momentum: `rsi`
  - volatility: `atr`, `bbands`
  - volume: `accumulation_distribution` (`adl`)
- Evidence:
  - `tests/integration/test_feature_pipeline_stream_batch.py`
  - `tests/usage/utils/usage_feature_pipeline.py`
  - `docs/haruquant/usage/research/feature_pipeline.md`
  - `benchmarks/feature/feature_compute_perf.md`

## Leakage Prevention and Split Enforcement (IP-14)

- Core module:
  - `apps/features/leakage.py`
- Capabilities:
  - point-in-time/no-lookahead validation for computed features
  - chronological train/validation/test split enforcement with optional purge gap
  - sensitive-field masking helper for research artifacts
- Integration:
  - `apps/edge/reporting.py::save_json` now masks artifact payloads before writing JSON reports
- Evidence:
  - `tests/contracts/test_no_lookahead.py`
  - `tests/integration/test_split_enforcement.py`
  - `tests/usage/utils/usage_leakage_prevention.py`
  - `docs/haruquant/usage/research/leakage_prevention.md`

## Nanobind Module Skeleton and Lifecycle (IP-18)

- Core bridge module:
  - `bridge/src/module.cpp`
- Added skeleton submodules:
  - `_event`, `_data`, `_risk`, `_oms`, `_execution`, `_backtest`, `_metrics`
- Added lifecycle hooks:
  - `initialize()`
  - `teardown()`
  - `health_check()`
- Leak-safety verification:
  - ASan CI workflow: `.github/workflows/asan_leak_check.yml`
  - lifecycle stress script: `tests/contracts/asan_bridge_lifecycle_check.py`
- Evidence:
  - `tests/contracts/test_nanobind_module_load.py`
  - `docs/haruquant/usage/dev/nanobind_module_layout.md`

## C++ Risk Engine Parity Slice (IP-27 in progress)

- Core module:
  - `cpp/include/risk/risk_engine.hpp`
  - `cpp/src/engine/risk_engine.cpp`
- Bridge bindings:
  - `bridge/src/risk_bindings.cpp` (`haruquant._risk`)
- Added C++ risk components:
  - `RiskGovernor` with `can_trade(...)` and `can_trade_with_mode(...)` gates for size, margin, drawdown, gross exposure, and net exposure
  - `RiskBudgetAllocator` with budget normalization, optional correlation penalty, lot deltas, and exposure-constraint application
  - mode-specific rules via `RiskMode` (`LIVE`, `BACKTEST`) with policy-code outputs (`OK`, `SIZE_INVALID`, `INSUFFICIENT_MARGIN`, `MAX_*`)
- Evidence:
  - `cpp/tests/test_risk_engine.cpp`
  - `tests/contracts/test_risk_bindings.py`
  - `tests/usage/risk/09_cpp_risk_policy.py`
  - `docs/haruquant/usage/risk/pretrade_risk.md`

## In-trade Monitoring and Circuit Breakers (IP-28)

- Core module:
  - `cpp/include/risk/risk_engine.hpp`
  - `cpp/src/engine/risk_engine.cpp`
- Added C++ components:
  - `IntradayRiskMonitor` for drawdown and volatility-spike monitoring
  - optional HMM-proxy hook via `evaluate_with_hmm(..., hmm_stress_probability)`
  - `CircuitBreaker` supporting strategy-level and global halt gates
- Bridge bindings:
  - `bridge/src/risk_bindings.cpp` (`haruquant._risk`)
- Evidence:
  - `cpp/tests/test_risk_engine.cpp`
  - `tests/contracts/test_risk_bindings.py`
  - `tests/usage/risk/10_intraday_circuit_breaker.py`
  - `docs/haruquant/usage/risk/intrade_controls.md`

## Kill-Switch and Safe-Mode State Machine (IP-29)

- Core module:
  - `cpp/include/risk/risk_engine.hpp`
  - `cpp/src/engine/risk_engine.cpp`
- Added C++ components:
  - `KillSwitchController` with safe-mode states:
    - `NORMAL`
    - `REDUCE_ONLY`
    - `HALT`
    - `EMERGENCY_SHUTDOWN`
  - strategy/global kill-switch triggers and emergency shutdown source tagging (`UI`/`API`)
- Bridge bindings:
  - `bridge/src/risk_bindings.cpp` (`haruquant._risk`)
- Evidence:
  - `cpp/tests/test_risk_engine.cpp`
  - `tests/contracts/test_risk_bindings.py`
  - `tests/usage/risk/11_killswitch_state_machine.py`
  - `docs/haruquant/usage/live/killswitch_runbook.md`

## Risk Override Audit Workflow (IP-30)

- Core module:
  - `apps/live/config.py`
- Added flow:
  - `Config.apply_risk_override(...)` for role-bound risk overrides
  - restricted risk-key allowlist
  - mandatory reason
  - live-profile authorization (superuser token)
  - immutable JSONL audit event (`event = risk_override`)
- Evidence:
  - `tests/security/test_risk_override_audit.py`
  - `docs/haruquant/usage/risk/risk_override_policy.md`

## Bridge Ownership and Lifetime Safety (IP-19)

- Ownership contract API:
  - `haruquant.ownership_contracts()`
  - explicit policies for:
    - C++ owned / Python view
    - shared ownership
    - callback ownership
    - zero-copy buffer ingestion
- Lifetime enforcement in bindings:
  - long-lived parent/child relationships are guarded with nanobind `keep_alive`
  - view-returning accessors use `reference_internal` for parent-bound lifetimes
- Zero-copy contract path:
  - `haruquant.sum_buffer_zero_copy(buffer)` consumes contiguous `float64` buffers via Python buffer protocol without copy
- Evidence:
  - `tests/contracts/test_bridge_lifetime.py`
  - `docs/haruquant/usage/dev/bridge_ownership_rules.md`
  - `artifacts/logs/bridge/lifetime_validation.log`

## Exception Mapping C++ + Python (IP-20)

- Bridge-level typed exception classes exported by `haruquant`:
  - `BridgeError`
  - `ConfigurationError`
  - `ValidationError`
  - `RiskViolationError`
  - `OrderStateError`
  - `ExecutionError`
  - `TransientConnectivityError`
  - `FatalEngineError`
- Mapping helpers:
  - `haruquant.raise_exception_for_retcode(code, detail="")`
  - `haruquant.raise_exception_for_category(category, detail="")`
- Python adapter behavior:
  - `apps/simulation/backend.py::_translate_cpp_exception(...)` preserves typed `haruquant.*Error` exceptions and uses retcode taxonomy fallback when needed.
- Crash handling:
  - `apps/utils/crash_handler.py` installs process-level handlers (`faulthandler`, uncaught exception hook, signal hooks).
  - Crash path flushes Python and C++ loggers, then appends snapshot payload to `artifacts/logs/crash/crash_state.json`.
- Evidence:
  - `tests/contracts/test_exception_mapping.py`
  - `tests/unit/apps/utils/test_errors.py`
  - `tests/unit/apps/utils/test_crash_handler.py`
  - `docs/haruquant/usage/dev/exception_mapping.md`
  - `docs/haruquant/usage/ops/crash_handling.md`

## Zero-Copy + Serialization Fallback (IP-21)

- Zero-copy paths:
  - `haruquant.sum_buffer_zero_copy(buffer)` for contiguous `float64` buffers.
  - `haruquant.sum_auto(values)` uses zero-copy when buffer-compatible, otherwise copy fallback.
- Capability API:
  - `haruquant.bridge_transfer_capabilities()`
- Python fallback helper:
  - `apps/utils/bridge_transfer.py::sum_with_fallback(values, serialization=...)`
  - supported modes:
    - `auto` (bridge-selected zero-copy/copy fallback)
    - `arrow` (explicit Arrow IPC roundtrip fallback; optional dependency)
    - `protobuf` (explicit protobuf roundtrip fallback; optional dependency)
- Performance evidence:
  - `benchmarks/bridge/zero_copy_vs_fallback.md`
- Validation evidence:
  - `tests/contracts/test_zero_copy.py`
  - `tests/integration/test_fallback_serialization.py`
  - `docs/haruquant/usage/dev/zero_copy_and_fallback.md`

## Strategy SDK Lifecycle + Event Contract (IP-22)

- Strategy base type:
  - `apps/strategy/base.py::BaseStrategy`
- Canonical lifecycle hooks:
  - required: `on_init()`, `on_bar(data)`
  - optional: `on_tick(data)`, `on_trade(event)`, `on_order_update(event)`, `on_timer(event)`, `on_shutdown(event=None)`
- Canonical strategy event shape:
  - `apps/strategy/base.py::StrategyEvent`
  - event keys: `event_id`, `event_type`, `symbol`, `strategy_id`, `event_ts`, `recv_ts`, `payload`, `run_id`, `trace_id`, `correlation_id`
- Strategy isolation:
  - each strategy instance has its own `strategy_id` and mutable `state` container (`dict`) for per-strategy runtime state.
- Evidence:
  - `tests/unit/apps/strategy/test_base.py`
  - `tests/contracts/test_strategy_event_contract.py`
  - `docs/haruquant/usage/strategy/create_strategy.md`

## Strategy Adapter and Signal Router (IP-23)

- Canonical contracts:
  - `apps/strategy/base.py::SignalIntent`
  - includes explainability metadata fields (`reason`, `features`, `confidence`, `tags`, `metadata`)
- Adapter:
  - `apps/strategy/adapter.py::StrategyAdapter`
  - normalizes strategy output from `get_signal(...)` into canonical `SignalIntent`
  - emits `StrategyEvent` payload for downstream audit/routing contexts
- Router:
  - `apps/strategy/adapter.py::SignalRouter`
  - validates canonical intent fields and forwards to provided handler
- Evidence:
  - `tests/integration/test_strategy_adapter_flow.py`
  - `docs/haruquant/usage/strategy/signal_intent_contract.md`
  - `benchmarks/strategy/adapter_latency.md`

## Strategy Reproducibility Metadata (IP-24)

- Binder helpers:
  - `apps/strategy/repro.py`
  - `compute_config_hash(config)` for deterministic config fingerprinting
  - `build_run_manifest(...)` for strategy version + artifact binding
  - `attach_stability_metadata(...)` for stability/sensitivity payloads
  - `validate_manifest_payload(...)` via `storage.run_manifest:1.0` schema
- Canonical reproducibility fields:
  - `strategy_version`, `config_hash`, `code_version`, `seed`
  - artifact bindings: `strategy_artifacts`, `model_artifacts`
  - stability section: `stability_score`, `sensitivity`, `notes`
- Evidence:
  - `tests/unit/apps/strategy/test_strategy_version_binding.py`
  - `docs/haruquant/usage/research/reproducible_strategy_runs.md`
  - `tests/usage/strategy/02_reproducible_manifest.py`
  - `artifacts/logs/repro/sample_manifest.json`

## Secrets and Privileged Config Controls (IP-05)

- Secret provider integration:
  - Live config supports `keyring://<service>/<account>` references.
  - Resolution is performed at config-load time via `apps/live/secrets.py`.
  - Missing/invalid keyring entries fail fast with `ConfigError`.
- Privileged runtime mutation:
  - `apps/live/config.py::Config.apply_privileged_mutation(...)` is the single privileged mutation path.
  - In `live` profile, mutation requires valid session token + superuser role.
  - Mutable keys are allowlisted to non-critical runtime parameters.
- Security audit logging:
  - Each privileged mutation writes a JSON-line event to `artifacts/logs/security/secret_access_audit.json`.
  - Audit payload is redacted with `apps/utils/redaction.py` before persistence.
- C++ pooling primitive:
  - `cpp/include/util/connection_pool.hpp` and `cpp/src/engine/connection_pool.cpp` provide configurable pool/overflow/timeout controls for DB-adjacent concurrency paths.

## Portfolio State Engine (IP-25)

- Core state type:
  - `cpp/include/engine/engine.hpp::PortfolioState`
  - implementation in `cpp/src/engine/analytics.cpp`
- Scope:
  - simulation/backtest side (`haruquant.sim`) canonical portfolio/account/position tracking
  - thread-safe updates for concurrent multi-strategy, multi-symbol state writes
- State model:
  - account snapshot: balance, equity, margin, margin_free, margin_level, profit
  - PnL split: `total_realized_pnl()` and `total_unrealized_pnl()`
  - aggregated position views:
    - `positions_by_symbol()`
    - `positions_by_strategy(strategy_id)`
- Update API:
  - `upsert_position(strategy_id, symbol, net_volume, margin, unrealized_pnl)`
  - `apply_realized_pnl(strategy_id, symbol, realized_pnl, commission, swap)`
  - `clear_position(strategy_id, symbol)`
- Bridge exposure:
  - `bridge/src/sim_bindings.cpp` (`sim.PortfolioState`, `sim.PositionAggregate`)
- Evidence:
  - `cpp/tests/test_portfolio_state.cpp`
  - `tests/integration/test_portfolio_updates.py`
  - `docs/haruquant/usage/portfolio/portfolio_state.md`
  - `benchmarks/portfolio/state_update_perf.md`

## Allocation/Rebalance/Exposure Models (IP-26)

- C++ primitives:
  - `cpp/include/engine/engine.hpp::PortfolioAllocator`
  - `cpp/include/engine/engine.hpp::RebalanceController`
  - `cpp/include/engine/engine.hpp::ExposureConstraints`
  - implementation in `cpp/src/engine/analytics.cpp`
- Allocation models:
  - static equal-weight
  - risk parity (inverse volatility weighting)
  - custom weights (optional normalization)
- Exposure constraints:
  - total portfolio exposure cap
  - per-symbol exposure cap
  - per-strategy exposure caps
  - per-asset exposure caps
- Rebalance policies:
  - scheduled interval-based trigger
  - event trigger based on allocation drift threshold
- Bridge exposure:
  - `haruquant.sim.PortfolioAllocator`
  - `haruquant.sim.RebalancePolicy`
  - `haruquant.sim.RebalanceController`
  - `haruquant.sim.ExposureConstraints`
- Design direction:
  - C++ remains the execution path for simulation/backtest loops.
  - Python usage is orchestration-only and invokes C++ APIs at control boundaries.
- Evidence:
  - `cpp/tests/test_allocation_models.cpp`
  - `cpp/tests/test_rebalance_policies.cpp`
  - `tests/unit/test_allocation_models.py`
  - `tests/integration/test_rebalance_policies.py`
  - `docs/haruquant/usage/portfolio/allocation_and_rebalance.md`
  - `benchmarks/portfolio/rebalance_cost.md`

## OMS Order State Machine and Idempotency (IP-31)

- Core APIs:
  - `cpp/include/engine/engine.hpp::TradeRequest`
  - `cpp/include/engine/engine.hpp::TradeSimulator`
  - implementation in `cpp/src/engine/trading.cpp`
- Order lifecycle model:
  - explicit logical states in `OmsOrderState`:
    - `NEW`
    - `ACCEPTED`
    - `PARTIALLY_FILLED`
    - `FILLED`
    - `CANCELED`
    - `EXPIRED`
    - `REJECTED`
  - order state query:
    - `TradeSimulator::order_state(...)`
    - `TradeSimulator::order_state_name(...)`
- Idempotent submission:
  - `TradeRequest.client_order_id` enables duplicate-guarded submit flow.
  - Same `client_order_id` + same payload returns cached original result.
  - Same `client_order_id` + different payload is rejected.
- Bridge exposure:
  - `bridge/src/sim_bindings.cpp`:
    - `sim.TradeRequest.client_order_id`
    - `sim.OmsOrderState`
    - `sim.TradeSimulator.order_state(...)`
    - `sim.TradeSimulator.order_state_name(...)`
- Evidence:
  - `cpp/tests/test_sim_oms_state_machine.cpp`
  - `docs/haruquant/usage/trade/oms_state_machine_idempotency.md`
  - `tests/usage/trade/oms_state_machine_idempotency_cpp.py`

## Position Book and Reconciliation Hooks (IP-32)

- Core C++ types:
  - `cpp/include/engine/engine.hpp::PositionBook`
  - `cpp/include/engine/engine.hpp::PositionMode`
  - `cpp/include/engine/engine.hpp::FillEvent`
  - `cpp/include/engine/engine.hpp::ReconciliationReport`
- Implementation:
  - `cpp/src/engine/analytics.cpp`
- Capabilities:
  - position updates from fills (`apply_fill`)
  - account snapshot updates (`apply_account_snapshot`)
  - netting mode (single net position per symbol)
  - hedging mode (multi-leg tracking per symbol)
  - reconciliation hooks:
    - `periodic_reconcile(...)`
    - `reconnect_reconcile(...)`
    - `reconcile_with_broker(...)`
- Bridge exposure (`haruquant.sim`):
  - `PositionBook`
  - `PositionMode`
  - `FillEvent`
  - `PositionLeg`
  - `ReconciliationReport`
- Evidence:
  - `cpp/tests/test_position_book.cpp`
  - `tests/integration/test_reconcile_hooks.py`
  - `docs/haruquant/usage/live/position_book_and_reconcile.md`

## Reconciliation Escalation Workflow (IP-33)

- Adds policy-aware escalation over IP-32 reconciliation reports.
- Core additions:
  - `ReconcilePolicy` (`Auto`, `Manual`)
  - `EscalationDecision`
  - extended `ReconciliationReport` with severity + blocking fields
- Behavior:
  - `Auto` policy:
    - clean: continue
    - minor mismatch: alert
    - major mismatch: block new orders + require manual resolution
  - `Manual` policy:
    - any mismatch requires manual resolution and blocks new orders
- Incident artifacts:
  - `PositionBook::write_incident_report(...)` writes JSON discrepancy reports
  - default operational evidence path:
    - `artifacts/logs/live/reconcile_discrepancy_report.json`
- Bridge exposure (`haruquant.sim`):
  - `ReconcilePolicy`
  - `EscalationDecision`
  - `PositionBook.evaluate_reconciliation(...)`
  - `PositionBook.write_incident_report(...)`
- Evidence:
  - `cpp/tests/test_reconcile_escalation.cpp`
  - `tests/e2e/test_reconcile_mismatch_blocking.py`
  - `docs/haruquant/usage/live/reconcile_escalation.md`

## Broker Adapter Abstraction + Mock Broker (IP-34)

- Core C++ types:
  - `cpp/include/engine/engine.hpp::BrokerAdapter`
  - `cpp/include/engine/engine.hpp::MockBroker`
  - `cpp/include/engine/engine.hpp::PaperTradingEngine`
  - `cpp/include/engine/engine.hpp::BrokerSnapshot`
- Implementation:
  - `cpp/src/engine/trading.cpp`
- Responsibilities:
  - `BrokerAdapter` defines a standardized broker contract:
    - `connect()`
    - `submit(...)`
    - `cancel(...)`
    - `fetch_state()`
  - `MockBroker` wraps `TradeSimulator` to provide deterministic execution behavior.
  - `PaperTradingEngine` routes execution flow through an injected broker adapter.
- Determinism controls:
  - `MockBroker.set_partial_fill_ratio(...)`
  - `MockBroker.set_deterministic_price(...)`
  - `MockBroker.clear_deterministic_price()`
- Bridge exposure (`haruquant.sim`):
  - `MockBroker`
  - `BrokerSnapshot`
  - `PaperTradingEngine`
- Evidence:
  - `cpp/tests/test_broker_adapter_interface.cpp`
  - `tests/integration/test_mock_broker.py`
  - `docs/haruquant/usage/live/broker_adapter.md`

## Execution Router + Retry + Bounded Failure Policies (IP-35)

- Core C++ types:
  - `cpp/include/engine/engine.hpp::ExecutionPolicy`
  - `cpp/include/engine/engine.hpp::ExecutionRouteResult`
  - `cpp/include/engine/engine.hpp::ExecutionRouter`
- Implementation:
  - `cpp/src/engine/trading.cpp`
- Responsibilities:
  - routes order submission through broker adapter
  - applies final pre-send risk checks via existing C++ `RiskGovernor`
  - retries only retryable retcodes with bounded attempts
  - enforces order spam prevention by windowed rate limiting
  - marks escalation when consecutive execution failures breach configured threshold
- Bridge exposure (`haruquant.sim`):
  - `ExecutionPolicy`
  - `ExecutionRouteResult`
  - `ExecutionRouter`
- Evidence:
  - `cpp/tests/test_execution_retry.cpp`
  - `tests/integration/test_execution_escalation.py`
  - `docs/haruquant/usage/live/execution_retry_policy.md`

## Execution Algos + Quality Metrics (IP-36)

- Core C++ types:
  - `cpp/include/engine/engine.hpp::ExecutionAlgoTWAP`
  - `cpp/include/engine/engine.hpp::ExecutionAlgoVWAP`
  - `cpp/include/engine/engine.hpp::ExecutionQualitySummary`
- Runtime integration:
  - `ExecutionRouter` tracks quality metrics per submission:
    - partial fills
    - spread/slippage aggregates
    - latency aggregates including p99
- Partial-fill modeling:
  - `MockBroker` returns partial fill retcode (`10010`) when configured fill ratio is below 1.0.
- Bridge exposure (`haruquant.sim`):
  - `ExecutionAlgoTWAP`
  - `ExecutionAlgoVWAP`
  - `ExecutionQualitySummary`
  - `ExecutionRouter.quality_summary()`
- Evidence:
  - `cpp/tests/test_twap_vwap.cpp`
  - `tests/integration/test_partial_fills.py`
  - `docs/haruquant/usage/live/execution_quality.md`

## Event-Driven Backtest Engine (IP-37)

- Core C++ engine:
  - `cpp/include/engine/engine.hpp::BacktestEngine`
  - `cpp/src/engine/engine.cpp`
- Execution path:
  - deterministic bar/tick loop
  - order lifecycle routed through `TradeSimulator` (OMS path)
  - account/position monitoring with close-reason tracking
- Lifecycle callbacks:
  - `set_on_bar_processed(...)`
  - `set_on_tick_processed(...)`
  - `set_on_trade_event(...)`
  - trade callback payload: `BacktestTradeEvent` with `event_type` (`open` / `close`) and `trade` snapshot
- Bridge exposure (`haruquant.sim`):
  - `BacktestEngine` callback registration for bar/tick/trade lifecycle hooks
  - `BacktestTradeEvent`
- Evidence:
  - `cpp/tests/test_backtest_event_runner.cpp`
  - `tests/e2e/test_backtest_event_path.py`
  - `docs/haruquant/usage/backtest/event_runner.md`

## Vectorized Backtest Engine (IP-38)

- Core C++ engine:
  - `cpp/include/engine/engine.hpp::VectorizedBacktestEngine`
  - `cpp/src/engine/analytics.cpp`
- Design:
  - batch-style deterministic bar processing loop
  - reuses `TradeSimulator` order path for consistent OMS semantics
  - tracks processed bars and executed trade count
- Bridge exposure (`haruquant.sim`):
  - `VectorizedBacktestEngine.run(...)`
  - `VectorizedBacktestEngine.processed_bars()`
  - `VectorizedBacktestEngine.total_trades()`
  - `VectorizedBacktestEngine.account_snapshot()`
- Parity validation:
  - event-driven vs vectorized comparison on deterministic bars
- Evidence:
  - `cpp/tests/test_backtest_vectorized.cpp`
  - `tests/parity/test_event_vs_vectorized_parity.py`
  - `docs/haruquant/usage/backtest/vectorized_runner.md`

## Fill Simulator and Transaction Cost Model (IP-39)

- Core C++ components:
  - `cpp/include/costs/costs_engine.hpp::CostsEngine`
  - `cpp/include/costs/slippage_model.hpp`
  - `cpp/include/costs/commission_model.hpp`
  - `cpp/include/costs/swap_model.hpp`
  - `cpp/include/costs/spread_model.hpp`
- Behavior:
  - pending and market order fill evaluation
  - SL/TP exit evaluation
  - gap-price handling for stop/take-profit executions
  - commission/swap/slippage/spread cost computation
  - seeded deterministic RNG for stochastic cost models
- Evidence:
  - `cpp/tests/test_costs_engine.cpp`
  - `docs/haruquant/usage/backtest/cost_and_fill_models.md`

## Python Trading Engine Result Packaging

- Python simulator runs in `apps/trading/main.py::Engine.run(...)` expose result accessors after processing completes.
- Result models now live in `apps/trading/core.py`:
  - `TradeRecord`: completed trade lifecycle row aligned to SQLite backtest trade persistence
  - `EquityPoint`: account curve snapshot aligned to equity-curve persistence
  - `RunResult`: packaged container for `trades`, `equity_curve`, `processed_ticks`, `final_balance`, and `final_equity`
- Engine accessors:
  - `Engine.get_completed_trades()`
  - `Engine.get_equity_curve()`
  - `Engine.get_run_result(processed_ticks=...)`
  - `Engine.clear_completed_trades()`
- Serialization helpers:
  - `TradeRecord.to_dict()`
  - `EquityPoint.to_dict()`
  - `RunResult.to_dict()`
  - datetime fields are converted to ISO 8601 strings so the payload is JSON-safe for API responses
- Example usage:
  - `examples/trading/trade_example.py::example_14_trade_results_report()`

## Python Trading Engine Multi-Symbol Portfolio V1

- `Engine.run(...)` still processes one chronological tick DataFrame, but V1 portfolio backtests can now concatenate multiple symbol tick streams into one merged timeline.
- Portfolio tick contract:
  - existing execution columns remain unchanged
  - `symbol` is required for merged multi-symbol runs
  - optional metadata such as `signal_timeframe` can be attached for reporting/debugging
- Preparation flow stays outside the engine:
  - fetch bars per symbol
  - run strategy per symbol
  - convert to ticks per symbol
  - add `symbol` metadata
  - concatenate and stable-sort by timestamp before `Engine.run(...)`
- Shared-account behavior remains unchanged:
  - one account/equity/margin pool
  - global schedules for position, pending, account, portfolio, and risk checks
- Reference example:
  - `examples/trading/trade_example.py::example_13_simple_portfolion_backtest()`

## Python Trading Engine Multi-Timeframe Phase 2 Direction

- Phase 2 still builds on the V1 merged portfolio stream rather than replacing it.
- Multi-timeframe processing is intended to happen at the individual symbol strategy-preparation level, not inside `Engine.run(...)`.
- Planned direction:
  - fetch bars per symbol and per required timeframe before signal generation
  - let each strategy incorporate its own higher-timeframe context into the symbol's final signalized bars
  - convert those already multi-timeframe-aware signal bars into ticks
  - merge symbol tick streams only after multi-timeframe signal generation is complete
  - keep one shared `Engine.run(...)` timeline for execution/account simulation
- Deferred from V1 on purpose:
  - arbitrary timeframe bundles inside `Engine.run(...)`
  - strategy callbacks that consume multi-symbol data directly
  - symbol-specific scheduling or per-symbol monitor cadence


## Optimization Engine Path

- `apps/optimization/execution.py` is the shared bridge from optimization methods into `apps/trading.Engine`.
- Grid, random, Bayesian, genetic, and walk-forward optimization now run strategy bars through `strategy.on_bar(...)`, convert to `timeframe_ticks` with `TicksGenerator`, then execute with `Engine.run(...)`.
- Optimization methods no longer depend on `apps.simulation` for these execution paths.
- Result scoring now reads the engine's completed trade records and equity curve, then derives optimization metrics with the existing `apps.finance` helpers.

## Frontend Backtest API Client

- `ui/src/lib/api/backtest.ts` is the thin frontend wrapper for the existing FastAPI backtest routes under `/api/backtest`.
- The current UI uses it for:
  - starting single-strategy backtests with `POST /api/backtest/run/{strategy_id}`
  - starting portfolio backtests with `POST /api/backtest/portfolio/run/{strategy_id}`
  - loading run status/details with `GET /api/backtest/{backtest_id}`
  - listing runs with `GET /api/backtest/`
  - updating alias/description with `PUT /api/backtest/{backtest_id}`
  - deleting runs with `DELETE /api/backtest/{backtest_id}`
- The client reads the auth token from the same browser storage key used by `ui/src/lib/auth-context.tsx` and attaches `Authorization: Bearer ...` for authenticated backtest operations.

## Frontend Shared Error Parsing

- `ui/src/lib/api-error.ts` centralizes lightweight frontend error-to-message conversion for API failures.
- The helper currently normalizes:
  - plain strings
  - `Error` instances
  - FastAPI-style `detail` payloads, including validation-error arrays
- Current consumers use `getErrorMessage(error)` directly in toast descriptions so UI error handling stays simple and consistent.

## Frontend Simulator API Client

- `ui/src/lib/api/simulator.ts` is the thin frontend wrapper for the simulator routes under `/api/simulator`.
- The current simulation UI uses it for:
  - starting and resuming sessions
  - loading session state and paused sessions
  - advancing bars and fetching specific bars
  - updating speed and pause state
  - executing market trades and placing pending orders
  - modifying and closing positions
  - modifying and deleting pending orders
  - seeking to a bar index and deleting sessions
- The client uses the same browser token storage key as `ui/src/lib/auth-context.tsx` and attaches bearer auth headers for all simulator requests.

## Frontend Simulator Trade Notifications

- `ui/src/lib/hooks/use-simulator-trade-notifications.ts` is currently a minimal client-side hook that exposes `notifyTrade(...)` for simulator UI components.
- The current implementation is intentionally a safe no-op so simulation trade execution can build and run without restoring a larger notification subsystem first.

## Frontend Optimization Client And Hooks

- `ui/src/lib/api/optimization.ts` is the thin frontend wrapper for `/api/optimization` routes.
- It currently covers:
  - optimization runs and ranked results
  - walk-forward job start and result fetch
  - Monte Carlo start/result fetch
  - parametric, position-sizing, consecutive-losing, profit-target, random-win-rate, robustness, and multi-entry utility endpoints
- `ui/src/lib/hooks/use-optimization.ts` provides the current optimization UI with:
  - `useOptimization(...)` for run details, ranked results, websocket progress, and cancellation
  - `useWalkForward(...)` for polling walk-forward result rows
- The hook uses websocket progress from `/api/optimization/ws/{optimization_id}` when available and keeps polling run/result endpoints as a simple fallback.
- `useOptimization(...)` keeps `onComplete` and `onProgressUpdate` in refs so the polling/WebSocket effect does not reconnect on every page render when callers pass inline callbacks.

## Frontend Edge Lab Client

- `ui/src/lib/api/edge.ts` is the thin frontend wrapper for `/api/edge-lab` routes.
- It currently covers:
  - edge-lab run execution
  - saved run summary/detail/trade retrieval and deletion
  - seasonality execution for the edge-lab seasonality screen

## Frontend Live Trading Client

- `ui/src/lib/api/live.ts` is the thin frontend wrapper for `/api/live` routes.
- It currently covers:
  - live session CRUD and start/stop/pause/resume/status
  - session strategies add/list/remove
  - market data and log retrieval
  - positions, orders, and manual execution actions used by the live dashboard

## Frontend Live Trading WebSocket Hook

- `ui/src/lib/hooks/use-live-websocket.ts` connects the live dashboard to `/api/live/sessions/{session_id}/ws`.
- It currently covers:
  - channel subscription for `signals`, `positions`, `status`, and `logs`
  - callback dispatch for the live dashboard components already using those events
  - simple reconnect tracking via `isConnected` and `reconnectAttempts`
- The hook keeps callback props in refs so inline handlers from components do not recreate the socket connection on every render.

## Frontend Trading Defaults

- `ui/src/lib/trading-defaults.ts` is the small shared source for default symbol lists used by the live manual order controls.
- It currently exposes the default forex, commodity, and indices symbol lists so the UI can fall back cleanly before user trading settings are loaded.

## Frontend Settings Hook

- `ui/src/lib/use-settings.ts` is the small shared hook for `/api/settings`.
- It currently covers:
  - loading the authenticated user's settings
  - updating scalar settings fields through `updateSettings(...)`
  - updating JSON-backed settings fields through `updateJSONField(...)`
  - reading parsed JSON-backed fields through `getJSONField(...)`
- The hook keeps its own local state in sync after updates and does not add a wider client-side settings store.

## Frontend Documentation Client

- `ui/src/lib/api/docs.ts` is the thin frontend wrapper for `/api/docs` routes.
- It currently covers:
  - documentation file tree loading
  - markdown content loading
  - markdown content save
  - markdown file deletion

