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
- [x] Move strategy routes after `apps/strategy` is migrated or wrapped.
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

- [ ] Wrap Dukascopy fetch as MCP tool.
- [ ] Move instrument constants/models into market data service.
- [ ] Normalize returned bars through deterministic market data service.
- [ ] Add stale/freshness metadata on returned data.
- [ ] Add error and timeout handling.
- [ ] Update `apps/utils.data_getters` callers after utility migration.
- [ ] Delete `apps/dukascopy`.

### Verification

- [ ] Contract tests for market data MCP tool.
- [ ] Unit tests for normalization.
- [ ] External fetch failures fail closed or degrade safely.
- [ ] `rg "apps.dukascopy|from apps.dukascopy|import apps.dukascopy"` has no production matches.

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

- [ ] Inventory all direct MT5 client imports.
- [ ] Move read-only account/symbol/position/order/tick operations into MT5 MCP resources/tools.
- [ ] Move side-effecting order operations into MT5 MCP mutating tools.
- [ ] Enforce auth roles for mutating tools.
- [ ] Enforce stale-input rejection for execution-critical calls.
- [ ] Ensure execution service is the only caller of mutating MT5 tools.
- [ ] Update live/trading/simulation examples.
- [ ] Delete `apps/mt5`.

### Verification

- [ ] MT5 MCP unit tests pass.
- [ ] Execution readiness and reconciliation tests pass.
- [ ] No direct MT5 mutation import outside `backend/mcp/mt5_mcp`.
- [ ] `rg "apps.mt5|from apps.mt5|import apps.mt5"` has no production matches.

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

- [ ] Inventory indicator modules.
- [ ] Move pure indicator functions into `backend/services/indicators`.
- [ ] Keep custom indicator loading bounded and validated.
- [ ] Add schema validation for indicator inputs.
- [ ] Update strategy and feature callers.
- [ ] Delete `apps/indicator`.

### Verification

- [ ] Indicator unit tests pass.
- [ ] Strategy examples using indicators still run.
- [ ] `rg "apps.indicator|from apps.indicator|import apps.indicator"` has no production matches.

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

- [ ] Move leakage utilities.
- [ ] Move feature pipeline models.
- [ ] Add deterministic feature pipeline tests.
- [ ] Ensure feature outputs include provenance/fingerprint metadata.
- [ ] Integrate with research and simulation services.
- [ ] Delete `apps/features`.

### Verification

- [ ] Feature unit tests pass.
- [ ] Research/edge tests using features pass.
- [ ] `rg "apps.features|from apps.features|import apps.features"` has no production matches.

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

- [ ] Move base strategy abstractions into backend strategy service or strategy SDK package.
- [ ] Move strategy storage to backend service using `backend/data/strategies`.
- [ ] Move templates under backend data or backend scripts templates.
- [ ] Move reproducibility/run manifest helpers.
- [ ] Integrate with strategy governance and promotion services.
- [ ] Update strategy API routes.
- [ ] Update trading/backtest examples.
- [ ] Delete `apps/strategy`.

### Verification

- [ ] Strategy CRUD tests pass.
- [ ] Strategy creation/editing from UI works.
- [ ] Reproducible strategy run tests pass.
- [ ] Promotion examples pass.
- [ ] `rg "apps.strategy|from apps.strategy|import apps.strategy"` has no production matches.

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

- [ ] Preserve `Engine(backend="sim")` behavior under backend simulation service.
- [ ] Wrap simulator operations as MCP tools/resources.
- [ ] Move simulator session lifecycle to backend service.
- [ ] Move trade abstraction into backend execution models/services.
- [ ] Keep simulator as a first-class non-fake execution backend.
- [ ] Ensure paper execution flows do not touch real MT5.
- [ ] Update all agentic and trading examples.
- [ ] Delete `apps/simulation`.
- [ ] Delete `apps/trading`.

### Verification

- [ ] Trading example with `backend="sim"` runs.
- [ ] Phase 2, Phase 3, and Phase 4 agentic examples run.
- [ ] Paper execution scenario passes.
- [ ] Simulation API tests pass through backend API.
- [ ] `rg "apps.simulation|apps.trading|from apps.simulation|from apps.trading"` has no production matches.

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

- [ ] Inventory finance metrics.
- [ ] Move pure metrics to analytics service.
- [ ] Move portfolio-relevant metrics to portfolio service.
- [ ] Add deterministic tests for metrics.
- [ ] Update reports, optimization, and risk callers.
- [ ] Delete `apps/finance`.

### Verification

- [ ] Finance metric unit tests pass.
- [ ] Backtest/optimization metrics tests pass.
- [ ] Portfolio promotion examples pass.
- [ ] `rg "apps.finance|from apps.finance|import apps.finance"` has no production matches.

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

- [ ] Move data cleaning/validation/enrichment to market data/features services where appropriate.
- [ ] Move edge discovery algorithms to research service.
- [ ] Move market structure analysis to research service.
- [ ] Move profile reporting and snapshots to research service/repository.
- [ ] Expose agent-facing research tools/resources through research MCP.
- [ ] Move edge API routes into backend API.
- [ ] Keep exports under `backend/data/simulations/exports`.
- [ ] Update edge examples.
- [ ] Delete `apps/edge`.

### Verification

- [ ] Edge lab API tests pass.
- [ ] Edge examples run.
- [ ] Research MCP contract tests pass.
- [ ] Export files land under `backend/data/simulations/exports`.
- [ ] `rg "apps.edge|from apps.edge|import apps.edge"` has no production matches.

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

- [ ] Move parameter-space models.
- [ ] Move grid/genetic optimization logic.
- [ ] Move result ranking and persistence integration.
- [ ] Expose optimization runs through MCP tools/resources.
- [ ] Move optimization API route.
- [ ] Connect optimization evidence to strategy promotion.
- [ ] Delete `apps/optimization`.

### Verification

- [ ] Optimization unit tests pass.
- [ ] Optimization API tests pass.
- [ ] Optimization MCP tests pass.
- [ ] Promotion evidence example can consume optimization output.
- [ ] `rg "apps.optimization|from apps.optimization|import apps.optimization"` has no production matches.

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

- [ ] Compare legacy risk modules against already implemented backend risk core.
- [ ] Move missing calculators into `backend/services/risk`.
- [ ] Move risk reports into risk or analytics service.
- [ ] Move risk scenario storage into repositories.
- [ ] Expose read-only risk analytics through MCP.
- [ ] Ensure live enforcement remains deterministic service-only.
- [ ] Delete duplicate legacy risk code after parity.
- [ ] Delete `apps/risk`.

### Verification

- [ ] Phase 2 risk tests pass.
- [ ] Risk analytics MCP tests pass.
- [ ] Risk reports still generate.
- [ ] Live risk gate tests pass.
- [ ] `rg "apps.risk|from apps.risk|import apps.risk"` has no production matches.

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

- [ ] Freeze direct changes to legacy live engine except migration adapters.
- [ ] Move config loading if not already handled by backend config/common settings.
- [ ] Move safety checks into safety/execution services.
- [ ] Move signal processing into strategy/execution service.
- [ ] Move trade execution into backend execution service.
- [ ] Move MT5 calls fully behind MT5 MCP.
- [ ] Move reconciliation behavior into backend reconciliation service.
- [ ] Move live dashboard data into read models and backend API.
- [ ] Move notification hooks into notification service/MCP.
- [ ] Remove direct live mutation paths not protected by risk/readiness/approval/kill-switch.
- [ ] Delete `apps/live`.

### Verification

- [ ] Supervised live scenario passes.
- [ ] Bounded autonomous live scenario passes.
- [ ] Kill-switch scenario passes.
- [ ] Duplicate retry/reconciliation scenario passes.
- [ ] Operator dashboard live views work.
- [ ] `rg "apps.live|from apps.live|import apps.live"` has no production matches.

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

- [ ] Move notification config models to notification service.
- [ ] Move message formatting to deterministic service.
- [ ] Move email/send side effects to notification MCP.
- [ ] Add role/policy checks for external sends.
- [ ] Add redaction tests for notification payloads.
- [ ] Update live/incident/monitoring callers.
- [ ] Delete `apps/notifications`.

### Verification

- [ ] Notification unit tests pass.
- [ ] Incident alert path can route notification intent.
- [ ] Notification MCP rejects unauthorized send attempts.
- [ ] `rg "apps.notifications|from apps.notifications|import apps.notifications"` has no production matches.

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
