# HaruQuant Architecture Notes

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

- C++ bridge input (`hqt_engine.set_log_level`, `hqt_engine.emit_log`) accepts:
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
- Bridge controls exposed via `hqt_engine`:
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

## Schema Validators (FR-UTIL-003)

- Pydantic-based schema validators are implemented in `apps/utils/validate.py`.
- Models:
  - `MarketTickSchema`
  - `TradeSchema`
  - `RuntimeConfigSchema` (with nested `LoggingConfigSchema` and `RiskConfigSchema`)
- Helper entry points:
  - `validate_market_schema(payload)`
  - `validate_trade_schema(payload)`
  - `validate_config_schema(payload)`
- These helpers perform schema contract validation and return `(is_valid, message)` for compatibility with existing utility call patterns.
- Existing `TradeValidator` remains unchanged and continues to provide deeper business/MT5-aware validation.
- C++ schema primitives are implemented in:
  - `cpp/include/util/schema_validator.hpp`
  - `cpp/src/engine/schema_validator.cpp`
- C++/bridge validation entry points exposed via `hqt_engine`:
  - `validate_market_schema(payload)`
  - `validate_trade_schema(payload)`
  - `validate_config_schema(payload)`
- Bridge payload handling supports nested config dictionaries by flattening keys into schema paths (e.g., `logging.level`, `risk.max_positions`).

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
  - `bridge/src/risk_bindings.cpp` (`hqt_engine._risk`)
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
  - `bridge/src/risk_bindings.cpp` (`hqt_engine._risk`)
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
  - `bridge/src/risk_bindings.cpp` (`hqt_engine._risk`)
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
  - `hqt_engine.ownership_contracts()`
  - explicit policies for:
    - C++ owned / Python view
    - shared ownership
    - callback ownership
    - zero-copy buffer ingestion
- Lifetime enforcement in bindings:
  - long-lived parent/child relationships are guarded with nanobind `keep_alive`
  - view-returning accessors use `reference_internal` for parent-bound lifetimes
- Zero-copy contract path:
  - `hqt_engine.sum_buffer_zero_copy(buffer)` consumes contiguous `float64` buffers via Python buffer protocol without copy
- Evidence:
  - `tests/contracts/test_bridge_lifetime.py`
  - `docs/haruquant/usage/dev/bridge_ownership_rules.md`
  - `artifacts/logs/bridge/lifetime_validation.log`

## Exception Mapping C++ + Python (IP-20)

- Bridge-level typed exception classes exported by `hqt_engine`:
  - `BridgeError`
  - `ConfigurationError`
  - `ValidationError`
  - `RiskViolationError`
  - `OrderStateError`
  - `ExecutionError`
  - `TransientConnectivityError`
  - `FatalEngineError`
- Mapping helpers:
  - `hqt_engine.raise_exception_for_retcode(code, detail="")`
  - `hqt_engine.raise_exception_for_category(category, detail="")`
- Python adapter behavior:
  - `apps/simulation/backend.py::_translate_cpp_exception(...)` preserves typed `hqt_engine.*Error` exceptions and uses retcode taxonomy fallback when needed.
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
  - `hqt_engine.sum_buffer_zero_copy(buffer)` for contiguous `float64` buffers.
  - `hqt_engine.sum_auto(values)` uses zero-copy when buffer-compatible, otherwise copy fallback.
- Capability API:
  - `hqt_engine.bridge_transfer_capabilities()`
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
  - simulation/backtest side (`hqt_engine.sim`) canonical portfolio/account/position tracking
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
  - `hqt_engine.sim.PortfolioAllocator`
  - `hqt_engine.sim.RebalancePolicy`
  - `hqt_engine.sim.RebalanceController`
  - `hqt_engine.sim.ExposureConstraints`
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
  - `cpp/include/engine/engine.hpp::SimulatorClient`
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
    - `SimulatorClient::order_state(...)`
    - `SimulatorClient::order_state_name(...)`
- Idempotent submission:
  - `TradeRequest.client_order_id` enables duplicate-guarded submit flow.
  - Same `client_order_id` + same payload returns cached original result.
  - Same `client_order_id` + different payload is rejected.
- Bridge exposure:
  - `bridge/src/sim_bindings.cpp`:
    - `sim.TradeRequest.client_order_id`
    - `sim.OmsOrderState`
    - `sim.SimulatorClient.order_state(...)`
    - `sim.SimulatorClient.order_state_name(...)`
- Evidence:
  - `cpp/tests/test_sim_oms_state_machine.cpp`
  - `docs/haruquant/usage/trade/oms_state_machine_idempotency.md`
  - `tests/usage/trade/oms_state_machine_idempotency_cpp.py`

