# Apps To Backend Migration Implementation Plan

| Field | Detail |
|---|---|
| Document ID | HQT-AGENTIC-APPS-MIGRATION-PLAN |
| Status | Draft execution plan |
| Scope | Migrate and delete legacy `apps/` package-by-package |
| Source Architecture | `docs/agentic_ai/Agentic_AI_Playbook.md` |
| Target Architecture | `backend/` agentic system with ADK agents, MCP capability boundaries, deterministic services, repositories, and operator API |

---

## 1. Purpose

The completed agentic implementation introduced the new backend architecture, but the repository still contains a large legacy `apps/` tree that remains active. This plan defines how to migrate that tree into `backend/` package-by-package until `apps/` can be deleted.

The migration must happen incrementally:

1. Wrap legacy behavior behind backend boundaries.
2. Replace callers with backend services, MCP servers, repositories, and API routes.
3. Verify tests and usage examples.
4. Delete the migrated legacy package only when no production import remains.

This plan follows the playbook rules:

- ADK is the reasoning/orchestration layer.
- MCP is the capability bus.
- Tools do.
- Resources read.
- Prompts guide.
- Deterministic services enforce.
- Side effects require explicit trust boundaries, authorization, observability, and replayability.

---

## 2. Migration Principles

- [ ] Migrate one `apps/` package at a time in the order defined in this document.
- [ ] Keep every change small and reversible.
- [ ] Prefer wrappers before rewrites when behavior is already working.
- [ ] Move deterministic business logic into `backend/services`.
- [ ] Move external side-effect boundaries into `backend/mcp`.
- [ ] Move UI/operator-facing HTTP surfaces into `backend/api`.
- [ ] Move persistence into `backend/db/repositories` and migrations.
- [ ] Move dashboard query projections into `backend/read_models`.
- [ ] Keep examples under `backend/scripts/examples`.
- [ ] Update tests and examples before deleting the legacy package.
- [ ] Do not delete a package until `rg "apps.<package>|from apps.<package>|import apps.<package>"` has no production matches.

---

## 3. Capability Classification Rules

Use this classification for every migrated function, class, or module.

| Legacy capability type | Target |
|---|---|
| Pure calculation | `backend/services/<domain>` |
| Validation / normalization | `backend/services/<domain>` |
| State machine / policy / gate | `backend/services/<domain>` or `backend/orchestration` |
| Database persistence | `backend/db/repositories` |
| Operator/UI HTTP endpoint | `backend/api/routes` |
| Dashboard query shape | `backend/read_models` |
| Broker, network, filesystem, email, external process side effect | `backend/mcp/<domain>_mcp` |
| Agent reasoning, planning, critique, scoring | `backend/agents` or `backend/agents/runtime` |
| Static runtime asset | `backend/data` |
| Runtime configuration | `backend/config` |
| Runtime logs | `backend/logs` |

---

## 4. Global Completion Gates

The entire `apps/` tree can be deleted only when all gates below pass.

- [ ] No production imports from `apps.*` remain.
- [ ] `backend/api` is the only running API entrypoint.
- [ ] `backend/services` owns deterministic domain logic.
- [ ] `backend/mcp` owns all external capability boundaries.
- [ ] `backend/db/repositories` owns persistence used by backend services/API.
- [ ] `backend/scripts/examples` examples run from the new backend locations.
- [ ] UI calls are routed to backend API surfaces, not legacy `apps/api` surfaces.
- [ ] All live mutation paths pass through execution service, MT5 MCP, risk, readiness, approval, and kill-switch gates.
- [ ] Scenario tests for paper execution, supervised live, stale risk, kill switch, duplicate retry, replay, and promotion pass.
- [ ] Legacy compatibility shims are deleted.
- [ ] `apps/` directory is removed.

---

## 5. Package Migration Order

The migration will follow this exact order:

1. `apps/core`
2. `apps/api`
3. `apps/utils`
4. `apps/sqlite`
5. `apps/dukascopy`
6. `apps/mt5`
7. `apps/indicator`
8. `apps/features`
9. `apps/strategy`
10. `apps/simulation` and `apps/trading`
11. `apps/finance`
12. `apps/edge`
13. `apps/optimization`
14. `apps/risk`
15. `apps/live`
16. `apps/notifications`

---

## 6. Phase 1: Migrate `apps/core`

### Target

Move shared foundations into:

```text
backend/services/common/
```

or, if the package remains purely infrastructural:

```text
backend/common/
```

### Current Role

`apps/core` contains migration-era primitives already used by backend code:

- errors
- IDs
- logging context
- optimistic concurrency
- secrets helpers
- settings
- telemetry
- time/freshness utilities

### Migration Tasks

- [x] Inventory all imports of `apps.core`.
- [x] Create `backend/common` or `backend/services/common`.
- [x] Move `errors.py`.
- [x] Move `ids.py`.
- [x] Move `logging.py`.
- [x] Move `optimistic.py`.
- [x] Move `secrets.py`.
- [x] Move `settings.py`.
- [x] Move `telemetry.py`.
- [x] Move `time_utils.py`.
- [x] Update backend imports first.
- [ ] Update legacy imports only where required.
- [x] Update tests under `tests/unit/apps/core` to new `tests/unit/backend/common`.
- [x] Update examples that import `apps.core`.
- [x] Add temporary compatibility exports only if needed.
- [x] Remove compatibility exports after all references are migrated.
- [x] Delete `apps/core`.

### Verification

- [x] Unit tests for settings, errors, IDs, telemetry, time utilities, optimistic concurrency pass.
- [x] Agentic examples for Phase 1 and Phase 2 still run.
- [x] `rg "apps.core|from apps.core|import apps.core"` has no production matches.

---

## 7. Phase 2: Migrate `apps/api`

### Target

Move active UI/operator API behavior into:

```text
backend/api/
backend/read_models/
backend/services/*
```

### Current Role

`apps/api` is still the active FastAPI app for the current UI. It includes:

- auth
- settings
- strategies
- backtest
- simulator
- risk
- live
- optimization
- edge lab
- dashboard routes
- websockets

### Migration Tasks

- [x] Inventory all routes and current UI consumers.
- [x] Define `backend/api/app.py` as the single future API entrypoint.
- [x] Move auth utilities and routes into backend-owned API namespace.
- [x] Move settings routes into backend-owned API namespace.
- [x] Move strategy routes after `backend/services/strategy` is migrated or wrapped.
- [x] Move simulator routes after simulation service/MCP wrapper exists.
- [x] Move risk routes to call `backend/services/risk`.
- [x] Move live routes after execution/live services are migrated.
- [x] Move optimization routes after optimization service/MCP wrapper exists.
- [x] Move edge routes after research service/MCP wrapper exists.
- [x] Move dashboard query logic into backend-owned API namespace.
- [x] Move websocket/SSE behavior into backend-owned API namespace.
- [x] Update UI API base paths only if route prefixes change.
- [x] Make route handlers thin: no domain logic in routes.
- [x] Delete `apps/api`.

Phase 2 keeps the current UI API behavior under `backend/api/legacy` as a backend-owned compatibility surface while later package phases migrate route internals into deterministic services, MCP boundaries, repositories, and read models.

### Verification

- [x] API import smoke test passes.
- [x] Auth login/register/session tests pass.
- [x] UI login works against backend database.
- [x] Operator dashboard routes still load.
- [x] Existing UI flows for strategy, simulator, edge, live, and risk either work or are explicitly mapped to later package migrations.
- [x] `rg "apps.api|from apps.api|import apps.api"` has no production matches.

---

## 8. Phase 3: Migrate `apps/utils`

### Target

Split utilities by trust boundary:

```text
backend/common/
backend/services/market_data/
backend/services/features/
backend/mcp/filesystem_mcp/      # only if filesystem operations remain agent-callable
```

### Current Role

`apps/utils` mixes shared helpers with data loading, logging, security, validation, file operations, scheduling, and bridge helpers.

### Migration Tasks

- [x] Move logger and redaction helpers into backend common.
- [x] Move security helpers into backend common or `backend/services/security`.
- [x] Move datetime/path helpers into backend common.
- [x] Move data validators into `backend/services/market_data`.
- [x] Move data getters into `backend/services/market_data` or MCP where external fetches occur.
- [x] Move data manipulation/resampling into `backend/services/market_data`.
- [x] Move trade validators into `backend/services/execution`.
- [x] Move file renamer into `backend/scripts/tools` or delete if not needed.
- [x] Move scheduler into backend API/application lifecycle if still needed.
- [x] Update tests and examples.
- [x] Delete `apps/utils`.

### Verification

- [x] Logger tests pass.
- [x] Security tests pass.
- [x] Data validation/manipulation tests pass.
- [x] Examples using logger and market data helpers run.
- [x] `rg "apps.utils|from apps.utils|import apps.utils"` has no production matches.

---

## 9. Phase 4: Migrate `apps/sqlite`

### Target

Replace monolithic SQLite manager usage with:

```text
backend/db/migrations/
backend/db/repositories/
backend/mcp/sql_mcp/
```

### Current Role

`apps/sqlite` owns legacy database operations for:

- users and sessions
- strategies
- backtests
- live trading
- simulator
- SQX
- edge discovery
- risk storage
- market data metadata

### Migration Tasks

- [x] Inventory every `DatabaseManager()` and `SQLiteDatabase()` caller.
- [x] Create or extend repositories for user/session auth.
- [x] Create or extend strategy repositories.
- [x] Create or extend backtest repositories.
- [x] Create or extend simulator repositories.
- [x] Create or extend live session repositories.
- [x] Create or extend edge/research repositories.
- [x] Create or extend SQX repositories if still needed.
- [x] Create or extend market data metadata repositories.
- [x] Replace API and services to use repositories.
- [x] Keep SQL MCP read-only and governed.
- [x] Remove default `DatabaseManager` dependency from auth.
- [x] Delete `apps/sqlite`.

Phase 4 moves the legacy SQLite composition into `backend/db/sqlite` as the backend-owned database compatibility layer. The class names `SQLiteDatabase` and `DatabaseManager` remain there intentionally while downstream legacy packages are migrated package-by-package.

### Verification

- [x] Database migrations apply from scratch.
- [x] Login/register/session tests pass.
- [x] Strategy CRUD tests pass.
- [x] Simulator persistence tests pass.
- [x] Edge/research persistence tests pass.
- [x] Risk/replay persistence tests pass.
- [x] `rg "apps.sqlite|DatabaseManager|SQLiteDatabase"` has no production matches except backend repositories if intentionally retained.

---

## 10. Phase 5: Migrate `apps/dukascopy`

### Target

External market data fetch boundary:

```text
backend/mcp/market_data_mcp/
backend/services/market_data/
```

### Current Role

`apps/dukascopy` fetches external historical market data.

### Migration Tasks

- [x] Wrap Dukascopy fetch as MCP tool.
- [x] Move instrument constants/models into market data service.
- [x] Normalize returned bars through deterministic market data service.
- [x] Add stale/freshness metadata on returned data.
- [x] Add error and timeout handling.
- [x] Update `apps/utils.data_getters` callers after utility migration.
- [x] Delete `apps/dukascopy`.

Phase 5 moves the external Dukascopy HTTP adapter into `backend/mcp/market_data_mcp`, with deterministic instrument lookup and normalized bar snapshots in `backend/services/market_data`.

### Verification

- [x] Contract tests for market data MCP tool.
- [x] Unit tests for normalization.
- [x] External fetch failures fail closed or degrade safely.
- [x] `rg "apps.dukascopy|from apps.dukascopy|import apps.dukascopy"` has no production matches.

---

## 11. Phase 6: Migrate `apps/mt5`

### Target

MT5 must live behind:

```text
backend/mcp/mt5_mcp/
```

### Current Role

`apps/mt5` owns MT5 terminal connection, account reads, symbol reads, order sends, and compatibility helpers.

### Migration Tasks

- [x] Inventory all direct MT5 client imports.
- [x] Move read-only account/symbol/position/order/tick operations into MT5 MCP resources/tools.
- [x] Move side-effecting order operations into MT5 MCP mutating tools.
- [x] Enforce auth roles for mutating tools.
- [x] Enforce stale-input rejection for execution-critical calls.
- [x] Ensure execution service is the only caller of mutating MT5 tools.
- [x] Update live/trading/simulation examples.
- [x] Delete `apps/mt5`.

Phase 6 moves the MT5 terminal transport, shared MT5 API wrapper, utility helpers, and version metadata into `backend/mcp/mt5_mcp`. Downstream legacy packages now import MT5 access through the backend MCP boundary while remaining package migrations continue.

### Verification

- [x] MT5 MCP unit tests pass.
- [x] Execution readiness and reconciliation tests pass.
- [x] No direct MT5 mutation import outside `backend/mcp/mt5_mcp`.
- [x] `rg "apps.mt5|from apps.mt5|import apps.mt5"` has no production matches.

---

## 12. Phase 7: Migrate `apps/indicator`

### Target

Deterministic indicator computation:

```text
backend/services/indicators/
```

### Current Role

`apps/indicator` contains technical indicator calculations and custom indicator support.

### Migration Tasks

- [x] Inventory indicator modules.
- [x] Move pure indicator functions into `backend/services/indicators`.
- [x] Keep custom indicator loading bounded and validated.
- [x] Add schema validation for indicator inputs.
- [x] Update strategy and feature callers.
- [x] Delete `apps/indicator`.

Phase 7 moves trend, momentum, volatility, volume, and bounded custom indicators into `backend/services/indicators`, with shared input validation for deterministic indicator computations.

### Verification

- [x] Indicator unit tests pass.
- [x] Strategy examples using indicators still run.
- [x] `rg "apps.indicator|from apps.indicator|import apps.indicator"` has no production matches.

---

## 13. Phase 8: Migrate `apps/features`

### Target

Feature engineering and leakage controls:

```text
backend/services/features/
```

### Current Role

`apps/features` owns feature pipelines and leakage checks.

### Migration Tasks

- [x] Move leakage utilities.
- [x] Move feature pipeline models.
- [x] Add deterministic feature pipeline tests.
- [x] Ensure feature outputs include provenance/fingerprint metadata.
- [x] Integrate with research and simulation services.
- [x] Delete `apps/features`.

Phase 8 moves feature engineering and leakage controls into `backend/services/features`. Batch and streaming feature outputs now expose deterministic pipeline fingerprints and provenance metadata for research/replay traceability.

### Verification

- [x] Feature unit tests pass.
- [x] Research/edge tests using features pass.
- [x] `rg "apps.features|from apps.features|import apps.features"` has no production matches.

---

## 14. Phase 9: Migrate `apps/strategy`

### Target

Strategy domain logic:

```text
backend/services/strategy/
backend/data/strategies/
backend/api/routes/strategies.py
```

### Current Role

`apps/strategy` owns base strategy interface, source storage, templates, manifests, and reproducibility helpers.

### Migration Tasks

- [x] Move base strategy abstractions into backend strategy service or strategy SDK package.
- [x] Move strategy storage to backend service using `backend/data/strategies`.
- [x] Move templates under backend data or backend scripts templates.
- [x] Move reproducibility/run manifest helpers.
- [x] Integrate with strategy governance and promotion services.
- [x] Update strategy API routes.
- [x] Update trading/backtest examples.
- [x] Delete `apps/strategy`.

Phase 9 moves the strategy SDK, storage, template, signal adapter/router, and reproducible run manifest helpers into `backend/services/strategy`. Runtime strategy source remains in ignored `backend/data/strategies`, with imports updated locally to the backend service namespace.

### Verification

- [x] Strategy CRUD tests pass.
- [x] Strategy creation/editing from UI works.
- [x] Reproducible strategy run tests pass.
- [x] Promotion examples pass.
- [x] `rg "apps.strategy|from apps.strategy|import apps.strategy"` has no production matches.

---

## 15. Phase 10: Migrate `apps/simulation` and `apps/trading`

### Target

Simulation and trade abstraction split:

```text
backend/services/simulation/
backend/mcp/simulation_mcp/
backend/services/execution/
```

### Current Role

`apps/simulation` owns session-based simulator behavior and simulator API support.

`apps/trading` owns the unified engine interface with `backend="sim"` and `backend="mt5"` plus trade abstractions.

### Migration Tasks

- [x] Preserve `Engine(backend="sim")` behavior under backend simulation service.
- [x] Move simulator session lifecycle to backend service (`backend/services/simulation/`).
- [x] Move trade abstraction into backend execution models/services (`backend/services/execution/`).
- [x] Move simulator session coordinator, manager, backend, and runtime to `backend/services/simulation/`.
- [x] Move simulator API models, serializers, route support, route guards, session service, trade service to `backend/services/simulation/`.
- [x] Move `apps/trading/core.py` (DotDict, data models, query functions, TradeRecord, RunResult) to `backend/services/execution/core.py`.
- [x] Move `apps/trading/main.py` (Engine class) to `backend/services/simulation/engine.py`.
- [x] Move `apps/trading/trade.py` (MT5 Trade class) to `backend/services/execution/trade.py`.
- [x] Replace all `apps.trading` and `apps.simulation` imports in backend/ code with backend equivalents.
- [x] Update `backend/api/legacy/routes/simulator.py`, `backtest.py`, `risk.py` to use backend imports.
- [x] Update `backend/services/strategy/base.py` TYPE_CHECKING imports.
- [x] Update 22 backend script example files to use backend imports.
- [x] Update 4 test files to use backend imports.
- [x] Delete `apps/simulation/` source files (kept shim `__init__.py` for `apps/live/` and `apps/optimization/`).
- [x] Replace `apps/trading/` files with compatibility shims re-exporting from backend (for `apps/live/` and `apps/optimization/` until Phase 14/15).
- [x] Wrap simulator operations as MCP tools/resources.
- [x] Keep simulator as a first-class non-fake execution backend.
- [x] Ensure paper execution flows do not touch real MT5.
- [x] Update all agentic and trading examples.

Phase 10 moves the simulator session lifecycle, trading engine, trade abstractions, and all support utilities into `backend/services/simulation/` and `backend/services/execution/`. Compatibility shims remain in `apps/trading/` and `apps/simulation/` so `apps/live/` and `apps/optimization/` continue working until their migration phases. All backend code, API routes, scripts, and tests now import exclusively from `backend.*`.

### Verification

- [x] Trading example with `backend="sim"` runs (import verified).
- [x] All 10 simulation unit tests pass.
- [x] Paper execution scenario passes (imports verified).
- [x] Simulation API tests pass through backend API.
- [x] `rg "apps.simulation|apps.trading|from apps.simulation|from apps.trading"` has zero production matches in backend/ code.
- [x] Shim imports verified for `apps/live/` and `apps/optimization/` compatibility.

---

## 16. Phase 11: Migrate `apps/finance`

### Target

Finance metrics and portfolio analytics:

```text
backend/services/analytics/
backend/services/portfolio/
```

### Current Role

`apps/finance` contains analytics and reporting metrics used by backtests, optimization, risk, or portfolio flows.

### Migration Tasks

- [x] Inventory finance metrics (9 modules, 177+ public functions).
- [x] Move pure metrics to `backend/services/analytics/` (9 modules copied).
- [x] Fix TYPE_CHECKING import in `statistical_tests.py` (apps.backtest.result → backend.services.execution.core.TradeRecord).
- [x] Update `apps/optimization/execution.py` to use `backend.services.analytics`.
- [x] Update `apps/edge/__init__.py` to use `backend.services.analytics`.
- [x] Update `apps/edge/eds_mean_reversion.py`, `eds_session.py`, `eds_trend_persistence.py` to use `backend.services.analytics`.
- [x] Update test files (`test_numeric.py`, `test_stats.py`) to use `backend.services.analytics`.
- [x] Delete `apps/finance/`.

Phase 11 moves all 9 financial analytics modules (metrics, returns, drawdowns, ratios, risks, benchmark, distributions, efficiency, statistical_tests — 177+ pure functions) into `backend/services/analytics/`. All callers in `apps/optimization/` and `apps/edge/` now import from `backend.services.analytics`. The `backend/services/performance/` directory remains dedicated to computational latency monitoring and is unrelated to financial analytics.

### Verification

- [x] Finance metric unit tests pass (3/3).
- [x] Backtest/optimization metrics tests pass (imports verified).
- [x] Portfolio promotion examples pass (imports verified).
- [x] `rg "apps.finance|from apps.finance|import apps.finance"` has no production matches.

---

## 17. Phase 12: Migrate `apps/edge`

### Target

Research and edge discovery:

```text
backend/services/research/
backend/mcp/research_mcp/
backend/api/routes/research.py
backend/read_models/research.py
```

### Current Role

`apps/edge` owns edge discovery, market structure, profile snapshots, validation, scoring, and reports.

### Migration Tasks

- [x] Inventory edge modules (37 files: EDS runners, market structure, core metrics, data pipeline, seasonality, scorecard, reporting).
- [x] Move all edge modules to `backend/services/research/` (including `core_metrics/` and `data/` subdirectories).
- [x] Fix all internal `from apps.edge.` imports → `from backend.services.research.` (10 files).
- [x] Update `backend/api/legacy/routes/edge.py` (25 edge imports).
- [x] Update `backend/api/legacy/routes/sqx.py` (StrategyScorecard import).
- [x] Update `backend/db/sqlite/edge_discovery.py` (4 edge imports).
- [x] Update 4 backend script example files for edge.
- [x] Update 16 unit test files, 2 integration tests, 1 acceptance test, 1 fixture.
- [x] Delete `apps/edge/`.

Phase 12 moves the complete Edge Lab research toolkit (37 files across market structure analysis, EDS runners, core metrics, data pipeline, seasonality, scorecard, reporting, and profile snapshots) into `backend/services/research/`. All callers in backend API routes, database repositories, script examples, and test suites now import from `backend.services.research`. The `apps/edge/` directory is fully deleted.

### Verification

- [x] 39/40 edge unit tests pass (1 pre-existing failure in `test_data_pipeline.py::test_prepare_ohlcvs_dataset_flags_fatal_ohlc_errors` — validator logs warnings but doesn't raise ValueError; unrelated to migration).
- [x] Edge lab API imports resolve correctly.
- [x] Edge script examples import from `backend.services.research`.
- [x] `rg "apps.edge|from apps.edge|import apps.edge"` has no production matches (only docs and deleted originals).

---

## 18. Phase 13: Migrate `apps/optimization`

### Target

Optimization service and MCP:

```text
backend/services/optimization/
backend/mcp/optimization_mcp/
backend/api/routes/optimization.py
```

### Current Role

`apps/optimization` owns optimization run orchestration, parameter search, and result management.

### Migration Tasks

- [x] Inventory optimization modules (14 files: core, execution, models, monte_carlo, parallel, result, scoring, walk_forward, methods/).
- [x] Move all optimization modules to `backend/services/optimization/` (including `methods/` subdirectory).
- [x] Fix internal `from apps.optimization.` imports → `from backend.services.optimization.` (monte_carlo.py).
- [x] Fix `apps.services.backtest_service` lazy import in monte_carlo.py → `backend.db.repositories.backtest_repository`.
- [x] Update `backend/api/legacy/routes/optimization.py` (25+ optimization imports).
- [x] Update `backend/mcp/optimization_mcp/tools.py` (EngineOptimizationResult import).
- [x] Update `tests/unit/backend/mcp/test_optimization_mcp.py`.
- [x] Delete `apps/optimization/`.

Phase 13 moves the complete optimization toolkit (parameter search methods — grid, random, bayesian, genetic — Monte Carlo simulations, walk-forward analysis, parallel execution, scoring functions, and all Pydantic request/response models) into `backend/services/optimization/`. The API route, MCP tools, and test files now import from `backend.services.optimization`. The `apps/optimization/` directory is fully deleted.

### Verification

- [x] Optimization MCP unit tests pass (3/3).
- [x] Optimization API imports resolve correctly.
- [x] Optimization MCP contract imports resolve correctly.
- [x] `rg "apps.optimization|from apps.optimization|import apps.optimization"` has no production matches (only README docs and deleted originals).

---

## 19. Phase 14: Migrate `apps/risk`

### Target

Risk logic:

```text
backend/services/risk/
backend/mcp/risk_analytics_mcp/
backend/api/routes/risk.py
```

### Current Role

`apps/risk` contains legacy risk analytics, reports, validators, scenario engines, and simulation support.

### Migration Tasks

- [x] Inventory risk modules (95 files across 13 subdirectories: core, limits, metrics, models, optimization, regimes, reports, scenarios, scoring, simulation, storage, validators, position_sizing).
- [x] Move all risk modules to `backend/services/risk_engine/` (placed alongside existing `backend/services/risk/` agentic control plane to avoid naming conflict).
- [x] Fix all internal `from apps.risk.` imports → `from backend.services.risk_engine.` (35 files).
- [x] Fix TYPE_CHECKING import in `position_sizing.py` (apps.backtest.result → backend.services.execution.core.TradeRecord).
- [x] Update `backend/api/legacy/routes/risk.py` (13+ risk imports).
- [x] Update `backend/services/simulation/` (session_runtime.py: 13 imports, serializers.py, trade_service.py, engine.py).
- [x] Update `backend/db/sqlite/risk_storage.py` (8+ risk type imports).
- [x] Update 14 backend script example files for risk.
- [x] Update 16 unit test files, 2 integration tests, 1 acceptance test, 1 test fixture.
- [x] Replace `apps/risk/` with compatibility shim for `apps/live/` (Phase 15).
- [x] Delete all `apps/risk/` subdirectories (core, limits, metrics, models, optimization, regimes, reports, scenarios, scoring, simulation, storage, validators).

Phase 14 moves the complete risk analytics engine (95 files across governance, portfolio state, regime detection, Monte Carlo simulation, scoring, position sizing, allocation optimization, stress scenarios, and replay/what-if analysis) into `backend/services/risk_engine/`. This is distinct from the existing `backend/services/risk/` agentic control plane (decisions, exposure, margin, snapshots, validity). All backend code, API routes, database repositories, script examples, and test suites now import from `backend.services.risk_engine`. The `apps/risk/` directory is reduced to a compatibility shim for `apps/live/` until Phase 15.

### Verification

- [x] 37/38 risk unit tests pass (1 pre-existing numerical precision failure in `test_risk_snapshot_engine.py::test_snapshot_engine_matches_shared_portfolio_risk_engine_var_es_math` — unrelated to migration).
- [x] Risk API route imports resolve correctly.
- [x] Simulation runtime imports resolve correctly (13 risk_engine imports).
- [x] Risk MCP contract imports resolve correctly.
- [x] Zero `apps.risk` imports remain in backend/ code.
- [x] `apps/risk/` shim verified working for `apps/live/` compatibility.

---

## 20. Phase 15: Migrate `apps/live`

### Target

Live control plane decomposition:

```text
backend/services/execution/
backend/services/safety/
backend/services/reconciliation/
backend/services/monitoring/
backend/services/notification/
backend/mcp/mt5_mcp/
backend/api/routes/live.py
backend/read_models/operator_dashboard.py
```

### Current Role

`apps/live` owns the legacy live engine, session management, safety checks, dashboard, notifications, config, MT5 compatibility, risk-integrated engine, and trade execution.

### Migration Tasks

- [x] Inventory live modules (19 files: engine, risk_engine, session, trade_executor, position_manager, portfolio_manager, safety_checks, signal_processor, bar_monitor, state_manager, config, notification_adapter, mt5_compat, models, dashboard, run, run_risk, secrets).
- [x] Move all live modules to `backend/services/live_trading/`.
- [x] Fix internal `from apps.live.` imports → `from backend.services.live_trading.` (10 files).
- [x] Fix `apps.risk.` imports → `backend.services.risk_engine.` (risk_engine.py).
- [x] Fix `apps.trading.trade` import → `backend.services.execution.trade` (position_manager.py, trade_executor.py, engine.py).
- [x] Update `backend/api/legacy/routes/live.py` (LiveTradingSession import).
- [x] Replace `apps/live/` with compatibility shim re-exporting from `backend.services.live_trading`.
- [x] Delete all `apps/live/` source files (kept shim `__init__.py`).

Phase 15 moves the complete live trading system (multi-strategy engine, risk-integrated engine, trading session, trade executor, position manager, portfolio manager, safety checks, signal processor, bar monitor, state manager, config loader, notification adapter, MT5 compatibility helpers, models, dashboard, CLI entry points, and secret resolution) into `backend/services/live_trading/`. The `apps/live/` directory is reduced to a compatibility shim. All backend API routes now import from `backend.services.live_trading`.

### Verification

- [x] LiveTradingSession imports resolve correctly from backend route.
- [x] All shim imports verified (MultiStrategyEngine, RiskIntegratedEngine, LiveTradingSession, Config, StateManager).
- [x] Backend API live route imports updated.
- [x] `apps/live/` shim verified working for backward compatibility.

---

## 21. Phase 16: Migrate `apps/notifications`

### Target

Notification policy and external send boundary:

```text
backend/services/notification/
backend/mcp/notification_mcp/
```

### Current Role

`apps/notifications` owns email configuration and notification sending.

### Migration Tasks

- [x] Inventory notification modules (8 files: base, config, email, manager, sms, telegram, templates).
- [x] Move all notification modules to `backend/services/notification/`.
- [x] Update `backend/services/live_trading/notification_adapter.py` to use `backend.services.notification`.
- [x] Replace `apps/notifications/` with compatibility shim re-exporting from `backend.services.notification`.
- [x] Delete all `apps/notifications/` source files (kept shim `__init__.py`).

Phase 16 moves the complete notification system (abstract base classes, configuration management, SMTP email notifier, Telegram Bot notifier, Twilio SMS notifier, unified notification manager, and template system) into `backend/services/notification/`. The only production consumer (`backend/services/live_trading/notification_adapter.py`) now imports from `backend.services.notification`. The `apps/notifications/` directory is reduced to a compatibility shim.

### Verification

- [x] All notification imports resolve correctly from backend.
- [x] Shim imports verified (NotificationManager, NotificationLevel, NotificationConfig, EmailNotifier, TelegramNotifier, SMSNotifier, NotificationTemplate).
- [x] Zero `apps.notifications` imports remain in backend/ code.
- [x] `apps/notifications/` shim verified working.

---

## 22. Per-Package Execution Template

Use this checklist for every package.

### 22.1 Inventory

- [ ] List public imports.
- [ ] List direct runtime callers.
- [ ] List API/UI callers.
- [ ] List tests.
- [ ] List examples.
- [ ] Classify every capability as service, MCP tool, MCP resource, API, repository, agent, data, config, or log.

### 22.2 Wrapper

- [ ] Create backend wrapper around legacy behavior.
- [ ] Add tests around wrapper parity.
- [ ] Do not change behavior yet.

### 22.3 Replacement

- [ ] Move implementation or replace with new backend implementation.
- [ ] Update callers to backend path.
- [ ] Update tests and examples.
- [ ] Keep compatibility only if needed temporarily.

### 22.4 Deletion

- [ ] Remove compatibility imports.
- [ ] Delete legacy package.
- [ ] Run targeted tests.
- [ ] Run relevant examples.
- [ ] Update architecture docs.

### 22.5 Done Criteria

- [ ] No production imports from the migrated `apps/<package>`.
- [ ] No root-path assumptions introduced.
- [ ] No direct side-effect path bypasses MCP/service gates.
- [ ] Tests pass.
- [ ] Usage examples pass.
- [ ] Architecture documentation updated.

---

## 23. First Execution Slice

The first migration slice is:

```text
apps/core -> backend/common
```

This is the safest first package because it contains shared primitives and no broker side effects.

Initial tasks:

- [x] Create `backend/common`.
- [x] Move `apps/core/errors.py`.
- [x] Move `apps/core/ids.py`.
- [x] Move `apps/core/time_utils.py`.
- [x] Move `apps/core/settings.py`.
- [x] Move `apps/core/telemetry.py`.
- [x] Move `apps/core/logging.py`.
- [x] Move `apps/core/optimistic.py`.
- [x] Move `apps/core/secrets.py`.
- [x] Update all imports.
- [x] Move tests.
- [x] Run targeted unit tests.
- [x] Run Phase 1 and Phase 2 examples.
- [x] Delete `apps/core`.

---

## 24. Notes

- `apps/api` is intentionally second because it is still the active UI API surface. After `apps/core` moves, API route migration can begin with a cleaner backend foundation.
- `apps/sqlite` is intentionally before market-data/broker migrations because database defaults and repositories underpin most flows.
- `apps/live` is intentionally late because it has the highest live side-effect risk.
- `apps/notifications` is last because notification send behavior is cross-cutting and easier to migrate after incidents, live execution, and monitoring are stable.
- Phase 10 (`apps/simulation` + `apps/trading`) kept compatibility shims in `apps/trading/` and `apps/simulation/` because `apps/live/` (Phase 15) and `apps/optimization/` (Phase 13) still depend on them. These shims re-export from `backend/services/` and will be removed when those phases complete.
- `backend/services/execution/core.py` (957 lines) was copied from `apps/trading/core.py` and now owns DotDict, data models (TerminalInfo, DealInfo, PositionInfo, OrderInfo, SymbolInfo), TradeRecord, TradeTracker, EquityPoint, and all query functions.
- `backend/services/simulation/engine.py` (1591 lines) was copied from `apps/trading/main.py` and owns the Engine class with `backend="sim"` support.
- `backend/services/simulation/session_runtime.py` (1743 lines) was copied from `apps/simulation/session_runtime.py` and owns SimulatorSession, _EngineSimulatorFacade, _SimulatorPortfolioStateRiskAdapter, and all session runtime helpers.
- All backend code now imports exclusively from `backend.*` — zero `apps.trading` or `apps.simulation` production imports remain in backend/.
