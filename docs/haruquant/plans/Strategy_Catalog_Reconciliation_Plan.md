# Strategy Catalog Agentic Reconciliation Implementation Plan

Status: canonical reconciliation plan
Scope: legacy strategy workflow alignment with governed agentic architecture
Use this when: you need the migration and coexistence plan for strategy artifacts
Companion docs: `ND881_Implementation_Plan.md`, `../agents/Catalog.md`, `../workflows/Catalog.md`
Owner: backend platform
Review cadence: during active migration work

**Purpose:** Reconcile the legacy user-created strategy workflow with the agentic service architecture. The legacy UI and SQLite-backed strategy catalog should continue to work, while strategy lifecycle, evidence, and promotion controls become first-class agentic governance concepts.

**Decision:** User-created strategies remain artifacts under `data/strategies/{username}/{strategy_slug}/v{version}/`. The package `services/strategy/` remains application/service code: base classes, adapters, storage, validation, built-in baselines, and catalog orchestration. Do not move user strategy source files into `services/strategy/`.

---

## 0. Current System Baseline

- **UI entry points**
  - `ui/src/app/(dashboard)/strategies/page.tsx`
  - `ui/src/app/(dashboard)/strategies/[id]/page.tsx`
  - `ui/src/components/strategies/`
  - `ui/src/lib/api/strategies.ts`
- **HTTP API**
  - `api/routes/strategies.py`
  - Mounted at `/api/strategies` in `api/main.py`
- **Legacy operational database**
  - `data/database/haruquant.db`
  - Tables: `strategies`, `strategy_versions`, `strategy_shares`
  - SQLite managers: `data/database/sqlite/strategies.py`
- **Physical strategy artifacts**
  - Managed by `services/strategy/storage.py`
  - Current path pattern: `data/strategies/{username}/{strategy_name}/v{version}/strategy.py`
  - Metadata file: `metadata.json`
- **Agentic governance**
  - Tables: `gov_strategy_registry`, `gov_strategy_promotions`
  - Services: `services/strategy/governance/`

---

## 1. Target Architecture

Route all strategy create/read/update/delete/version operations through a service facade:

```text
UI /strategies
  -> ui/src/lib/api/strategies.ts
  -> api/routes/strategies.py
  -> services/strategy/catalog.py
      -> data/database/sqlite/strategies.py
      -> services/strategy/storage.py
      -> services/strategy/governance/registry.py
      -> services/strategy/governance/lifecycle.py
  -> data/database/haruquant.db
  -> data/strategies/{username}/{strategy_slug}/v{version}/strategy.py
```

The legacy tables stay as the operational strategy catalog because simulation, optimization, backtesting, live trading, and UI code already depend on integer `strategy_id` and `active_version_id`.

The agentic governance registry becomes the lifecycle and approval plane. It should reference, but not replace, the operational catalog.

---

## 2. Identity Model

Use two IDs deliberately:

- **Operational ID:** `strategies.id`, integer, used by existing UI, backtests, optimization, and live sessions.
- **Governance ID:** stable string, used by agentic governance.

Recommended governance ID format:

```text
strategy:{user_id}:{strategy_id}
```

Example:

```text
strategy:1:42
```

Add these optional columns to `strategies`:

```sql
ALTER TABLE strategies ADD COLUMN governance_strategy_id TEXT;
ALTER TABLE strategies ADD COLUMN artifact_root TEXT;
ALTER TABLE strategies ADD COLUMN strategy_family TEXT;
```

Acceptance:

- Every strategy can be resolved by legacy integer ID.
- Every strategy created after this change has a `governance_strategy_id`.
- Existing code that only knows `strategy_id: int` continues to work.

---

## 3. Phase 1 - Add Catalog Service Facade

Create:

```text
services/strategy/catalog.py
```

Core dataclasses or Pydantic models:

- `StrategyCatalogCreateRequest`
- `StrategyCatalogUpdateRequest`
- `StrategyCatalogRecord`
- `StrategyVersionRecord`
- `StrategyCodePayload`
- `StrategyCatalogService`

Service methods:

- `create_strategy(request, user_id)`
- `list_strategies(user_id, status=None, category=None, include_shared=False)`
- `get_strategy(strategy_id, user_id=None)`
- `update_strategy(strategy_id, request, user_id)`
- `delete_strategy(strategy_id, user_id)`
- `list_versions(strategy_id)`
- `get_version_code(strategy_id, version_id, user_id)`
- `rollback_version(strategy_id, version_id, user_id)`
- `export_strategy(strategy_id, user_id)`
- `import_strategy(...)`

Responsibilities:

- Coordinate database writes.
- Coordinate file writes.
- Compute version numbers.
- Compute code and parameter hashes.
- Register/update governance records.
- Normalize metadata.
- Resolve username and artifact paths.
- Enforce ownership checks before filesystem access.

Acceptance:

- `api/routes/strategies.py` no longer directly coordinates DB and filesystem writes.
- Existing API behavior stays compatible with `ui/src/lib/api/strategies.ts`.
- Unit tests cover service methods without requiring the frontend.

---

## 4. Phase 2 - Make Storage Path Stable

Current `StrategyStorage` derives paths from username and strategy name. That works, but renaming a strategy can orphan files or make old versions hard to resolve.

Recommended new artifact path:

```text
data/strategies/{username}/strategy_{strategy_id}_{strategy_slug}/v{version}/strategy.py
```

Example:

```text
data/strategies/haruperi/strategy_42_ema_cross/v1.0.0/strategy.py
```

Keep backward-compatible loading:

1. Try `strategy_versions.file_path` first.
2. Try new stable path.
3. Try existing legacy path: `{username}/{strategy_name}/v{version}/strategy.py`.
4. Try built-in baseline fallback only for known baseline names.

Tasks:

- Extend `StrategyStorage` with `get_strategy_artifact_root(...)`.
- Prefer `strategy_versions.file_path` when loading code.
- Store absolute or repo-relative canonical file path in `strategy_versions.file_path`.
- Keep legacy path resolution until migration is complete.

Acceptance:

- Strategy rename does not break loading existing versions.
- Existing folders under `data/strategies/haruperi/...` remain readable.
- Newly created strategies use stable `strategy_{id}_{slug}` folders.

---

## 5. Phase 3 - Database Migration

Add migration:

```text
data/database/migrations/00xx_strategy_catalog_agentic_reconciliation.sql
```

Migration content:

```sql
ALTER TABLE strategies ADD COLUMN governance_strategy_id TEXT;
ALTER TABLE strategies ADD COLUMN artifact_root TEXT;
ALTER TABLE strategies ADD COLUMN strategy_family TEXT;

CREATE INDEX IF NOT EXISTS ix_strategies_governance_strategy_id
    ON strategies (governance_strategy_id);

CREATE INDEX IF NOT EXISTS ix_strategies_user_family_updated
    ON strategies (user_id, strategy_family, updated_at DESC);
```

If the migration runner does not tolerate repeated `ALTER TABLE ADD COLUMN`, implement this with a Python migration helper that checks `PRAGMA table_info(strategies)` first.

Backfill script:

```text
scripts/tools/migrate_legacy_strategies_to_agentic_registry.py
```

Backfill steps:

1. Read all `strategies`.
2. Resolve `users.username`.
3. Resolve active and historical `strategy_versions`.
4. Resolve file path using current path, new path, or legacy path.
5. Compute `code_hash` from `strategy.py`.
6. Compute `parameter_hash` from canonical JSON parameters.
7. Set `governance_strategy_id = strategy:{user_id}:{id}`.
8. Set `strategy_family = category or "custom"`.
9. Set `artifact_root` to detected root.
10. Insert missing `gov_strategy_registry` rows.
11. Emit a report for missing files, orphan version rows, and folders without DB records.

Acceptance:

- Script is idempotent.
- Script does not delete or move files in its first version.
- Missing files are reported, not silently ignored.
- Existing strategies appear in `gov_strategy_registry`.

---

## 6. Phase 4 - Governance Integration

On create:

- Create legacy `strategies` row.
- Save `strategy.py` and `metadata.json`.
- Create `strategy_versions` row.
- Compute hashes.
- Register governance row in `gov_strategy_registry`.

Governance defaults:

```text
strategy_name = strategies.name
strategy_family = strategies.strategy_family or category or "custom"
current_lifecycle_state = "research"
owner_id = str(user_id)
code_hash = sha256(strategy.py)
parameter_hash = sha256(canonical parameters json)
```

On update:

- If only name/description/category/status changes, update operational metadata.
- If code or parameters change, create a new strategy version.
- If code or parameters change, update governance hash fields.
- Do not auto-promote lifecycle state based on UI save.

Lifecycle mapping:

```text
UI status inactive -> operationally not runnable
UI status testing  -> runnable in research/backtest/paper contexts only
UI status active   -> runnable only if governance state permits that runtime
```

Governance state should control runtime permission:

```text
research -> can edit and backtest
backtest_qualified -> can run robustness checks
robustness_qualified -> can request paper approval
paper_approved -> can paper trade
live_limited -> can live trade with constrained envelope
live_production -> can live trade under production envelope
suspended -> cannot start new live activity
retired -> read-only
```

Acceptance:

- Creating a strategy creates both operational and governance records.
- Saving a strategy does not bypass lifecycle controls.
- Live execution checks governance state before running a strategy.

---

## 7. Phase 5 - Refactor API Routes

Refactor:

```text
api/routes/strategies.py
```

Keep public route paths stable:

- `GET /api/strategies/`
- `POST /api/strategies/`
- `GET /api/strategies/{strategy_id}`
- `PUT /api/strategies/{strategy_id}`
- `DELETE /api/strategies/{strategy_id}`
- `GET /api/strategies/{strategy_id}/versions`
- `GET /api/strategies/{strategy_id}/versions/{version_id}/code`
- `POST /api/strategies/{strategy_id}/versions/{version_id}/rollback`
- `POST /api/strategies/{strategy_id}/export`

Route responsibilities after refactor:

- Validate request payload.
- Resolve authenticated user, initially still `user_id=1` until auth is connected.
- Call `StrategyCatalogService`.
- Convert service exceptions to HTTP errors.

Response additions:

```python
governance_strategy_id: Optional[str]
lifecycle_state: Optional[str]
code_hash: Optional[str]
parameter_hash: Optional[str]
artifact_root: Optional[str]
strategy_family: Optional[str]
```

Acceptance:

- Existing frontend calls still succeed.
- API response is backward-compatible with current TypeScript interfaces.
- New fields are optional so older UI code is not forced to change immediately.

---

## 8. Phase 6 - Fix Templates and Strategy Code Compatibility

Current UI fallback template references old imports:

```python
from apps.strategy import Strategy
from apps.indicator import sma, ema, rsi
```

Replace with agentic service imports:

```python
from services.strategy import BaseStrategy
from services.indicator import sma, ema, rsi
```

Tasks:

- Update `services/strategy/templates/template_strategy.py`.
- Update hardcoded fallback in `ui/src/components/strategies/create-strategy-dialog.tsx`.
- Fix backend template route to read from `services/strategy/templates/`.
- Add a validation endpoint or service method to compile/load a strategy before save.
- Ensure generated templates subclass `BaseStrategy`.

Acceptance:

- New empty strategy template imports current service modules.
- Saved strategy can be loaded by `StrategyStorage.load_strategy_class`.
- UI-created strategy can be backtested without manual import edits.

---

## 9. Phase 7 - UI Integration

Minimal UI changes first:

- Extend `Strategy` type in `ui/src/lib/api/strategies.ts` with optional fields:
  - `governance_strategy_id`
  - `lifecycle_state`
  - `code_hash`
  - `parameter_hash`
  - `artifact_root`
  - `strategy_family`
- Show lifecycle state on strategy card or editor header.
- Show artifact path and active version in a read-only technical details panel.
- Keep create/save user flow unchanged.

Later UI work:

- Add lifecycle controls under `ui/src/app/(dashboard)/operator/strategies/page.tsx`.
- Add promotion requests and evidence links.
- Add "eligible for paper/live" indicators based on governance state.

Acceptance:

- Existing Strategy Library still works.
- User can create a strategy and lands on `/strategies/{id}`.
- Editor save creates a new version.
- Operator strategy page can eventually read governance state without scraping the legacy table.

---

## 10. Phase 8 - Runtime Enforcement

Add a strategy runtime permission check in the execution paths that start strategy runs.

Likely integration points:

- Simulation/backtest strategy mode.
- Optimization runs.
- Live session strategy attachment/start.
- Any workflow stage that executes user strategy code.

Rules:

- Backtest/research can run `research` and above.
- Paper trading requires `paper_approved`, `live_limited`, or `live_production`.
- Live limited requires `live_limited` or `live_production`.
- Live production requires `live_production`.
- `suspended` and `retired` block new live starts.

Create service:

```text
services/strategy/permissions.py
```

Suggested API:

```python
assert_strategy_allowed(strategy_id: int, context: Literal["backtest", "optimization", "paper", "live"])
```

Acceptance:

- Live execution cannot start a strategy that only has `research` lifecycle state.
- Backtest and optimization remain available for research strategies.
- Error messages tell the user which lifecycle state is required.

---

## 11. Phase 9 - Tests

Add unit tests:

```text
tests/unit/services/strategy/test_catalog_service.py
tests/unit/services/strategy/test_strategy_storage_paths.py
tests/unit/services/strategy/test_strategy_permissions.py
tests/unit/api/routes/test_strategies_routes.py
```

Add integration tests:

```text
tests/integration/strategy/test_strategy_create_update_storage_governance.py
tests/integration/strategy/test_legacy_strategy_migration.py
```

Test cases:

- Create strategy writes:
  - `strategies`
  - `strategy_versions`
  - `strategy.py`
  - `metadata.json`
  - `gov_strategy_registry`
- Update metadata only does not create a new version unless code/params changed.
- Update code creates version `1.0.1`.
- Rename does not break old version loading.
- Missing file returns clear error.
- Migration is idempotent.
- Governance ID format is stable.
- Runtime permission blocks live run for `research` state.

Acceptance:

- Tests use temporary DB and temporary strategy artifact directory.
- Tests do not write to the real `data/database/haruquant.db`.
- Tests do not depend on `haruperi` existing in the developer machine.

---

## 12. Phase 10 - Cutover and Backward Compatibility

Cutover sequence:

1. Add service facade without changing route behavior.
2. Add tests around existing API behavior.
3. Add DB migration and optional fields.
4. Add governance registration on create/update.
5. Run migration script in dry-run mode.
6. Review migration report.
7. Run migration script in apply mode.
8. Enable runtime permission checks in warning mode.
9. Move runtime permission checks to enforcement mode.
10. Add operator UI lifecycle controls.

Backward compatibility rules:

- Do not rename or move existing strategy folders during first cutover.
- Do not remove legacy path resolution until all existing `strategy_versions.file_path` rows are verified.
- Do not remove `strategies.status`; keep it as operational UI state.
- Do not require operator lifecycle UI before normal strategy editing works.

Rollback plan:

- Disable governance registration in service config.
- Keep legacy routes using `StrategyCatalogService` but no-op governance writes.
- Runtime permission checks can be set to warning mode.
- Existing strategies remain readable because legacy tables and file paths are preserved.

---

## 13. Implementation Order Checklist

- [ ] Add `StrategyCatalogService` facade.
- [ ] Add hash helpers for code and parameters.
- [ ] Add stable artifact path helpers while preserving legacy path loading.
- [ ] Add strategy catalog DB migration.
- [ ] Add backfill/migration script with dry-run and apply modes.
- [ ] Refactor `api/routes/strategies.py` to call the catalog service.
- [ ] Fix backend template lookup path.
- [ ] Update UI fallback template imports.
- [ ] Extend TypeScript strategy types with optional governance fields.
- [ ] Add governance registration on strategy create.
- [ ] Add governance hash update on version create.
- [ ] Add strategy runtime permission service.
- [ ] Add warning-mode runtime checks.
- [ ] Add enforcement-mode runtime checks after migration validation.
- [ ] Add operator lifecycle UI integration.
- [ ] Add unit and integration tests.
- [ ] Run migration dry-run against `data/database/haruquant.db`.
- [ ] Review migration report.
- [ ] Run migration apply mode.
- [ ] Verify UI create, edit, save, version history, backtest, optimization, and live session flows.

---

## 14. Done Criteria

The reconciliation is complete when:

- A strategy created from `http://localhost:3000/strategies` writes:
  - an operational DB row in `strategies`
  - a version row in `strategy_versions`
  - physical code under `data/strategies/{username}/...`
  - metadata under `metadata.json`
  - a governance row in `gov_strategy_registry`
- A strategy edit from the UI creates a new version without losing older versions.
- The active version can be loaded by simulation, optimization, and live execution.
- Governance lifecycle state is visible to the backend and eventually to the operator UI.
- Live/paper execution can be blocked by lifecycle policy.
- Existing legacy strategies remain loadable.
- No user strategy source files are stored under `services/strategy/`.
