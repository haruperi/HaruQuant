
([Past chat][1])([Past chat][1])([Past chat][2])([Past chat][3])

# ImplementationPlan.md

## Hybrid C++/Python Quant Trading & Backtesting Platform

**Based on:** `01_software_requirements_specification.md` (edited) and rewritten `02_system_design.md`
**Version:** v2.0 (re-baselined)
**Goal:** 100% implementation coverage of SRS + SDD with task-level traceability.

---

## 0) Plan Rules and Completion Policy

### 0.1 Mandatory Execution Rules

* Keep PRs **small and traceable** (target: 1 primary task per PR).
* Every task has explicit references to:

  * **SRS IDs**
  * **SDD sections**
* Every completed task must include:

  * test file(s),
  * usage file(s),
  * benchmark/log evidence (when applicable),
  * git commit hash.

### 0.2 Checkbox Policy

* Use `[ ]` for not done.
* Replace with `[x]` **only** when Item-Level DoD is fully satisfied.

---

## 1) Definition of Done

### 1.1 Program-Level DoD

* Backtest and live share canonical contracts.
* Risk decisions parity-tested between Python and C++.
* Live system supports reconcile/kill-switch/degraded mode.
* UI shows live health + research outputs from same event/data model.
* CI enforces contracts, tests, lint, and migration integrity.

### 1.2 Item-Level DoD

* Code merged with passing CI (unit + integration + lint/type checks)
* Requirement IDs referenced in PR description
* Tests added/updated with clear assertions (100% coverage for touched scope)
* Usage case added/updated with clear examples (100% coverage for touched scope)
* Reproducibility metadata included where applicable
* Docs updated (SRS/SDD/README/module docs)
* Performance-sensitive paths benchmarked (if touched)
* Git commit recorded

---

## 2) Coverage Strategy (100% SRS + 100% SDD)

## 2.1 SRS Coverage Matrix (Module/Category â†’ Tasks)

| SRS Area           | Coverage Tasks                    |
| ------------------ | --------------------------------- |
| FR-UTIL-001..005   | IP-01, IP-02, IP-03               |
| FR-CONF-001..006   | IP-04, IP-05                      |
| FR-BRIDGE-001..006 | IP-18, IP-19, IP-20, IP-21        |
| FR-TIME-001..005   | IP-06, IP-07, IP-08               |
| FR-DATA-001..006   | IP-09, IP-10, IP-11, IP-12        |
| FR-FEAT-001..005   | IP-13, IP-14                      |
| FR-STRAT-001..006  | IP-22, IP-23, IP-24               |
| FR-PORT-001..005   | IP-25, IP-26                      |
| FR-RISK-001..006   | IP-27, IP-28, IP-29, IP-30        |
| FR-OMS-001..006    | IP-31, IP-32, IP-33               |
| FR-EXEC-001..006   | IP-34, IP-35, IP-36               |
| FR-BT-001..007     | IP-37, IP-38, IP-39, IP-40        |
| FR-RSCH-001..006   | IP-41, IP-42, IP-43               |
| FR-MET-001..005    | IP-44                             |
| FR-LIVE-001..006   | IP-45, IP-46, IP-47               |
| FR-STOR-001..006   | IP-15, IP-16, IP-17, IP-48        |
| FR-API-001..006    | IP-49, IP-50, IP-51               |
| FR-UI-001..006     | IP-52, IP-53, IP-54               |
| FR-OBS-001..006    | IP-55, IP-56, IP-57               |
| FR-TEST-001..006   | IP-58, IP-59                      |
| FR-CICD-001..006   | IP-60, IP-61, IP-62               |
| FR-INT-001..007    | IP-12, IP-34, IP-49, IP-50        |
| FR-DQ-001..003     | IP-10, IP-14, IP-16               |
| FR-SAFE-001..005   | IP-28, IP-29, IP-33, IP-46        |
| NFR-PERF-001..005  | IP-03, IP-21, IP-36, IP-39, IP-62 |
| NFR-REL-001..005   | IP-45, IP-46, IP-47, IP-57        |
| NFR-REC-001..004   | IP-47                             |
| NFR-REP-001..004   | IP-08, IP-17, IP-24, IP-40, IP-43 |
| NFR-SEC-001..006   | IP-05, IP-51, IP-57, IP-63        |
| NFR-OBS-001..004   | IP-01, IP-55, IP-56, IP-57        |
| NFR-SCL-001..003   | IP-12, IP-39, IP-41, IP-64        |
| NFR-MNT-001..004   | IP-00, IP-04, IP-60               |
| NFR-USE-001..003   | IP-52, IP-53, IP-54               |
| NFR-TST-001..004   | IP-58, IP-59, IP-62               |
| NFR-AUD-001..003   | IP-16, IP-30, IP-51               |

## 2.2 SDD Coverage Matrix (Section â†’ Tasks)

| SDD Section                    | Coverage Tasks                           |
| ------------------------------ | ---------------------------------------- |
| Â§1 Objectives               | IP-00                                    |
| Â§2 Principles/Constraints   | IP-00, IP-04, IP-60                      |
| Â§3 Architecture Overview    | IP-12, IP-18, IP-49                      |
| Â§4 Architectural Decisions  | IP-18, IP-31, IP-47                      |
| Â§5 Component Design         | IP-06..IP-57 (core implementation tasks) |
| Â§6 Class Diagrams           | IP-22, IP-25, IP-31, IP-34, IP-65        |
| Â§7 Interface Design         | IP-12, IP-22, IP-49, IP-50               |
| Â§8 Data Model/Persistence   | IP-15, IP-16, IP-17, IP-48               |
| Â§9 State Machines           | IP-31, IP-45, IP-46                      |
| Â§10 User Sequence Flows     | IP-37, IP-45, IP-46, IP-53               |
| Â§11 Security                | IP-05, IP-51, IP-57, IP-63               |
| Â§12 Error/Resilience        | IP-29, IP-33, IP-47                      |
| Â§13 Performance/Scalability | IP-21, IP-39, IP-41, IP-62, IP-64        |
| Â§14 Observability           | IP-55, IP-56, IP-57                      |
| Â§15 Deployment Architecture | IP-60, IP-61, IP-64                      |
| Â§16 Verification Design     | IP-58, IP-59, IP-62                      |
| Â§17 Traceability            | IP-00, IP-61                             |
| Â§18 Migration Guidance      | IP-15, IP-48, IP-61                      |
| Â§19 Appendices/Contracts    | IP-12, IP-22, IP-49, IP-65               |

---

## 3) Work Breakdown Structure (Task-Level Traceability)

> **Completion fields are included under each task** and must be filled when marking `[x]`.

---

### Phase A â€” Baseline, Governance, and Traceability

#### [ ] IP-00 Re-baseline docs and traceability skeleton

* **Sub-tasks**
  * [X] Initialize `ImplementationPlan.md` with version 2.0 baseline.
  * [X] Create traceability matrix structure in `docs/requirements_traceability_matrix.md`.
  * [X] Map all `FR-###` and `NFR-###` IDs to implementation tasks.
  * [X] Define program-level and item-level Definition of Done (DoD).
* **Deliverables**
  * Rewritten `02_system_design.md`
  * Updated implementation baseline and task IDs
  * Coverage matrices scaffold
* **SRS refs:** All FR/NFR families (baseline alignment task)
* **SDD refs:** Â§1â€“Â§19
* **Dependencies:** None
* **Completion evidence**
  * Tests: N/A (docs baseline)
  * Usage files: `docs/architecture.md`
  * Bench/log: N/A
  * Commit: `TBD`

#### [X] IP-01 Unified structured logging (C++ + Python)

* **Sub-tasks**
  * [X] Implement C++ thread-safe async logging using `spdlog`. (FR-CPP-006)
  * [X] Implement Python logger adapter using `structlog`.
  * [X] Normalize severity levels between C++ and Python. (FR-UTIL-001)
  * [X] Add correlation, run, and trace IDs to log schema. (FR-UTIL-002)
  * [X] Implement dynamic filtering by component and severity at runtime. (FR-UTIL-006)
  * [X] Implement automatic sensitive field redaction (API keys, passwords). (FR-UTIL-008)
* **Deliverables**
  * Shared log schema and adapters
  * Correlation/run/trace IDs in all critical logs
* **SRS refs:** FR-UTIL-001..002, FR-UTIL-006, FR-UTIL-008, FR-OBS-001, NFR-OBS-001, FR-CPP-006
* **SDD refs:** Â§5.1, Â§12, Â§14.1
* **Dependencies:** IP-00
* **Completion evidence**
  * Tests: `cpp/tests/unit/test_logger_cpp.cpp`, `py/tests/unit/test_logger_py.py`
  * Usage:  `docs/haruquant/usage/ops/logging.md`
  * Bench/log: `artifacts/logs/structured_log_samples.json`
  * Commit: `TBD`

#### [X] IP-02 Validators/manipulators library

* **Sub-tasks**
  * [X] Implement Pydantic-based schema validators for market/trade/config objects. (FR-UTIL-003)
  * [X] Implement C++ schema validation primitives (JSON-schema or equivalent). (FR-UTIL-003)
  * [X] Implement date/time and timezone normalization helpers. (FR-UTIL-004)
  * [X] Implement platform-independent path handling using `pathlib`. (NFR-PERF-001/Constraint)
* **Deliverables**
  * Schema validators, datetime/string manipulators
* **SRS refs:** FR-UTIL-003..004
* **SDD refs:** Â§5.1.2, Â§7
* **Dependencies:** IP-00
* **Completion evidence**
  * Tests: `py/tests/unit/test_validators.py`, `py/tests/unit/test_time_string_utils.py`
  * Usage: `usage/ops/validation_and_utils.md`
  * Bench/log: N/A
  * Commit: `TBD`

#### [ ] IP-03 C++ math/stat helper kernels

* **Sub-tasks**
  * [ ] Implement rolling stats kernels (SMA, EMA, StdDev, Z-Score). (FR-UTIL-005, FR-STRAT-007)
  * [ ] Implement statistical kernels (Moments, Skew, Kurtosis, Correlation, Rank). (FR-UTIL-005)
  * [ ] Expose kernels to Python via Nanobind buffer protocols. (FR-BRIDGE-001, FR-BRIDGE-002)
* **Deliverables**
  * Rolling stats, zscore, corr, rank kernels exposed to Python
* **SRS refs:** FR-UTIL-005, NFR-PERF-002..005
* **SDD refs:** Â§5.1.2, Â§13
* **Dependencies:** IP-18
* **Completion evidence**
  * Tests: `cpp/tests/unit/test_math_kernels.cpp`, `py/tests/contracts/test_math_bindings.py`
  * Usage: `usage/research/math_stat_kernels.md`
  * Bench/log: `benchmarks/utils/math_kernel_perf.md`
  * Commit: `TBD`

#### [X] IP-04 Configuration profiles + precedence + schema versioning

* **Sub-tasks**
  * [X] Implement TOML-based hierarchical config loader (file + env + runtime overrides). (FR-CONF-001)
  * [X] Support `DEV/BACKTEST/PAPER/LIVE` profile switching. (FR-CONF-002)
  * [X] Implement config validation against versioned schemas with descriptions/safeguards. (FR-CONF-003, FR-CONF-008)
  * [X] Implement runtime reloading of non-critical config (log levels, risk limits). (FR-CONF-007)
* **Deliverables**
  * Config loader with DEV/BACKTEST/PAPER/LIVE policies
* **SRS refs:** FR-CONF-001..003, FR-CONF-005, FR-CONF-007..008, NFR-MNT-001..004
* **SDD refs:** Â§2, Â§3.2, Â§5.3.1
* **Dependencies:** IP-00
* **Completion evidence**
  * Tests: `py/tests/unit/test_config_loader.py`, `py/tests/contracts/test_config_schema_versions.py`
  * Usage: `usage/ops/config_profiles.md`
  * Bench/log: `artifacts/logs/config_validation.log`
  * Commit: `TBD`

#### [X] IP-05 Secrets and privileged live config controls

* **Sub-tasks**
  * [X] Integrate OS-level secret storage (Windows Credential Locker / Keyring). (FR-CONF-009)
  * [X] Implement privileged config mutation path with authorization and audit logging. (FR-CONF-006)
  * [X] Implement configurable DB connection pooling in C++ core. (FR-CONF-010)
* **Deliverables**
  * Secret provider integration
  * Privileged config mutation path with audit
* **SRS refs:** FR-CONF-004, FR-CONF-006, FR-CONF-009..010, NFR-SEC-001..006
* **SDD refs:** Â§11, Â§5.3.5
* **Dependencies:** IP-04, IP-16
* **Completion evidence**
  * Tests: `py/tests/security/test_secret_redaction.py`, `py/tests/integration/test_live_config_authorization.py`
  * Usage: `usage/ops/secrets_and_privileged_changes.md`
  * Bench/log: `artifacts/logs/security/secret_access_audit.json`
  * Commit: `TBD`

---

### Phase B â€” Time, Data Contracts, Ingestion, and Features

#### [X] IP-06 Event/Time engine (ClockService + EventSequencer)

* **Sub-tasks**
  * [X] Implement `ClockService` supporting event-time and processing-time. (FR-TIME-001)
  * [X] Implement `EventSequencer` for deterministic event ordering per-symbol and merged. (FR-TIME-002, FR-CPP-001)
  * [X] Standardize timezone handling with explicit DST policies. (FR-TIME-003)
* **Deliverables**
  * Canonical event-time model and deterministic ordering
* **SRS refs:** FR-TIME-001..003, FR-CPP-001
* **SDD refs:** Â§5.1.1, Â§9
* **Dependencies:** IP-00
* **Completion evidence**
  * Tests: `cpp/tests/test_clock_service.cpp`, `cpp/tests/test_event_sequencer.cpp`
  * Usage: `docs/haruquant/usage/backtest/event_time_model.md`
  * Bench/log: `benchmarks/time/event_ordering_perf.md`
  * Commit: `TBD`

#### [X] IP-07 Session calendar (hours/holidays/timezone/DST)

* **Sub-tasks**
  * [X] Implement `SessionCalendar` with exchange holiday and trading session rules. (FR-TIME-004)
  * [X] Expose trading session restrictions to strategy runtime and live controller. (FR-LIVE-001)
  * [X] Implement symbol metadata mapping (sessions, digits, point value). (FR-DATA-006)
* **Deliverables**
  * SessionCalendar service for all modes
* **SRS refs:** FR-TIME-004, FR-LIVE-001, FR-DATA-006
* **SDD refs:** Â§5.1.1, Â§10.2
* **Dependencies:** IP-06
* **Completion evidence**
  * Tests: `cpp/tests/test_session_calendar.cpp`
  * Usage: `docs/haruquant/usage/live/session_calendar.md`
  * Bench/log: N/A
  * Commit: `TBD`

#### [X] IP-08 ReplayClock and deterministic replay hooks

* **Sub-tasks**
  * [X] Implement `ReplayClock` for deterministic event playback. (FR-TIME-005)
  * [X] Implement deterministic replay hooks for incident reproduction. (FR-BT-007)
  * [X] Support `pause`, `resume`, and `step-by-bar` debugging in replay. (FR-STRAT-010)
* **Deliverables**
  * Deterministic replay clock and event playback control
* **SRS refs:** FR-TIME-005, FR-BT-007, FR-STRAT-010, NFR-REP-001..004
* **SDD refs:** Â§5.1.1, Â§10.1, Â§16
* **Dependencies:** IP-06
* **Completion evidence**
  * Tests: `cpp/tests/test_replay_clock.cpp`, `tests/replay/test_replay_clock_consistency.py`
  * Usage: `docs/haruquant/usage/backtest/replay_clock.md`
  * Bench/log: `artifacts/benchmarks/replay/replay_clock_report.json`
  * Commit: `TBD`

#### [X] IP-09 Data source adapters + normalization pipeline

* **Sub-tasks**
  * [X] Implement MT5 adapter via ZeroMQ (MQL5 EA streaming). (FR-INT-008)
  * [X] Implement Dukascopy historical data adapter. (FR-INT-008)
  * [X] Normalize provider-specific payloads to canonical tick/bar schemas. (FR-DATA-001..002)
  * [X] Implement progress callbacks for long-running ingestion. (FR-DATA-014)
* **Deliverables**
  * MT5/Dukascopy adapters
  * Canonical tick/bar normalization
* **SRS refs:** FR-DATA-001..002, FR-DATA-014, FR-INT-001..003, FR-INT-008
* **SDD refs:** Â§5.1.2, Â§7
* **Dependencies:** IP-06, IP-12
* **Completion evidence**
  * Tests: `tests/integration/test_data_adapter_normalization.py`, `tests/contracts/test_tick_bar_contract.py`
  * Usage: `docs/haruquant/usage/ops/ingestion_and_normalization.md`, `tests/usage/utils/usage_mt5_zmq_adapter.py`
  * Bench/log: `artifacts/benchmarks/ingestion/ingestion_throughput.md`
  * Commit: `TBD`

#### [X] IP-10 Data quality guardrails (missing/duplicate/out-of-order)

* **Sub-tasks**
  * [X] Implement price sanity, gap detection, and spike filtering checks. (FR-DATA-011, FR-DQ-001)
  * [X] Implement detection of zero-volume bars and spread widening alerts. (FR-DATA-011)
  * [X] Implement DQ remediation flagging and reporting. (FR-DATA-003, FR-DQ-002)
* **Deliverables**
  * DQ detection + severity + remediation flags
* **SRS refs:** FR-DATA-003, FR-DATA-011, FR-DQ-001..003
* **SDD refs:** Â§5.1.2, Â§8
* **Dependencies:** IP-09
* **Completion evidence**
  * Tests: `tests/integration/test_data_quality_alerts.py`, `tests/unit/apps/utils/test_data_validator_pipeline.py`
  * Usage: `docs/haruquant/usage/ops/data_quality_runbook.md`
  * Bench/log: `artifacts/evidence/data_quality/sample_report.json`
  * Commit: `TBD`

#### [X] IP-11 Multi-symbol synchronized ingestion

* **Sub-tasks**
  * [X] Implement synchronized multi-symbol ingestion pipeline. (FR-DATA-004)
  * [X] Implement memory-mapped (mmap) lazy loading for historical data. (FR-CPP-002)
  * [X] Support data compaction for incremental downloads. (FR-DATA-013)
* **Deliverables**
  * Cross-symbol sync and ordering policy
* **SRS refs:** FR-DATA-004, FR-DATA-013, FR-CPP-002, NFR-SCL-001..003
* **SDD refs:** Â§3, Â§5.1.2, Â§13
* **Dependencies:** IP-06, IP-09
* **Completion evidence**
  * Tests: `tests/integration/test_multisymbol_sync.py`
  * Usage: `docs/haruquant/usage/ops/multisymbol_ingestion.md`
  * Bench/log: `artifacts/benchmarks/ingestion/multisymbol_sync_perf.md`
  * Commit: `TBD`

#### [X] IP-12 Message contracts and schema registry (events/API/storage)

* **Sub-tasks**
  * [X] Initialize versioned schema registry with backward compatibility checks. (FR-INT-005, FR-API-003)
  * [X] Define canonical schemas for Ticks, Bars, Orders, Fills, and Positions. (SRS §6.1)
  * [X] Implement schema validation for run manifests and reports. (FR-STOR-004, FR-INT-007)
* **Deliverables**
  * Versioned schema registry + compatibility checks
* **SRS refs:** FR-INT-004..007, FR-API-003, FR-STOR-004, SRS Â§6.1
* **SDD refs:** Â§7, Â§8, Â§19
* **Dependencies:** IP-00
* **Completion evidence**
  * Tests: `tests/contracts/test_schema_registry.py`, `tests/migrations/test_schema_backward_compat.py`
  * Usage: `docs/haruquant/usage/ops/schema_registry.md`
  * Bench/log: N/A
  * Commit: `TBD`

#### [X] IP-13 Feature pipeline (batch + streaming)

* **Sub-tasks**
  * [X] Implement technical indicator library (Trend, Momentum, Volatility, Volume). (FR-STRAT-007)
  * [X] Implement batch and incremental (streaming) feature computation. (FR-FEAT-001, FR-FEAT-003)
  * [X] Implement feature computation graph inspection. (FR-FEAT-005)
* **Deliverables**
  * Feature graph engine + versioned pipeline
* **SRS refs:** FR-FEAT-001..003, FR-FEAT-005, FR-STRAT-007
* **SDD refs:** Â§5.1.2, Â§8
* **Dependencies:** IP-09, IP-12
* **Completion evidence**
  * Tests: `tests/integration/test_feature_pipeline_stream_batch.py`
  * Usage: `docs/haruquant/usage/research/feature_pipeline.md`, `tests/usage/utils/usage_feature_pipeline.py`
  * Bench/log: `benchmarks/feature/feature_compute_perf.md`
  * Commit: `TBD`

#### [X] IP-14 Leakage prevention + split policy enforcement

* **Sub-tasks**
  * [X] Implement Point-in-Time (PIT) correctness guards in core engine. (FR-STRAT-009, FR-FEAT-004)
  * [X] Implement train/validation/test split enforcement policy. (FR-RSCH-005)
  * [X] Implement sensitive data masking in research artifacts. (FR-UTIL-008)
* **Deliverables**
  * No-lookahead guards and split validators
* **SRS refs:** FR-FEAT-004, FR-RSCH-005, FR-STRAT-009, FR-DQ-001, FR-UTIL-008
* **SDD refs:** Â§5.1.2, Â§16
* **Dependencies:** IP-13, IP-41
* **Completion evidence**
  * Tests: `tests/contracts/test_no_lookahead.py`, `tests/integration/test_split_enforcement.py`
  * Usage: `docs/haruquant/usage/research/leakage_prevention.md`, `tests/usage/utils/usage_leakage_prevention.py`
  * Bench/log: N/A
  * Commit: `TBD`

---

### Phase C â€” Storage, Lineage, and Audit Foundations

#### [ ] IP-15 Storage schema + migrations baseline

* **Sub-tasks**
  * [ ] Initialize SQLAlchemy models and Alembic migrations. (FR-STOR-009)
  * [ ] Define schemas for: `sessions`, `backtests`, `users`, `live_trades`, `paper_trades`, `account_snapshots`. (FR-STOR-012)
  * [ ] Implement Write-Ahead Logging (WAL) for critical state changes. (FR-STOR-010)
  * [ ] Implement state reconstruction from WAL + Snapshot upon recovery. (FR-STOR-011)
* **Deliverables**
  * SQL schema for manifests/orders/fills/positions/risk/audit
  * migration scripts
* **SRS refs:** FR-STOR-001, FR-STOR-004, FR-STOR-006, FR-STOR-009..012
* **SDD refs:** Â§8, Â§18
* **Dependencies:** IP-12
* **Completion evidence**
  * Tests: `py/tests/migrations/test_initial_schema.py`, `py/tests/migrations/test_migration_integrity.py`
  * Usage: `usage/ops/storage_migrations.md`
  * Bench/log: N/A
  * Commit: `TBD`

#### [ ] IP-16 Append-only journals + immutable audit trail

* **Sub-tasks**
  * [ ] Implement append-only journal writers for orders and fills. (FR-STOR-002)
  * [ ] Implement `AuditService` for risk decisions, overrides, and security events. (FR-RISK-006, NFR-AUD-001)
  * [ ] Enforce immutability and record actor identity, timestamp, and reason code. (NFR-AUD-002)
  * [ ] Implement 90-day retention for access logs and permanent for trade audit. (FR-STOR-008)
* **Deliverables**
  * order/fill/risk/audit append-only writes
* **SRS refs:** FR-STOR-002, FR-STOR-008, FR-RISK-006, NFR-AUD-001..003, FR-SAFE-004
* **SDD refs:** Â§8, Â§11, Â§12
* **Dependencies:** IP-15
* **Completion evidence**
  * Tests: `py/tests/integration/test_append_only_journal.py`, `py/tests/integration/test_audit_integrity.py`
  * Usage: `usage/ops/audit_journal_queries.md`
  * Bench/log: `artifacts/logs/audit/sample_chain.json`
  * Commit: `TBD`

#### [ ] IP-17 Lineage catalog + run manifest binding

* **Sub-tasks**
  * [ ] Implement `RunManifestService` to capture strategy version, config hash, data snapshot, and code commit. (FR-STOR-003, SRS Â§6.1)
  * [ ] Link every output artifact (trade log, metrics) to a unique Run Manifest ID. (FR-STOR-003)
  * [ ] Implement `reproduce(run_id)` command scaffold to retrieve config/data/seed. (FR-BT-012)
* **Deliverables**
  * lineage IDs attached to outputs/reports/artifacts
* **SRS refs:** FR-STOR-003, FR-CONF-005, FR-BT-012, NFR-REP-003..004, SRS Â§6.1
* **SDD refs:** Â§8, Â§10.4
* **Dependencies:** IP-15, IP-41
* **Completion evidence**
  * Tests: `py/tests/integration/test_lineage_linking.py`
  * Usage: `usage/research/lineage_and_manifest.md`
  * Bench/log: `artifacts/logs/lineage/lineage_examples.json`
  * Commit: `TBD`

---

### Phase D â€” Interop Bridge (Nanobind)

#### [X] IP-18 Nanobind module skeleton and lifecycle

* **Sub-tasks**
  * [X] Initialize binding modules: `_event`, `_data`, `_risk`, `_oms`, `_execution`, `_backtest`, `_metrics`. (FR-BRIDGE-001)
  * [X] Implement lifecycle hooks for initialization, teardown, and health checks. (FR-BRIDGE-006)
  * [X] Assert **Zero Memory Leaks** on shutdown, verified by ASan in CI. (NFR-REL-007)
* **Deliverables**
  * `_event`, `_data`, `_risk`, `_oms`, `_execution`, `_backtest`, `_metrics` modules
* **SRS refs:** FR-BRIDGE-001, FR-BRIDGE-006, NFR-REL-007
* **SDD refs:** Â§3, Â§5.2
* **Dependencies:** IP-00
* **Completion evidence**
  * Tests: `tests/contracts/test_nanobind_module_load.py`, `tests/contracts/asan_bridge_lifecycle_check.py`
  * Usage: `docs/haruquant/usage/dev/nanobind_module_layout.md`
  * Bench/log: `.github/workflows/asan_leak_check.yml` (ASan leak gate)
  * Commit: `TBD`

#### [X] IP-19 Ownership contracts and object lifetime safety

* **Sub-tasks**
  * [X] Define C++/Python ownership policies (C++ owned, Python view, shared ownership). (FR-BRIDGE-003)
  * [X] Strictly enforce RAII resource management and smart pointer exposure. (FR-CPP-003)
  * [X] Guarantee zero-copy ownership contracts for heavy payloads. (FR-CPP-004)
* **Deliverables**
  * C++ owned/Python view and shared-ownership policies
* **SRS refs:** FR-BRIDGE-003, FR-CPP-003, FR-CPP-004
* **SDD refs:** Â§5.2.2
* **Dependencies:** IP-18
* **Completion evidence**
  * Tests: `tests/contracts/test_bridge_lifetime.py`
  * Usage: `docs/haruquant/usage/dev/bridge_ownership_rules.md`
  * Bench/log: `artifacts/logs/bridge/lifetime_validation.log`
  * Commit: `TBD`

#### [x] IP-20 Exception mapping Cpp +  Python

* **Sub-tasks**
  * [X] Implement `Unified Exception Hierarchy` mapping C++ to typed Python exceptions. (FR-UTIL-007, FR-BRIDGE-004)
  * [X] Implement crash handling for segfaults/panics with log flushing and state persistence. (FR-UTIL-009)
* **Deliverables**
  * typed exceptions and propagation for all engine boundaries
* **SRS refs:** FR-UTIL-007, FR-UTIL-009, FR-BRIDGE-004
* **SDD refs:** Â§5.2.3, Â§12
* **Dependencies:** IP-18
* **Completion evidence**
  * Tests: `tests/contracts/test_exception_mapping.py`, `tests/unit/apps/utils/test_errors.py`, `tests/unit/apps/utils/test_crash_handler.py`
  * Usage: `docs/haruquant/usage/dev/exception_mapping.md`, `docs/haruquant/usage/ops/crash_handling.md`
  * Bench/log: N/A
  * Commit: `TBD`

#### [x] IP-21 Zero-copy path + serialization fallback

* **Sub-tasks**
  * [X] Implement zero-copy buffer views for contiguous numeric layouts. (FR-BRIDGE-002)
  * [X] Optimize bridge call latency to < 1Î¼s. (NFR-PERF-010)
  * [X] Implement zero-copy ownership handover via Nanobind. (FR-CPP-004)
  * [X] Implement Arrow/Protobuf fallback path for incompatible data layouts. (FR-BRIDGE-005)
* **Deliverables**
  * zero-copy buffers for compatible layouts
  * Arrow/Protobuf fallback for incompatible/cross-process flows
* **SRS refs:** FR-BRIDGE-002, FR-BRIDGE-005, NFR-PERF-005, NFR-PERF-010, FR-CPP-004
* **SDD refs:** Â§5.2.4, Â§13
* **Dependencies:** IP-18, IP-12
* **Completion evidence**
  * Tests: `tests/contracts/test_zero_copy.py`, `tests/integration/test_fallback_serialization.py`
  * Usage: `docs/haruquant/usage/dev/zero_copy_and_fallback.md`
  * Bench/log: `benchmarks/bridge/zero_copy_vs_fallback.md`
  * Commit: `TBD`

---

### Phase E â€” Strategy Runtime, Portfolio, Risk, OMS, Execution

#### [x] IP-22 Strategy SDK lifecycle and canonical event contract

* **Sub-tasks**
  * [X] Implement `BaseStrategy` hooks with `on_init`, `on_bar`, `on_tick`, `on_trade`, `on_order_update`, `on_timer`, `on_shutdown`. (FR-STRAT-002)
  * [X] Define `StrategyEvent` contract for all operating modes. (FR-STRAT-001)
  * [X] Implement strategy isolation and per-strategy state containers. (FR-STRAT-003)
* **Deliverables**
  * `BaseStrategy` hooks
  * `StrategyEvent` contract used in backtest + live
* **SRS refs:** FR-STRAT-001..003, FR-STRAT-006
* **SDD refs:** Â§5.3.2, Â§6, Â§7
* **Dependencies:** IP-12, IP-18
* **Completion evidence**
  * Tests: `tests/unit/apps/strategy/test_base.py`, `tests/contracts/test_strategy_event_contract.py`
  * Usage: `docs/haruquant/usage/strategy/create_strategy.md`
  * Bench/log: N/A
  * Commit: `TBD`

#### [x] IP-23 Strategy adapter and signal router

* **Sub-tasks**
  * [X] Implement `StrategyAdapter` to bridge Python logic with C++ engine. (FR-STRAT-004)
  * [X] Define canonical `SignalIntent` (Action, Qty, OrderType, Price, TIF). (FR-OMS-001, SDD Â§7.2)
  * [X] Implement signal explainability metadata emission for audit trail. (FR-STRAT-006)
* **Deliverables**
  * adapter between Python strategies and C++ engines
  * canonical `SignalIntent`
* **SRS refs:** FR-STRAT-004, FR-STRAT-001, FR-STRAT-006, FR-OMS-001
* **SDD refs:** Â§5.3.2, Â§7
* **Dependencies:** IP-22, IP-21
* **Completion evidence**
  * Tests: `tests/integration/test_strategy_adapter_flow.py`
  * Usage: `docs/haruquant/usage/strategy/signal_intent_contract.md`
  * Bench/log: `benchmarks/strategy/adapter_latency.md`
  * Commit: `TBD`

#### [x] IP-24 Strategy artifact versioning + reproducibility metadata

* **Sub-tasks**
  * [X] Bind strategy version and model artifacts to run manifests. (FR-STRAT-005, FR-CONF-005)
  * [X] Implement stability scoring and sensitivity analysis metadata. (FR-RSCH-004)
* **Deliverables**
  * strategy/model versions embedded in run outputs
* **SRS refs:** FR-STRAT-005, FR-CONF-005, FR-RSCH-004, NFR-REP-001..004
* **SDD refs:** Â§5.3.2, Â§8, Â§10.4
* **Dependencies:** IP-17, IP-23
* **Completion evidence**
  * Tests: `tests/unit/apps/strategy/test_strategy_version_binding.py`
  * Usage: `docs/haruquant/usage/research/reproducible_strategy_runs.md`, `tests/usage/strategy/02_reproducible_manifest.py`
  * Bench/log: `artifacts/logs/repro/sample_manifest.json`
  * Commit: `TBD`

#### [X] IP-25 Portfolio state engine

* **Sub-tasks**
  * [X] Implement `PortfolioState` tracking capital, margin, realized/unrealized PnL. (FR-PORT-005)
  * [X] Support concurrent multi-strategy, multi-symbol portfolio state. (FR-PORT-001)
* **Deliverables**
  * canonical portfolio/account/position state updates
* **SRS refs:** FR-PORT-001, FR-PORT-005
* **SDD refs:** Â§5.1.3, Â§6
* **Dependencies:** IP-23, IP-31
* **Completion evidence**
  * Tests: `cpp/tests/test_portfolio_state.cpp`, `tests/integration/test_portfolio_updates.py`
  * Usage: `docs/haruquant/usage/portfolio/portfolio_state.md`
  * Bench/log: `benchmarks/portfolio/state_update_perf.md`
  * Commit: `TBD`

#### [X] IP-26 Allocation/rebalance/exposure models

* **Sub-tasks**
  * [X] Implement allocation models: static weights, risk parity, custom. (FR-PORT-002)
  * [X] Implement portfolio-level exposure constraints (asset, symbol, strategy). (FR-PORT-003)
  * [X] Implement scheduled and event-triggered rebalancing policies. (FR-PORT-004)
* **Deliverables**
  * static/custom allocators + rebalance triggers + exposure caps
* **SRS refs:** FR-PORT-002..004, FR-RISK-004
* **SDD refs:** Â§5.1.3, Â§5.1.4
* **Dependencies:** IP-25
* **Completion evidence**
  * Tests: `cpp/tests/test_allocation_models.cpp`, `cpp/tests/test_rebalance_policies.cpp`, `tests/unit/test_allocation_models.py`, `tests/integration/test_rebalance_policies.py`
  * Usage: `docs/haruquant/usage/portfolio/allocation_and_rebalance.md`
  * Bench/log: `benchmarks/portfolio/rebalance_cost.md`
  * Commit: `TBD`

#### [X] IP-27 Risk pre-trade checks (policy engine)

* **Sub-tasks**
  * [X] Implement pre-trade checks: size, margin, max exposure, policy. (FR-RISK-001, FR-SAFE-001)
  * [X] Implement position sizing methods: fixed, volatility-based, Kelly. (FR-RISK-004)
  * [X] Support mode-specific risk rules (backtest vs live). (FR-RISK-005)
* **Deliverables**
  * [X] margin/size/exposure checks with policy codes
* **SRS refs:** FR-RISK-001, FR-RISK-004..005, FR-SAFE-001
* **SDD refs:** Â§5.1.4, Â§12
* **Dependencies:** IP-25, IP-26
* **Completion evidence**
  * Tests: `cpp/tests/test_risk_engine.cpp`, `tests/contracts/test_risk_bindings.py`
  * Usage: `docs/haruquant/usage/risk/pretrade_risk.md`, `tests/usage/risk/09_cpp_risk_policy.py`
  * Bench/log: `TBD`
  * Commit: `TBD`

#### [X] IP-28 In-trade monitoring + circuit breakers

* **Sub-tasks**
  * [X] Implement in-trade monitoring for drawdown and volatility spikes. (FR-RISK-002)
  * [X] Implement strategy-level and global circuit breakers. (FR-RISK-003, FR-RISK-009)
  * [X] Integrate HMM-based regime detection for dynamic risk inputs. (FR-RISK-010)
* **Deliverables**
  * [X] drawdown/volatility monitors and auto-protect logic
* **SRS refs:** FR-RISK-002..003, FR-RISK-009..010, FR-SAFE-002..003
* **SDD refs:** Â§5.1.4, Â§12, Â§14
* **Dependencies:** IP-27
* **Completion evidence**
  * Tests: `cpp/tests/test_risk_engine.cpp`, `tests/contracts/test_risk_bindings.py`
  * Usage: `docs/haruquant/usage/risk/intrade_controls.md`, `tests/usage/risk/10_intraday_circuit_breaker.py`
  * Bench/log: `TBD`
  * Commit: `TBD`

#### [X] IP-29 Kill-switch controller and safe-mode transitions

* **Sub-tasks**
  * [X] Implement global kill-switch functionality. (FR-RISK-003, FR-LIVE-009)
  * [X] Define safe-mode state machine transitions (halt trading, reduce exposure). (FR-SAFE-002..005)
  * [X] Implement emergency shutdown triggerable via UI and API. (FR-LIVE-009)
* **Deliverables**
  * [X] global/strategy kill-switch
  * [X] safe-mode state transitions
* **SRS refs:** FR-RISK-003, FR-LIVE-009, FR-SAFE-002..005
* **SDD refs:** Â§9.2, Â§10.3, Â§14
* **Dependencies:** IP-28, IP-45
* **Completion evidence**
  * Tests: `cpp/tests/test_risk_engine.cpp`, `tests/contracts/test_risk_bindings.py`
  * Usage: `docs/haruquant/usage/live/killswitch_runbook.md`, `tests/usage/risk/11_killswitch_state_machine.py`
  * Bench/log: `TBD`
  * Commit: `TBD`

#### [X] IP-30 Risk audit/override workflow

* **Sub-tasks**
  * [X] Implement role-bound risk override flow with reason logging. (FR-RISK-006, FR-SAFE-004)
  * [X] Implement secure authorization for live risk limit updates. (FR-CONF-006)
* **Deliverables**
  * [X] role-bound override flow with immutable reason logging
* **SRS refs:** FR-RISK-006, FR-CONF-006, NFR-AUD-001..003, FR-SAFE-004
* **SDD refs:** Â§11, Â§12
* **Dependencies:** IP-16, IP-51
* **Completion evidence**
  * Tests: `tests/security/test_risk_override_audit.py`
  * Usage: `docs/haruquant/usage/risk/risk_override_policy.md`
  * Bench/log: `TBD`
  * Commit: `TBD`

#### [X] IP-31 OMS order state machine + idempotency

* **Sub-tasks**
  * [X] Implement order state machine (NEW -> ACCEPTED -> FILLED/CANCELED). (FR-OMS-001, SDD Â§9.1)
  * [X] Support Market, Limit, Stop, Stop-Limit, Trailing-Stop order types. (FR-OMS-002)
  * [X] Implement gap handling for matching engine (executing at gap price). (FR-CPP-005)
  * [X] Implement idempotent submission via client order IDs. (FR-OMS-003)
* **Deliverables**
  * `NEWâ†’...â†’terminal` transitions + duplicate guard
* **SRS refs:** FR-OMS-001..004, FR-CPP-005
* **SDD refs:** Â§5.1.5, Â§9.1
* **Dependencies:** IP-23
* **Completion evidence**
  * Tests: `cpp/tests/test_sim_oms_state_machine.cpp`, `cpp/tests/test_sim_pending_orders.cpp`, `cpp/tests/test_sim_pending_trigger_monitor.cpp`
  * Usage: `docs/haruquant/usage/trade/oms_state_machine_idempotency.md`, `tests/usage/trade/oms_state_machine_idempotency_cpp.py`
  * Bench/log: `TBD`
  * Commit: `TBD`

#### [X] IP-32 Position book and broker reconciliation hooks

* **Sub-tasks**
  * [X] Implement `PositionBook` updating from fills and account events. (FR-OMS-004)
  * [X] Support Netting and Hedging modes per symbol/account. (FR-OMS-007)
  * [X] Implement periodic and on-reconnect reconciliation hooks. (FR-OMS-005)
* **Deliverables**
  * position updates from fills + reconcile entry points
* **SRS refs:** FR-OMS-004..005, FR-OMS-007
* **SDD refs:** Â§5.1.5, Â§10.2, Â§10.3
* **Dependencies:** IP-31, IP-34
* **Completion evidence**
  * Tests: `cpp/tests/test_position_book.cpp`, `tests/integration/test_reconcile_hooks.py`
  * Usage: `docs/haruquant/usage/live/position_book_and_reconcile.md`
  * Bench/log: N/A
  * Commit: `TBD`

#### [X] IP-33 Reconciliation mismatch handling and escalation

* **Sub-tasks**
  * [X] Implement mismatch detection and incident report generation. (FR-OMS-006)
  * [X] Implement split reconciliation policies (Auto vs Manual). (FR-LIVE-011)
  * [X] Enforce blocking policy on major discrepancies. (FR-SAFE-005)
* **Deliverables**
  * mismatch detection, incident report, blocking policy
* **SRS refs:** FR-OMS-006, FR-LIVE-005..006, FR-LIVE-011, FR-SAFE-005
* **SDD refs:** Â§10.3, Â§12, Â§14
* **Dependencies:** IP-32, IP-46
* **Completion evidence**
  * Tests: `cpp/tests/test_reconcile_escalation.cpp`, `tests/e2e/test_reconcile_mismatch_blocking.py`
  * Usage: `docs/haruquant/usage/live/reconcile_escalation.md`
  * Bench/log: `artifacts/logs/live/reconcile_discrepancy_report.json`
  * Commit: `TBD`

#### [X] IP-34 Broker adapter abstraction + mock broker

* **Sub-tasks**
  * [X] Define standardized `BrokerAdapter` interface (connect, submit, fetch). (FR-INT-001)
  * [X] Implement `MockBroker` with deterministic fill behavior for backtesting. (FR-BT-004)
  * [X] Implement `Paper Trading Engine` for execution simulation using live data. (FR-EXEC-008)
* **Deliverables**
  * unified broker interface + deterministic mock broker
* **SRS refs:** FR-INT-001..003, FR-EXEC-001, FR-EXEC-008, FR-BT-004
* **SDD refs:** Â§5.1.6, Â§7
* **Dependencies:** IP-12
* **Completion evidence**
  * Tests: `cpp/tests/test_broker_adapter_interface.cpp`, `tests/integration/test_mock_broker.py`
  * Usage: `docs/haruquant/usage/live/broker_adapter.md`
  * Bench/log: N/A
  * Commit: `TBD`

#### [X] IP-35 Execution router + retry + bounded failure policies

* **Sub-tasks**
  * [X] Implement execution routing to adapters with final pre-send risk checks. (FR-EXEC-001, FR-EXEC-006)
  * [X] Implement retry policies with bounded attempts and escalation. (FR-EXEC-004)
  * [X] Implement `Order Spam Prevention` rate limiting. (FR-LIVE-008)
* **Deliverables**
  * routing and retry with escalation policies
* **SRS refs:** FR-EXEC-001, FR-EXEC-004, FR-EXEC-006, FR-LIVE-008, FR-SAFE-004
* **SDD refs:** Â§5.1.6, Â§12
* **Dependencies:** IP-34, IP-31
* **Completion evidence**
  * Tests: `cpp/tests/test_execution_retry.cpp`, `tests/integration/test_execution_escalation.py`
  * Usage: `docs/haruquant/usage/live/execution_retry_policy.md`
  * Bench/log: N/A
  * Commit: `TBD`

#### [X] IP-36 TWAP/VWAP + partial fills + latency/slippage metrics

* **Sub-tasks**
  * [X] Implement basic execution algorithms (TWAP, VWAP). (FR-EXEC-002)
  * [X] Model and track slippage, spread, and partial fills. (FR-EXEC-003)
  * [X] Track p99 latency from intent to dispatch and ack. (FR-EXEC-005, NFR-PERF-004)
* **Deliverables**
  * TWAP/VWAP algorithms
  * partial fill handling
  * latency/slippage tracking
* **SRS refs:** FR-EXEC-002..003, FR-EXEC-005..006, NFR-PERF-004
* **SDD refs:** Â§5.1.6, Â§10.2, Â§13
* **Dependencies:** IP-35, IP-44
* **Completion evidence**
  * Tests: `cpp/tests/test_twap_vwap.cpp`, `tests/integration/test_partial_fills.py`
  * Usage: `docs/haruquant/usage/live/execution_quality.md`
  * Bench/log: N/A
  * Commit: `TBD`

---

### Phase F â€” Backtesting, Research, Metrics

#### [X] IP-37 Event-driven backtest engine

* **Sub-tasks**
  * [X] Implement deterministic event runner with strategy/risk/OMS path. (FR-BT-001)
  * [X] Support tick-level and bar-level simulations. (FR-BT-002)
  * [X] Implement `on_bar`, `on_tick`, `on_trade` lifecycle events. (FR-STRAT-002)
* **Deliverables**
  * deterministic event runner with strategy/risk/OMS path
* **SRS refs:** FR-BT-001..002, FR-BT-006, FR-STRAT-002
* **SDD refs:** Â§5.1.7, Â§10.1
* **Dependencies:** IP-22, IP-27, IP-31
* **Completion evidence**
  * Tests: `cpp/tests/test_backtest_event_runner.cpp`, `tests/e2e/test_backtest_event_path.py`
  * Usage: `docs/haruquant/usage/backtest/event_runner.md`
  * Bench/log: N/A
  * Commit: `TBD`

#### [X] IP-38 Vectorized backtest engine

* **Sub-tasks**
  * [X] Implement vectorized simulation path for high-throughput research. (FR-BT-001)
  * [X] Optimize throughput to 1M orders in 70-100ms. (NFR-PERF-006)
  * [X] Implement parity checks between event-driven and vectorized engines. (FR-TEST-004)
* **Deliverables**
  * vectorized simulation path and parity checks
* **SRS refs:** FR-BT-001, NFR-PERF-006, FR-TEST-004
* **SDD refs:** Â§5.1.7, Â§13
* **Dependencies:** IP-37
* **Completion evidence**
  * Tests: `cpp/tests/test_backtest_vectorized.cpp`, `tests/parity/test_event_vs_vectorized_parity.py`
  * Usage: `docs/haruquant/usage/backtest/vectorized_runner.md`
  * Bench/log: N/A
  * Commit: `TBD`

#### [ ] IP-39 Fill simulator + transaction cost model

* **Sub-tasks**
  * [ ] Implement realistic fill simulation (spread, slippage, partials). (FR-BT-003..004)
  * [ ] Handle price gap scenarios (executing at gap price, not stop level). (FR-CPP-005)
  * [ ] Implement transaction cost model (commission [fixed/%, tiered], swap). (FR-BT-003)
  * [ ] Use seeded RNG for all stochastic simulation processes. (FR-BT-018)
* **Deliverables**
  * spread/commission/slippage/financing simulation
* **SRS refs:** FR-BT-003..004, FR-BT-018, NFR-PERF-001..003, FR-CPP-005
* **SDD refs:** Â§5.1.7, Â§13
* **Dependencies:** IP-37
* **Completion evidence**
  * Tests: `cpp/tests/unit/test_fill_simulator.cpp`, `py/tests/integration/test_cost_model.py`
  * Usage: `usage/backtest/cost_and_fill_models.md`
  * Bench/log: `benchmarks/backtest/cost_model_overhead.md`
  * Commit: `TBD`

#### [ ] IP-40 Replay certification + WFO/WFM orchestration

* **Sub-tasks**
  * [ ] Implement replay verifier comparing trade sequences across runs. (FR-BT-007, FR-BT-011)
  * [ ] Implement WFO and Matrix evaluation orchestrator. (FR-BT-005)
  * [ ] Generate **Edge Detector** reports (skill vs luck, p-values). (FR-BT-017)
* **Deliverables**
  * replay verifier
  * WFO/WFM runner integration
* **SRS refs:** FR-BT-005, FR-BT-007, FR-BT-011, FR-BT-017, NFR-REP-001..004
* **SDD refs:** Â§5.1.7, Â§10.4, Â§16
* **Dependencies:** IP-37, IP-42
* **Completion evidence**
  * Tests: `py/tests/replay/test_replay_certification.py`, `py/tests/integration/test_wfo_wfm.py`
  * Usage: `usage/research/wfo_wfm.md`
  * Bench/log: `artifacts/benchmarks/replay_wfo_wfm_report.json`
  * Commit: `TBD`

#### [ ] IP-41 Experiment manager and registry

* **Sub-tasks**
  * [ ] Implement searchable experiment registry by strategy, symbol, period. (FR-RSCH-006)
  * [ ] Support symbol classification (Asset class, Volatility regime). (FR-RSCH-007)
  * [ ] Implement seasonal pattern analysis (Day of week, Holiday impacts). (FR-RSCH-009)
* **Deliverables**
  * experiment metadata and searchable registry
* **SRS refs:** FR-RSCH-006, FR-RSCH-007, FR-RSCH-009, FR-STOR-003
* **SDD refs:** Â§5.3.3, Â§8
* **Dependencies:** IP-17
* **Completion evidence**
  * Tests: `py/tests/unit/test_experiment_manager.py`
  * Usage: `usage/research/experiment_registry.md`
  * Bench/log: N/A
  * Commit: `TBD`

#### [ ] IP-42 Optimization runners (grid/random/genetic/Bayesian)

* **Sub-tasks**

  * [ ] Implement parallel optimization runners (Grid, Bayesian, etc.). (FR-RSCH-001, FR-RSCH-002)
  * [ ] Integrate Ray-based distributed workers for scaling. (FR-BT-009, FR-BT-013)
  * [ ] Implement worker health monitoring and auto-restart. (FR-BT-016)
* **Deliverables**

  * Optimization algorithms and distributed execution
  * optimization orchestration with parallel execution policies
* **SRS refs:** FR-RSCH-001..002, NFR-SCL-001..003
* **SDD refs:** Â§5.3.3, Â§13
* **Dependencies:** IP-41
* **Completion evidence**

  * Tests: `py/tests/unit/test_optimizers.py`, `py/tests/integration/test_parallel_optimization.py`
  * Usage: `usage/research/optimization_runner.md`
  * Bench/log: `benchmarks/research/optimizer_scaling.md`
  * Commit: `TBD`

#### [ ] IP-43 Monte Carlo + sensitivity analysis

* **Deliverables**

  * MC perturbation and sensitivity modules
* **SRS refs:** FR-RSCH-003..005, NFR-REP-004
* **SDD refs:** Â§5.3.3, Â§16
* **Dependencies:** IP-41
* **Completion evidence**

  * Tests: `py/tests/unit/test_monte_carlo.py`, `py/tests/unit/test_sensitivity.py`
  * Usage: `usage/research/monte_carlo_sensitivity.md`
  * Bench/log: `artifacts/benchmarks/research/mc_sensitivity_report.json`
  * Commit: `TBD`

#### [ ] IP-44 Metrics engine and benchmark comparison

* **Deliverables**

  * return/risk/efficiency metrics
  * benchmark-relative metrics
* **SRS refs:** FR-MET-001..005
* **SDD refs:** Â§5.1.8, Â§8
* **Dependencies:** IP-37
* **Completion evidence**

  * Tests: `cpp/tests/unit/test_metrics_engine.cpp`, `py/tests/integration/test_metrics_benchmarking.py`
  * Usage: `usage/backtest/metrics_reference.md`
  * Bench/log: `benchmarks/metrics/compute_cost.md`
  * Commit: `TBD`

---

### Phase G â€” Live Control Plane, Recovery, and Safety

#### [ ] IP-45 Live session controller and readiness gates

* **Sub-tasks**
  * [ ] Implement `LiveSessionController` with startup readiness gates. (FR-LIVE-002)
  * [ ] Implement heartbeat monitoring and service readiness checks. (FR-LIVE-002, FR-OBS-005)
  * [ ] Implement graceful shutdown and emergency stop policies. (FR-LIVE-003, FR-LIVE-009)
* **Deliverables**
  * live session controller and readiness policy
* **SRS refs:** FR-LIVE-001..003, FR-LIVE-009, FR-OBS-005, NFR-REL-002..003
* **SDD refs:** Â§5.3.4, Â§9.2, Â§10.2
* **Dependencies:** IP-29
* **Completion evidence**
  * Tests: `py/tests/integration/test_live_session_controller.py`, `py/tests/e2e/test_live_startup_gating.py`
  * Usage: `usage/live/session_controller_usage.md`
  * Bench/log: `artifacts/logs/live/session_startup.log`
  * Commit: `TBD`

#### [ ] IP-46 Warm recovery and state reconstruction

* **Sub-tasks**
  * [ ] Implement checkpointing for warm recovery state. (FR-LIVE-004, FR-STOR-011)
  * [ ] Implement broker reconnection with exponential backoff (target <30s). (FR-LIVE-007)
  * [ ] Implement position and order reconciliation before resuming flow. (FR-LIVE-005)
* **Deliverables**
  * warm restart and state reconstruction logic
* **SRS refs:** FR-LIVE-004..005, FR-LIVE-007, FR-STOR-011, NFR-REC-001..004
* **SDD refs:** Â§5.3.4, Â§10.3, Â§12
* **Dependencies:** IP-45, IP-15
* **Completion evidence**
  * Tests: `py/tests/e2e/test_warm_restart_recovery.py`
  * Usage: `usage/live/recovery_runbook.md`
  * Bench/log: `artifacts/logs/live/recovery_trace.log`
  * Commit: `TBD`

#### [ ] IP-47 Automated incident response and recovery workflows

* **Sub-tasks**
  * [ ] Implement auto-recovery for minor connection/data issues. (FR-LIVE-011, FR-LIVE-007)
  * [ ] Implement manual intervention workflows with authorization. (FR-LIVE-006, FR-LIVE-011)
* **Deliverables**
  * auto-recovery and manual override playbooks
* **SRS refs:** FR-LIVE-005..006, FR-LIVE-011, NFR-REL-005
* **SDD refs:** Â§5.3.4, Â§12
* **Dependencies:** IP-46
* **Completion evidence**
  * Tests: `py/tests/e2e/test_incident_response_flow.py`
  * Usage: `usage/live/incident_management.md`
  * Bench/log: `artifacts/logs/live/incident_sample.json`
  * Commit: `TBD`

#### [ ] IP-48 Retention, archival, and fast replay data access

* **Deliverables**

  * retention policy executor + archive reader for replay
* **SRS refs:** FR-STOR-005..006
* **SDD refs:** Â§8, Â§18
* **Dependencies:** IP-15, IP-17, IP-40
* **Completion evidence**

  * Tests: `py/tests/integration/test_retention_and_archive.py`
  * Usage: `usage/ops/retention_and_archive.md`
  * Bench/log: `benchmarks/storage/archive_replay_access.md`
  * Commit: `TBD`

---

### Phase H â€” API, UI, and User Workflows

#### [ ] IP-49 REST API gateway v1

* **Deliverables**

  * run control, orders, positions, metrics, health APIs
* **SRS refs:** FR-API-001, FR-API-003, FR-API-006, FR-INT-006
* **SDD refs:** Â§5.3.5, Â§7.5
* **Dependencies:** IP-12, IP-51
* **Completion evidence**

  * Tests: `py/tests/integration/test_api_rest_v1.py`, `py/tests/contracts/test_api_contracts.py`
  * Usage: `usage/api/rest_reference.md`
  * Bench/log: `benchmarks/api/rest_latency.md`
  * Commit: `TBD`

#### [ ] IP-50 WebSocket streaming gateway

* **Sub-tasks**
  * [ ] Implement streaming channels for orders/fills/pnl/risk/health/alerts. (FR-API-002)
  * [ ] Implement real-time system status updates via WebSocket. (FR-API-002)
* **Deliverables**
  * streaming channels for orders/fills/pnl/risk/health/alerts
* **SRS refs:** FR-API-002, FR-INT-005
* **SDD refs:** Â§5.3.5, Â§7.5
* **Dependencies:** IP-49, IP-55
* **Completion evidence**
  * Tests: `py/tests/integration/test_api_ws_streams.py`
  * Usage: `usage/api/websocket_reference.md`
  * Bench/log: `benchmarks/api/ws_throughput.md`
  * Commit: `TBD`

#### [ ] IP-51 RBAC enforcement and secure API controls

* **Sub-tasks**
  * [ ] Implement JWT Authentication and RBAC roles. (FR-API-004, NFR-SEC-002)
  * [ ] Implement elevated permission flow for live trading actions. (FR-API-005, NFR-SEC-005)
  * [ ] Enforce password complexity and account locking policies. (NFR-SEC-007..008)
  * [ ] Use Argon2/Bcrypt for password hashing (no plaintext storage). (NFR-SEC-012)
* **Deliverables**
  * Auth/AuthZ layer for API and UI
* **SRS refs:** FR-API-004..005, NFR-SEC-002, NFR-SEC-005..012, NFR-AUD-001..003
* **SDD refs:** Â§11, Â§5.3.5
* **Dependencies:** IP-16
* **Completion evidence**
  * Tests: `py/tests/security/test_rbac.py`, `py/tests/security/test_privileged_audit.py`
  * Usage: `usage/api/rbac_and_permissions.md`
  * Bench/log: `artifacts/logs/security/rbac_audit_events.json`
  * Commit: `TBD`

#### [ ] IP-52 UI shell + role-aware navigation

* **Deliverables**

  * authenticated dashboard shell and permission-aware menus
* **SRS refs:** FR-UI-001, FR-UI-006, NFR-USE-001
* **SDD refs:** Â§5.3.6, Â§11
* **Dependencies:** IP-51
* **Completion evidence**

  * Tests: `py/tests/e2e/test_ui_navigation_rbac.py`
  * Usage: `usage/ui/navigation.md`
  * Bench/log: N/A
  * Commit: `TBD`

#### [ ] IP-53 Live health/risk/execution dashboards

* **Deliverables**

  * real-time health and risk visualizations
* **SRS refs:** FR-UI-001, FR-UI-005, FR-OBS-005, NFR-USE-001
* **SDD refs:** Â§10.2, Â§10.3, Â§14
* **Dependencies:** IP-50, IP-55, IP-46
* **Completion evidence**

  * Tests: `py/tests/e2e/test_ui_live_health.py`
  * Usage: `usage/ui/live_health_dashboard.md`
  * Bench/log: `artifacts/logs/ui/live_dashboard_snapshot.log`
  * Commit: `TBD`

#### [ ] IP-54 Research/backtest UI + reporting exports

* **Deliverables**

  * research outputs + charts + export flows
* **SRS refs:** FR-UI-002..004, NFR-USE-002..003
* **SDD refs:** Â§10.1, Â§10.4, Â§5.3.6
* **Dependencies:** IP-44, IP-49
* **Completion evidence**

  * Tests: `py/tests/e2e/test_ui_research_reporting.py`
  * Usage: `usage/ui/research_and_reports.md`
  * Bench/log: `artifacts/logs/ui/report_export_examples.json`
  * Commit: `TBD`

---

### Phase I â€” Observability, Notifications, Security Hardening

#### [ ] IP-55 Metrics instrumentation and health endpoints

* **Sub-tasks**
  * [ ] Collect operational metrics: latency, throughput, failures. (FR-OBS-002)
  * [ ] Implement SLO dashboards (Latency <200ms, Freshness). (NFR-OBS-004, NFR-PERF-010)
  * [ ] Implement health endpoints and service readiness checks. (FR-OBS-005)
* **Deliverables**
  * system metrics, SLO probes, health endpoints
* **SRS refs:** FR-OBS-002, FR-OBS-005, NFR-OBS-002..004, NFR-PERF-010
* **SDD refs:** Â§12, Â§14, Â§5.3.7
* **Dependencies:** IP-01
* **Completion evidence**
  * Tests: `py/tests/integration/test_metrics_pipeline.py`, `py/tests/integration/test_health_endpoints.py`
  * Usage: `usage/ops/metrics_and_health.md`
  * Bench/log: `artifacts/benchmarks/obs/metrics_capacity.json`
  * Commit: `TBD`

#### [ ] IP-56 Distributed tracing across critical flow

* **Sub-tasks**
  * [ ] Implement trace propagation: ingestion â†’ strategy â†’ risk â†’ OMS â†’ execution. (FR-OBS-003)
  * [ ] Configure trace sampling based on operating mode and severity. (NFR-OBS-003)
* **Deliverables**
  * trace propagation ingestâ†’strategyâ†’riskâ†’OMSâ†’execution
* **SRS refs:** FR-OBS-003, NFR-OBS-003
* **SDD refs:** Â§14.3
* **Dependencies:** IP-55, IP-23, IP-35
* **Completion evidence**
  * Tests: `py/tests/integration/test_trace_propagation.py`
  * Usage: `usage/ops/distributed_tracing.md`
  * Bench/log: `artifacts/logs/tracing/sample_trace.json`
  * Commit: `TBD`

#### [ ] IP-57 Real-time alerting and notification channels

* **Sub-tasks**
  * [ ] Implement Telegram notification channel (Bot API). (FR-NOTIF-001)
  * [ ] Implement Email notification channel (SMTP). (FR-NOTIF-002)
  * [ ] Support granular configuration (channel per event, rate limiting). (FR-NOTIF-004, FR-NOTIF-006)
  * [ ] Implement notification audit trail in database. (FR-NOTIF-007)
* **Deliverables**
  * alert routing and incident logging
* **SRS refs:** FR-OBS-004, FR-OBS-006, FR-NOTIF-001..007, NFR-REL-005, NFR-SEC-006
* **SDD refs:** Â§12, Â§14.4, Â§5.3.7
* **Dependencies:** IP-55
* **Completion evidence**
  * Tests: `py/tests/integration/test_alert_routing.py`, `py/tests/integration/test_escalation_policy.py`, `py/tests/integration/test_notifications.py`
  * Usage: `usage/ops/alerts_and_escalations.md`
  * Bench/log: `artifacts/logs/alerts/delivery_report.json`
  * Commit: `TBD`

---

### Phase J â€” Testing, CI/CD, Performance Gates, Release

#### [ ] IP-58 Test architecture implementation (unit/integration/contract/parity/e2e)

* **Sub-tasks**
  * [ ] Implement unit test harnesses for C++ (Google Test) and Python (pytest). (FR-TEST-001)
  * [ ] Implement integration tests for bridge contracts and cross-language flows. (FR-TEST-002)
  * [ ] Implement fault-injection tests (disconnects, price gaps, rejects). (FR-TEST-005)
  * [ ] Enforce minimum coverage thresholds (>70% MVP, >90% V2). (NFR-TST-001, NFR-TST-007)
* **Deliverables**
  * test harnesses and fixtures for all layers
* **SRS refs:** FR-TEST-001..002, FR-TEST-005..006, NFR-TST-001..004, NFR-TST-007
* **SDD refs:** Â§16
* **Dependencies:** IP-12, IP-22, IP-31, IP-37
* **Completion evidence**
  * Tests: `py/tests/**`, `cpp/tests/**` (suite index file required)
  * Usage: `usage/ops/test_strategy.md`
  * Bench/log: `artifacts/logs/tests/test_matrix_report.json`
  * Commit: `TBD`

#### [ ] IP-59 Risk parity tests (Python vs C++)

* **Sub-tasks**
  * [ ] Implement parity test harness comparing risk decisions across both layers. (FR-TEST-004)
  * [ ] Validate position sizing and margin calculations against manual baseline. (Acceptance Criteria 9.2)
* **Deliverables**
  * parity harness and policy consistency assertions
* **SRS refs:** FR-RISK-001..006, FR-TEST-004, Program DoD #2
* **SDD refs:** Â§16, Â§5.1.4
* **Dependencies:** IP-27, IP-28
* **Completion evidence**
  * Tests: `py/tests/parity/test_risk_parity.py`
  * Usage: `usage/risk/parity_testing.md`
  * Bench/log: `artifacts/benchmarks/parity/risk_parity_report.json`
  * Commit: `TBD`

#### [ ] IP-60 CI pipeline (build/lint/type/unit/integration)

* **Sub-tasks**
  * [ ] Implement CI build matrix for C++20 and Python 3.11+. (FR-CICD-001)
  * [ ] Integrate linting (clang-tidy, ruff) and static analysis (mypy). (FR-CICD-002, NFR-MNT-004)
  * [ ] Enforce secure secret scanning in protected branches. (NFR-SEC-011)
* **Deliverables**
  * CI matrix for C++ + Python
* **SRS refs:** FR-CICD-001..003, NFR-MNT-004, NFR-SEC-011
* **SDD refs:** Â§15, Â§16
* **Dependencies:** IP-58
* **Completion evidence**
  * Tests: `py/tests/unit/test_ci_manifest.py`
  * Usage: `usage/ops/ci_pipeline.md`
  * Bench/log: CI artifacts and run logs
  * Commit: `TBD`

#### [ ] IP-61 Contract + migration integrity gates

* **Sub-tasks**
  * [ ] Implement blocking gates for schema evolution and backward compatibility. (FR-CICD-005, FR-STOR-004)
  * [ ] Automate `requirements_traceability_matrix.md` updates from run manifests. (SRS Â§10)
* **Deliverables**
  * blocking gates for schema and migrations
* **SRS refs:** FR-CICD-002, FR-CICD-005..006, FR-STOR-004, FR-INT-005, SRS Â§10
* **SDD refs:** Â§8, Â§15, Â§17, Â§18
* **Dependencies:** IP-12, IP-15, IP-60
* **Completion evidence**
  * Tests: `py/tests/migrations/test_ci_migration_gate.py`, `py/tests/contracts/test_ci_contract_gate.py`
  * Usage: `usage/ops/contract_migration_gates.md`
  * Bench/log: CI gate logs
  * Commit: `TBD`

#### [ ] IP-62 Performance regression gates

* **Sub-tasks**
  * [ ] Implement regression suite for throughput (ticks/sec) and latency (ms). (NFR-TST-003)
  * [ ] Benchmark bridge overhead and event-driven processing speed. (NFR-PERF-001..005)
* **Deliverables**
  * baseline + delta checks for throughput/latency/bridge overhead
* **SRS refs:** NFR-PERF-001..005, FR-CICD-005, NFR-TST-003
* **SDD refs:** Â§13, Â§16
* **Dependencies:** IP-21, IP-36, IP-39, IP-60
* **Completion evidence**
  * Tests: `py/tests/perf/test_perf_regressions.py`
  * Usage: `usage/ops/performance_gates.md`
  * Bench/log: `artifacts/benchmarks/perf_gate/perf_delta.json`
  * Commit: `TBD`

#### [ ] IP-63 Security hardening and penetration checklist

* **Sub-tasks**
  * [ ] Implement security audit for auth, secrets, and permissions. (NFR-SEC-001..006)
  * [ ] Validate input sanitization and rate limiting controls. (NFR-SEC-009..010)
* **Deliverables**
  * security review, secret scanning, permission hardening
* **SRS refs:** NFR-SEC-001..006, NFR-SEC-009..010, FR-CICD-005
* **SDD refs:** Â§11, Â§15
* **Dependencies:** IP-51, IP-60
* **Completion evidence**
  * Tests: `py/tests/security/test_security_controls.py`
  * Usage: `usage/ops/security_hardening.md`
  * Bench/log: `artifacts/logs/security/hardening_report.json`
  * Commit: `TBD`

#### [ ] IP-64 Deployment topology and rollout playbooks

* **Sub-tasks**
  * [ ] Define dev/staging/live deployment manifests (Windows/Linux/OSX). (SRS Â§3.3)
  * [ ] Implement failover and rollback procedures. (FR-CICD-004, NFR-REL-006)
* **Deliverables**
  * dev/staging/prod manifests, canary and rollback
* **SRS refs:** FR-CICD-003..004, NFR-SCL-001..003, NFR-REL-001..003, NFR-REL-006, SRS Â§3.3
* **SDD refs:** Â§15
* **Dependencies:** IP-60, IP-61
* **Completion evidence**
  * Tests: `py/tests/e2e/test_deployment_smoke.py`
  * Usage: `usage/ops/deployment_rollout.md`
  * Bench/log: rollout simulation logs
  * Commit: `TBD`

#### [ ] IP-65 UML/sequence diagrams and docs sync gate

* **Sub-tasks**
  * [ ] Automate Sphinx/Doxygen generation for code-level documentation. (NFR-DOC-001)
  * [ ] Enforce sync between implementation and SDD/SRS diagrams in CI. (NFR-DOC-003, SDD Â§17)
* **Deliverables**
  * class diagrams and user sequence diagrams kept in sync with code/contracts
* **SRS refs:** FR-CICD-006, FR-TEST-006, NFR-DOC-001, NFR-DOC-003, SDD Â§17
* **SDD refs:** Â§6, Â§10, Â§17, Â§19
* **Dependencies:** IP-22, IP-31, IP-37, IP-49, IP-53
* **Completion evidence**
  * Tests: `py/tests/unit/test_docs_sync_gate.py`
  * Usage: `usage/ops/diagram_sync_process.md`
  * Bench/log: docs sync CI logs
  * Commit: `TBD`

---

## 4) PR Slicing Plan (Small, Traceable PRs)

* **PR-1:** IP-01
* **PR-2:** IP-02 + IP-04 (if LOC budget allows; else separate)
* **PR-3:** IP-12
* **PR-4:** IP-15 + IP-16
* **PR-5:** IP-06 + IP-07
* **PR-6:** IP-18 + IP-19
* **PR-7:** IP-20 + IP-21
* **PR-8:** IP-22 + IP-23
* **PR-9:** IP-25 + IP-27 + IP-31 (split if too large)
* **PR-10:** IP-34 + IP-35
* **PR-11:** IP-37 + IP-39
* **PR-12:** IP-41 + IP-42 + IP-43
* **PR-13:** IP-45 + IP-46 + IP-47
* **PR-14:** IP-49 + IP-50 + IP-51
* **PR-15:** IP-52 + IP-53 + IP-54
* **PR-16:** IP-55 + IP-56 + IP-57
* **PR-17:** IP-58 + IP-59 + IP-60
* **PR-18:** IP-61 + IP-62 + IP-63 + IP-64 + IP-65

> If any PR exceeds size budget, split by single task ID and keep dependency order.

---

## 5) Milestone Gates

### M1 Foundation Complete

* IP-01..IP-05, IP-12 complete.

### M2 Core Engine + Bridge Complete

* IP-06..IP-11, IP-13..IP-21 complete.

### M3 Trading Core Complete

* IP-22..IP-36 complete.

### M4 Research/Backtest/Storage Complete

* IP-37..IP-44, IP-48 complete.

### M5 Live Ops + UX Complete

* IP-45..IP-57 complete.

### M6 Quality + Release Complete

* IP-58..IP-65 complete.

---

## 6) Completion Ledger Template (Required Per Task)

| Task ID | Status  | SRS refs | SDD refs | Test files | Usage files | Bench/Log evidence | Commit |
| ------- | ------- | -------- | -------- | ---------- | ----------- | ------------------ | ------ |
| IP-XX   | [ ]/[x] | ...      | ...      | ...        | ...         | ...                | ...    |

---

## 7) Global Exit Checklist (Program DoD Validation)

* [ ] Backtest/live canonical contracts validated (IP-22, IP-23, IP-37, IP-45)
* [ ] Python vs C++ risk parity green (IP-59)
* [ ] Reconcile/kill-switch/degraded mode proven in e2e drills (IP-29, IP-33, IP-46, IP-47)
* [ ] UI unified model for live + research outputs (IP-53, IP-54)
* [ ] CI enforces contracts/tests/lint/migrations/perf gates (IP-60..IP-62)

---

## 8) Notes for Execution

1. Do not mark any task `[x]` without all completion evidence fields populated.
2. Keep one primary task per PR for clean traceability.
3. Any change touching hot path **must** include benchmark artifact.
4. Any change touching live safety **must** include e2e drill evidence.
5. `requirements_traceability_matrix.md` must be auto-updated in CI on every merged task.

---
