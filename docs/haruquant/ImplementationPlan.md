# ImplementationPlan.md

## Hybrid C++/Python Quantitative Trading & Backtesting System  
**Baseline:** Nanobind + Signal-Driven first  
**Derived from:** `01_software_requirements_specification_updated.md`, `02_system_design_document_updated.md`, `requirements_traceability_matrix.xlsx`  
**Date:** 2026-02-16

---

## How to use this checklist

- Mark items as done by replacing `[ ]` with `[x]`.
- Keep PRs small and traceable.
- Every completed item must link to:
  - requirement IDs,
  - test file(s),
  - benchmark/log evidence (when applicable).

---

## Definition of Done (Global)

- [ ] Code merged with passing CI (unit + integration + lint/type checks)
- [ ] Requirement IDs referenced in PR description
- [ ] Tests added/updated with clear assertions
- [ ] Reproducibility metadata included in outputs where applicable
- [ ] Docs updated (SRS/SDD/README/module docs)
- [ ] Performance-sensitive paths benchmarked (if touched)

---

## Phase 0 — Project Foundation & Build Skeleton (P0)

### 0.1 Repository and Toolchain
- [ ] Create canonical repo layout:
  - [ ] `hybrid_backtester/python/...`
  - [ ] `hybrid_backtester/cpp_core/...`
  - [ ] `hybrid_backtester/bridge/...`
  - [ ] `config/`, `scripts/`, `docs/`, `tests/`
- [ ] Setup Python packaging (`pyproject.toml`) and env management
- [ ] Setup C++ build system (`CMakeLists.txt`) for core + tests + benchmarks
- [ ] Setup cross-platform CI (Windows + Linux matrix)
- [ ] Add linting/formatting:
  - [ ] Python: ruff/black/mypy
  - [ ] C++: clang-format/clang-tidy
- [ ] Add commit hooks and quality gates

**Req IDs:** FND-FR-001..006, NFR-MNT-001..002  
**Primary tests:** `tests/quality/test_ci_guards.py`

### 0.2 Logging/Config/Secrets Baseline
- [ ] Implement structured logger in Python with `run_id` correlation
- [ ] Implement structured logger in C++ and harmonize schema with Python
- [ ] Implement typed config loader (TOML + environment overlay)
- [ ] Implement secret redaction middleware/helpers
- [ ] Implement error taxonomy shared across Python/C++

**Req IDs:** FND-FR-001..005, NFR-SEC-001..002  
**Primary tests:** `tests/unit/test_foundation.py`, `tests/security/test_secrets_redaction.py`

### 0.3 Nanobind Hello-Path
- [ ] Create Nanobind module `hqt_engine`
- [ ] Expose `version()` and simple array op (`sum` smoke function)
- [ ] Validate dtype/shape errors map to Python exceptions
- [ ] Add GIL release pattern for long native calls template

**Req IDs:** BRG-FR-001..004  
**Primary tests:** `tests/integration/test_nanobind_bridge.py`

---

## Phase 1 — Data Contracts + Signal-Driven Core v1 (P0)

### 1.1 Market Data Contracts (Python side)
- [ ] Implement loaders (`parquet/csv`) with symbol/timeframe metadata
- [ ] Implement normalization to required arrays:
  - [ ] `ts:int64`
  - [ ] `open/high/low/close:float64`
  - [ ] `volume:float64` (optional)
  - [ ] `spread:float64` (optional)
- [ ] Implement validators:
  - [ ] monotonic timestamps
  - [ ] duplicates/gaps checks
  - [ ] spread sanity checks
  - [ ] schema contract enforcement
- [ ] Persist data version/hash and lineage metadata

**Req IDs:** DAT-FR-001..005, STR-FR-003  
**Primary tests:** `tests/unit/test_data_validation.py`

### 1.2 Signal Contract SDK (Python side)
- [ ] Implement signal adapters with required alignment checks
- [ ] Implement baseline strategies as signal generators:
  - [ ] EMA crossover
  - [ ] Williams %R example
- [ ] Ensure outputs support:
  - [ ] `entry_long`, `entry_short`
  - [ ] optional `exit_long`, `exit_short`
  - [ ] optional `size`, `sl_points`, `tp_points`

**Req IDs:** STR-FR-001..004, BKT-FR-001  
**Primary tests:** `tests/unit/test_signal_contracts.py`

### 1.3 C++ SignalEngine v1
- [ ] Implement deterministic bar loop
- [ ] Implement entry/exit policy order (document tie-breaking)
- [ ] Implement netting position model (one position per symbol)
- [ ] Implement fill logic with spread/slippage
- [ ] Implement commission/swap hooks (default no-op configurable)
- [ ] Implement portfolio accounting:
  - [ ] balance/equity
  - [ ] floating and realized PnL
  - [ ] margin/free margin baseline
- [ ] Emit outputs:
  - [ ] trades array
  - [ ] equity curve
  - [ ] summary metrics baseline

**Req IDs:** CPP-FR-001..005, BKT-FR-001..005, TRD-FR-001..003  
**Primary tests:** `cpp_core/tests/test_core_engine.cpp`, `tests/integration/test_backtest_modes.py`

### 1.4 Nanobind bridge for run_bars_signals
- [ ] Bind `run_bars_signals(market, signals, config)`
- [ ] Add input validation and exception mapping
- [ ] Ensure no per-row marshaling (buffer protocol usage)
- [ ] Add long-run GIL release guard
- [ ] Return structured result object (trades/equity/metrics/meta)

**Req IDs:** BRG-FR-001..004, NFR-PERF-002..003  
**Primary tests:** `tests/integration/test_nanobind_bridge.py`

### 1.5 Persistence + Repro bundle v1
- [ ] Implement `runs`, `run_configs`, `run_metrics`, `run_trades`, `artifacts`
- [ ] Implement run reproducibility bundle:
  - [ ] config hash
  - [ ] data hash/version
  - [ ] engine version/commit
  - [ ] seed
- [ ] Save top-level report artifact and references

**Req IDs:** NFR-DET-001..002, DAT-FR-005  
**Primary tests:** `tests/regression/test_deterministic_replay.py`

---

## Phase 2 — Batch Optimization & Throughput Scaling (P0/P1)

### 2.1 C++ BatchRunner
- [ ] Implement thread-pool based parallel run scheduling
- [ ] Implement per-run deterministic seed assignment
- [ ] Implement top-K reduction and leaderboard output
- [ ] Add failure isolation per job and partial-result handling

**Req IDs:** BKT-FR-003..006, OPT-FR-004, NFR-PERF-001  
**Primary tests:** `tests/integration/test_batch_optimization.py`

### 2.2 Python orchestration for batch/wfo
- [ ] Implement `run_batch.py` with config pack creation
- [ ] Implement `run_wfo.py` scaffold (windowing + fold orchestration)
- [ ] Implement persistent optimization tables:
  - [ ] `optimization_jobs`
  - [ ] `optimization_results`
- [ ] Add resumable/restartable batch job control

**Req IDs:** OPT-FR-001..004  
**Primary tests:** `tests/integration/test_batch_optimization.py`

### 2.3 Performance benchmarking suite
- [ ] Add benchmarks for:
  - [ ] single-run throughput (bars/sec)
  - [ ] batch throughput (runs/sec)
  - [ ] bridge overhead and memory
- [ ] Establish baseline thresholds and CI perf report artifact
- [ ] Compare Python-only vs hybrid speedup on fixed dataset

**Req IDs:** NFR-PERF-001..003  
**Primary tests:** `tests/perf/test_perf_benchmarks.py`

---

## Phase 3 — Event-Driven Engine Parity (P1)

### 3.1 EventEngine core
- [ ] Implement event queue and dispatch loop
- [ ] Implement pending orders (limit/stop) lifecycle
- [ ] Implement order modify/cancel semantics
- [ ] Implement partial close support and lifecycle transitions
- [ ] Implement intrabar SL/TP policy options

**Req IDs:** BKT-FR-002, TRD-FR-002..003, CPP-FR-001  
**Primary tests:** `tests/unit/test_order_lifecycle.py`, `tests/integration/test_backtest_modes.py`

### 3.2 Unified interface parity
- [ ] Ensure strategy/trading API uniformity between signal/event modes
- [ ] Ensure output schema parity between modes
- [ ] Add mode comparison tool for diagnostics

**Req IDs:** TRD-FR-001, BKT-FR-004  
**Primary tests:** `tests/integration/test_backtest_modes.py`

---

## Phase 4 — Risk Governor + Live/Paper Hardening (P0 for live safety, otherwise P1)

### 4.1 Risk Governor
- [ ] Implement hard daily loss limit
- [ ] Implement max exposure and max concurrent positions
- [ ] Implement symbol/session throttles
- [ ] Implement circuit breaker and kill-switch interfaces
- [ ] Add audit logs for blocked actions

**Req IDs:** RSK-FR-001..003  
**Primary tests:** `tests/integration/test_risk_governor.py`

### 4.2 MT5 Gateway integration (live path)
- [ ] Implement ZeroMQ protocol contracts
- [ ] Implement connect/reconnect + heartbeat
- [ ] Implement startup reconciliation:
  - [ ] open positions
  - [ ] pending orders
  - [ ] account state
- [ ] Implement fail-safe halt on ambiguity/disconnect
- [ ] Add critical notifications integration

**Req IDs:** LIV-FR-001..003, NTF-FR-003, NFR-REL-002  
**Primary tests:** `tests/integration/test_live_gateway_reconcile.py`, `tests/integration/test_recovery_and_reconnect.py`

### 4.3 Paper mode parity
- [ ] Implement paper engine using same strategy interface as live
- [ ] Implement configurable fill realism profiles
- [ ] Validate behavior consistency vs signal/event backtest semantics

**Req IDs:** PAP-FR-001..002  
**Primary tests:** `tests/integration/test_paper_mode_parity.py`

---

### 4.4 Live Hardening Addendum (Institutional Safety)
- [ ] Implement idempotent order keys for all live order submissions
- [ ] Implement retry-safe deduplication on reconnect/replay windows
- [ ] Implement clock-sync guard (reject/hold trading on excessive drift)
- [ ] Implement broker rule snapshot cache:
  - [ ] min lot / lot step
  - [ ] min stop distance
  - [ ] symbol trading permissions/session windows
- [ ] Implement daily reconciliation report:
  - [ ] local state vs broker state diff
  - [ ] unmatched orders/positions/deals
  - [ ] operator action checklist
- [ ] Implement manual kill-switch command channel (operator override)
- [ ] Implement latency telemetry:
  - [ ] signal->risk_check->send_order
  - [ ] send_order->broker_ack/fill
  - [ ] p50/p95/p99 dashboards and alerts
- [ ] Implement degraded-mode policy:
  - [ ] quote stale detection
  - [ ] spread blowout guard
  - [ ] auto-throttle/auto-halt thresholds

**Req IDs (newly emphasized mapping):** LIV-FR-001..003, RSK-FR-001..003, NFR-REL-002, NFR-SEC-001..002, NTF-FR-003  
**Primary tests:** `tests/integration/test_live_idempotency_and_dedup.py`, `tests/integration/test_clock_sync_guard.py`, `tests/integration/test_broker_rules_cache.py`, `tests/integration/test_daily_reconciliation_report.py`, `tests/integration/test_kill_switch_channel.py`, `tests/integration/test_latency_telemetry_slos.py`


## Phase 5 — API, Desktop UI, and Reporting (P1)

### 5.1 REST/WS API
- [ ] Implement endpoints:
  - [ ] `POST /runs/backtest/signal`
  - [ ] `POST /runs/backtest/event`
  - [ ] `POST /runs/optimize`
  - [ ] `GET /runs/{run_id}`
  - [ ] `GET /health`
  - [ ] `WS /stream/runs/{run_id}`
- [ ] Add auth/token guards for non-local deployments
- [ ] Add pagination and filtering for run history

**Req IDs:** API-FR-001..003  
**Primary tests:** `tests/api/test_routes_and_ws.py`

### 5.2 Desktop UI (PySide6)
- [ ] Implement run launcher panel
- [ ] Implement equity/drawdown chart views
- [ ] Implement trade blotter + metrics panels
- [ ] Implement optimization leaderboard view
- [ ] Implement reproducibility bundle viewer

**Req IDs:** GUI-FR-001..003  
**Primary tests:** `tests/ui/test_desktop_panels.py`

### 5.3 Reporting pipeline
- [ ] Generate markdown/html run reports
- [ ] Include strategy params, metrics, trade stats, plot artifacts
- [ ] Include repro metadata in report footer/metadata block

**Req IDs:** BKT-FR-004, NFR-DET-002  
**Primary tests:** `tests/integration/test_reporting_pipeline.py`

---

## Phase 6 — Reliability, Security, and Ops Excellence (P0/P1 depending environment)

### 6.1 WAL and crash recovery
- [ ] Implement WAL for state-changing operations
- [ ] Implement replay/recovery routines
- [ ] Add stale lock cleanup and restart checks
- [ ] Add crash simulation integration tests

**Req IDs:** FND-FR-006, NFR-REL-001  
**Primary tests:** `tests/integration/test_recovery_and_reconnect.py`

### 6.2 Security hardening
- [ ] Enforce secret source policy (env/secure store)
- [ ] Redact sensitive fields in logs/APIs/UI exports
- [ ] Add permission boundaries for live operations
- [ ] Add security review checklist in CI template

**Req IDs:** NFR-SEC-001..002  
**Primary tests:** `tests/security/test_secrets_redaction.py`

### 6.3 Observability and SLOs
- [ ] Implement health metrics export (engine/api/bridge)
- [ ] Add throughput and latency dashboards
- [ ] Define SLOs and alert thresholds
- [ ] Add on-call runbook

**Req IDs:** FND-FR-001..002, NFR-REL-001..002, NFR-PERF-001  
**Primary tests:** `tests/integration/test_observability_contracts.py`

---

## Cross-Cutting Workstreams (run in parallel)

### A) Data quality & model realism
- [ ] Add spread regime analysis and anomaly flags
- [ ] Add slippage model calibration tools
- [ ] Add broker metadata versioning/validation

### B) Determinism governance
- [ ] Enforce deterministic seed injection in all modes
- [ ] Record deterministic tie-break policy in metadata
- [ ] Add “replay exact run” CLI command

### C) Documentation governance
- [ ] Keep SRS/SDD updated per major milestone
- [ ] Maintain module READMEs with API contracts
- [ ] Maintain sequence/class diagrams in design docs

---

## Milestone Checklist (Executive View)

### M1 — Signal-Driven MVP
- [ ] Phase 0 complete
- [ ] Phase 1 complete
- [ ] Deterministic replay test passing
- [ ] Baseline benchmark report published

### M2 — Optimization Engine
- [ ] Phase 2 complete
- [ ] Top-K optimization workflow stable
- [ ] Throughput target reached and documented

### M3 — Event Parity
- [ ] Phase 3 complete
- [ ] Event vs Signal consistency diagnostics added

### M4 — Live/Paper Safety
- [ ] Phase 4 complete
- [ ] Risk governor and reconciliation validated

### M5 — Platform Completeness
- [ ] Phase 5 complete
- [ ] Phase 6 critical items complete

---

## Suggested Sprint Breakdown (Checklist)

### Sprint 1
- [ ] Phase 0.1, 0.2, 0.3

### Sprint 2
- [ ] Phase 1.1, 1.2

### Sprint 3
- [ ] Phase 1.3, 1.4, 1.5

### Sprint 4
- [ ] Phase 2.1, 2.2, 2.3

### Sprint 5
- [ ] Phase 3.1, 3.2

### Sprint 6
- [ ] Phase 4.1, 4.2, 4.3
- [ ] Phase 4.4 live hardening addendum tasks

### Sprint 7
- [ ] Phase 5.1, 5.2, 5.3

### Sprint 8
- [ ] Phase 6.1, 6.2, 6.3 + closure hardening

---

## Completion Criteria

- [ ] All P0 requirements closed or formally deferred with sign-off
- [ ] Regression suite stable
- [ ] Performance acceptance met
- [ ] Live safety acceptance passed (if live enabled)
- [ ] Documentation and traceability artifacts current

---

## Linked Artifacts

- [ ] `01_software_requirements_specification_updated.md`
- [ ] `02_system_design_document_updated.md`
- [ ] `requirements_traceability_matrix.xlsx`
- [ ] `requirements_traceability_matrix.csv`
