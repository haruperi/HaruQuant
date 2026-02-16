# Tasks.md

Comprehensive sprint-ready task board derived from `ImplementationPlan.md`.

## Legend
- **Estimate**: S (<=1 day), M (2–4 days), L (5+ days)
- **Priority**: P0 (must-have), P1 (important next)
- **Status**: Not Started / In Progress / Blocked / Done

## Task Board (Checklist)

### Sprint 1
- [ ] **T-001** — Setup canonical repository layout  
  - Estimate: `M` | Priority: `P0` | Status: `Not Started`  
  - Depends on: ``  
  - Owner: `TBD` | PR: `TBD` | Requirement IDs: `TBD` | Test Case IDs: `TBD`
- [ ] **T-002** — Configure Python packaging and environment management  
  - Estimate: `S` | Priority: `P0` | Status: `Not Started`  
  - Depends on: `T-001`  
  - Owner: `TBD` | PR: `TBD` | Requirement IDs: `TBD` | Test Case IDs: `TBD`
- [ ] **T-003** — Configure CMake build for cpp_core + tests + benchmarks  
  - Estimate: `M` | Priority: `P0` | Status: `Not Started`  
  - Depends on: `T-001`  
  - Owner: `TBD` | PR: `TBD` | Requirement IDs: `TBD` | Test Case IDs: `TBD`
- [ ] **T-004** — Setup CI matrix (Windows/Linux) with lint/test gates  
  - Estimate: `M` | Priority: `P0` | Status: `Not Started`  
  - Depends on: `T-002,T-003`  
  - Owner: `TBD` | PR: `TBD` | Requirement IDs: `TBD` | Test Case IDs: `TBD`
- [ ] **T-005** — Implement structured logging (Python + C++) with run_id correlation  
  - Estimate: `M` | Priority: `P0` | Status: `Not Started`  
  - Depends on: `T-003`  
  - Owner: `TBD` | PR: `TBD` | Requirement IDs: `TBD` | Test Case IDs: `TBD`
- [ ] **T-006** — Implement typed config loader (TOML + env overlay)  
  - Estimate: `S` | Priority: `P0` | Status: `Not Started`  
  - Depends on: `T-002`  
  - Owner: `TBD` | PR: `TBD` | Requirement IDs: `TBD` | Test Case IDs: `TBD`
- [ ] **T-007** — Implement secrets redaction helpers  
  - Estimate: `S` | Priority: `P0` | Status: `Not Started`  
  - Depends on: `T-006`  
  - Owner: `TBD` | PR: `TBD` | Requirement IDs: `TBD` | Test Case IDs: `TBD`
- [ ] **T-008** — Create Nanobind module skeleton + version() + sum(array)  
  - Estimate: `M` | Priority: `P0` | Status: `Not Started`  
  - Depends on: `T-003`  
  - Owner: `TBD` | PR: `TBD` | Requirement IDs: `TBD` | Test Case IDs: `TBD`
- [ ] **T-009** — Add bridge smoke tests (dtype/shape/error mapping)  
  - Estimate: `S` | Priority: `P0` | Status: `Not Started`  
  - Depends on: `T-008`  
  - Owner: `TBD` | PR: `TBD` | Requirement IDs: `TBD` | Test Case IDs: `TBD`

### Sprint 2
- [ ] **T-010** — Implement market data loaders (parquet/csv)  
  - Estimate: `M` | Priority: `P0` | Status: `Not Started`  
  - Depends on: `T-002`  
  - Owner: `TBD` | PR: `TBD` | Requirement IDs: `TBD` | Test Case IDs: `TBD`
- [ ] **T-011** — Implement normalization to market arrays contract  
  - Estimate: `M` | Priority: `P0` | Status: `Not Started`  
  - Depends on: `T-010`  
  - Owner: `TBD` | PR: `TBD` | Requirement IDs: `TBD` | Test Case IDs: `TBD`
- [ ] **T-012** — Implement data validators (monotonic/duplicates/gaps/spread)  
  - Estimate: `M` | Priority: `P0` | Status: `Not Started`  
  - Depends on: `T-011`  
  - Owner: `TBD` | PR: `TBD` | Requirement IDs: `TBD` | Test Case IDs: `TBD`
- [ ] **T-013** — Implement data version/hash lineage metadata  
  - Estimate: `S` | Priority: `P0` | Status: `Not Started`  
  - Depends on: `T-011`  
  - Owner: `TBD` | PR: `TBD` | Requirement IDs: `TBD` | Test Case IDs: `TBD`
- [ ] **T-014** — Implement signal adapters with alignment checks  
  - Estimate: `M` | Priority: `P0` | Status: `Not Started`  
  - Depends on: `T-011`  
  - Owner: `TBD` | PR: `TBD` | Requirement IDs: `TBD` | Test Case IDs: `TBD`
- [ ] **T-015** — Implement baseline signal generators (EMA, Williams %R)  
  - Estimate: `M` | Priority: `P0` | Status: `Not Started`  
  - Depends on: `T-014`  
  - Owner: `TBD` | PR: `TBD` | Requirement IDs: `TBD` | Test Case IDs: `TBD`

### Sprint 3
- [ ] **T-016** — Implement C++ SignalEngine deterministic loop  
  - Estimate: `L` | Priority: `P0` | Status: `Not Started`  
  - Depends on: `T-008,T-011,T-014`  
  - Owner: `TBD` | PR: `TBD` | Requirement IDs: `TBD` | Test Case IDs: `TBD`
- [ ] **T-017** — Implement entry/exit tie-break policy + docs  
  - Estimate: `S` | Priority: `P0` | Status: `Not Started`  
  - Depends on: `T-016`  
  - Owner: `TBD` | PR: `TBD` | Requirement IDs: `TBD` | Test Case IDs: `TBD`
- [ ] **T-018** — Implement fill model (spread/slippage)  
  - Estimate: `M` | Priority: `P0` | Status: `Not Started`  
  - Depends on: `T-016`  
  - Owner: `TBD` | PR: `TBD` | Requirement IDs: `TBD` | Test Case IDs: `TBD`
- [ ] **T-019** — Implement commission/swap hooks  
  - Estimate: `S` | Priority: `P1` | Status: `Not Started`  
  - Depends on: `T-018`  
  - Owner: `TBD` | PR: `TBD` | Requirement IDs: `TBD` | Test Case IDs: `TBD`
- [ ] **T-020** — Implement portfolio accounting (balance/equity/pnl/margin)  
  - Estimate: `L` | Priority: `P0` | Status: `Not Started`  
  - Depends on: `T-016`  
  - Owner: `TBD` | PR: `TBD` | Requirement IDs: `TBD` | Test Case IDs: `TBD`
- [ ] **T-021** — Implement outputs: trades, equity, metrics baseline  
  - Estimate: `M` | Priority: `P0` | Status: `Not Started`  
  - Depends on: `T-020`  
  - Owner: `TBD` | PR: `TBD` | Requirement IDs: `TBD` | Test Case IDs: `TBD`
- [ ] **T-022** — Bind run_bars_signals via Nanobind + GIL release  
  - Estimate: `M` | Priority: `P0` | Status: `Not Started`  
  - Depends on: `T-016,T-008`  
  - Owner: `TBD` | PR: `TBD` | Requirement IDs: `TBD` | Test Case IDs: `TBD`
- [ ] **T-023** — Implement persistence tables (runs/configs/metrics/trades/artifacts)  
  - Estimate: `M` | Priority: `P0` | Status: `Not Started`  
  - Depends on: `T-013`  
  - Owner: `TBD` | PR: `TBD` | Requirement IDs: `TBD` | Test Case IDs: `TBD`
- [ ] **T-024** — Implement reproducibility bundle writer  
  - Estimate: `S` | Priority: `P0` | Status: `Not Started`  
  - Depends on: `T-023`  
  - Owner: `TBD` | PR: `TBD` | Requirement IDs: `TBD` | Test Case IDs: `TBD`

### Sprint 4
- [ ] **T-025** — Implement C++ BatchRunner thread-pool scheduling  
  - Estimate: `L` | Priority: `P0` | Status: `Not Started`  
  - Depends on: `T-016`  
  - Owner: `TBD` | PR: `TBD` | Requirement IDs: `TBD` | Test Case IDs: `TBD`
- [ ] **T-026** — Implement deterministic per-run seed assignment  
  - Estimate: `S` | Priority: `P0` | Status: `Not Started`  
  - Depends on: `T-025`  
  - Owner: `TBD` | PR: `TBD` | Requirement IDs: `TBD` | Test Case IDs: `TBD`
- [ ] **T-027** — Implement top-K reduction + leaderboard  
  - Estimate: `M` | Priority: `P0` | Status: `Not Started`  
  - Depends on: `T-025`  
  - Owner: `TBD` | PR: `TBD` | Requirement IDs: `TBD` | Test Case IDs: `TBD`
- [ ] **T-028** — Implement Python run_batch orchestration  
  - Estimate: `M` | Priority: `P0` | Status: `Not Started`  
  - Depends on: `T-022,T-025`  
  - Owner: `TBD` | PR: `TBD` | Requirement IDs: `TBD` | Test Case IDs: `TBD`
- [ ] **T-029** — Implement WFO orchestration scaffold  
  - Estimate: `M` | Priority: `P1` | Status: `Not Started`  
  - Depends on: `T-028`  
  - Owner: `TBD` | PR: `TBD` | Requirement IDs: `TBD` | Test Case IDs: `TBD`
- [ ] **T-030** — Implement optimization_jobs/results persistence  
  - Estimate: `S` | Priority: `P0` | Status: `Not Started`  
  - Depends on: `T-023,T-028`  
  - Owner: `TBD` | PR: `TBD` | Requirement IDs: `TBD` | Test Case IDs: `TBD`
- [ ] **T-031** — Add perf benchmarks (single/batch/bridge overhead)  
  - Estimate: `M` | Priority: `P0` | Status: `Not Started`  
  - Depends on: `T-025,T-022`  
  - Owner: `TBD` | PR: `TBD` | Requirement IDs: `TBD` | Test Case IDs: `TBD`

### Sprint 5
- [ ] **T-032** — Implement EventEngine event queue + dispatch  
  - Estimate: `L` | Priority: `P1` | Status: `Not Started`  
  - Depends on: `T-016`  
  - Owner: `TBD` | PR: `TBD` | Requirement IDs: `TBD` | Test Case IDs: `TBD`
- [ ] **T-033** — Implement pending orders lifecycle (limit/stop)  
  - Estimate: `M` | Priority: `P1` | Status: `Not Started`  
  - Depends on: `T-032`  
  - Owner: `TBD` | PR: `TBD` | Requirement IDs: `TBD` | Test Case IDs: `TBD`
- [ ] **T-034** — Implement modify/cancel + partial close  
  - Estimate: `M` | Priority: `P1` | Status: `Not Started`  
  - Depends on: `T-033`  
  - Owner: `TBD` | PR: `TBD` | Requirement IDs: `TBD` | Test Case IDs: `TBD`
- [ ] **T-035** — Implement intrabar SL/TP policy options  
  - Estimate: `M` | Priority: `P1` | Status: `Not Started`  
  - Depends on: `T-033`  
  - Owner: `TBD` | PR: `TBD` | Requirement IDs: `TBD` | Test Case IDs: `TBD`
- [ ] **T-036** — Ensure signal/event output schema parity  
  - Estimate: `S` | Priority: `P1` | Status: `Not Started`  
  - Depends on: `T-032,T-021`  
  - Owner: `TBD` | PR: `TBD` | Requirement IDs: `TBD` | Test Case IDs: `TBD`
- [ ] **T-037** — Add mode comparison diagnostics  
  - Estimate: `S` | Priority: `P1` | Status: `Not Started`  
  - Depends on: `T-036`  
  - Owner: `TBD` | PR: `TBD` | Requirement IDs: `TBD` | Test Case IDs: `TBD`

### Sprint 6
- [ ] **T-038** — Implement RiskGovernor hard limits + exposure checks  
  - Estimate: `M` | Priority: `P0` | Status: `Not Started`  
  - Depends on: `T-020`  
  - Owner: `TBD` | PR: `TBD` | Requirement IDs: `TBD` | Test Case IDs: `TBD`
- [ ] **T-039** — Implement circuit breaker + kill switch  
  - Estimate: `S` | Priority: `P0` | Status: `Not Started`  
  - Depends on: `T-038`  
  - Owner: `TBD` | PR: `TBD` | Requirement IDs: `TBD` | Test Case IDs: `TBD`
- [ ] **T-040** — Implement MT5 ZeroMQ protocol contracts  
  - Estimate: `L` | Priority: `P0` | Status: `Not Started`  
  - Depends on: `T-006`  
  - Owner: `TBD` | PR: `TBD` | Requirement IDs: `TBD` | Test Case IDs: `TBD`
- [ ] **T-041** — Implement gateway reconnect + heartbeat  
  - Estimate: `M` | Priority: `P0` | Status: `Not Started`  
  - Depends on: `T-040`  
  - Owner: `TBD` | PR: `TBD` | Requirement IDs: `TBD` | Test Case IDs: `TBD`
- [ ] **T-042** — Implement startup reconciliation (positions/orders/account)  
  - Estimate: `M` | Priority: `P0` | Status: `Not Started`  
  - Depends on: `T-041`  
  - Owner: `TBD` | PR: `TBD` | Requirement IDs: `TBD` | Test Case IDs: `TBD`
- [ ] **T-043** — Implement fail-safe halt on ambiguity/disconnect  
  - Estimate: `S` | Priority: `P0` | Status: `Not Started`  
  - Depends on: `T-042,T-039`  
  - Owner: `TBD` | PR: `TBD` | Requirement IDs: `TBD` | Test Case IDs: `TBD`
- [ ] **T-044** — Implement paper mode parity engine + realism profiles  
  - Estimate: `M` | Priority: `P1` | Status: `Not Started`  
  - Depends on: `T-022`  
  - Owner: `TBD` | PR: `TBD` | Requirement IDs: `TBD` | Test Case IDs: `TBD`

- [ ] **T-057** — Implement idempotent order keys for live order submission  
  - Estimate: `M` | Priority: `P0` | Status: `Not Started`  
  - Depends on: `T-040`  
  - Owner: `TBD` | PR: `TBD` | Requirement IDs: `TBD` | Test Case IDs: `TBD`
- [ ] **T-058** — Implement reconnect retry deduplication window  
  - Estimate: `M` | Priority: `P0` | Status: `Not Started`  
  - Depends on: `T-041,T-057`  
  - Owner: `TBD` | PR: `TBD` | Requirement IDs: `TBD` | Test Case IDs: `TBD`
- [ ] **T-059** — Implement clock-sync guard and drift thresholds  
  - Estimate: `S` | Priority: `P0` | Status: `Not Started`  
  - Depends on: `T-041`  
  - Owner: `TBD` | PR: `TBD` | Requirement IDs: `TBD` | Test Case IDs: `TBD`
- [ ] **T-060** — Implement broker rules snapshot cache (min lot/step/stops/sessions)  
  - Estimate: `M` | Priority: `P0` | Status: `Not Started`  
  - Depends on: `T-040`  
  - Owner: `TBD` | PR: `TBD` | Requirement IDs: `TBD` | Test Case IDs: `TBD`
- [ ] **T-061** — Implement daily reconciliation report (local vs broker diffs)  
  - Estimate: `M` | Priority: `P0` | Status: `Not Started`  
  - Depends on: `T-042`  
  - Owner: `TBD` | PR: `TBD` | Requirement IDs: `TBD` | Test Case IDs: `TBD`
- [ ] **T-062** — Implement manual kill-switch command channel  
  - Estimate: `S` | Priority: `P0` | Status: `Not Started`  
  - Depends on: `T-039,T-040`  
  - Owner: `TBD` | PR: `TBD` | Requirement IDs: `TBD` | Test Case IDs: `TBD`
- [ ] **T-063** — Implement latency telemetry (signal->send->ack/fill) + percentile metrics  
  - Estimate: `M` | Priority: `P1` | Status: `Not Started`  
  - Depends on: `T-040,T-054`  
  - Owner: `TBD` | PR: `TBD` | Requirement IDs: `TBD` | Test Case IDs: `TBD`
- [ ] **T-064** — Implement degraded-mode guards (stale quotes/spread blowout/auto-halt)  
  - Estimate: `M` | Priority: `P0` | Status: `Not Started`  
  - Depends on: `T-038,T-043`  
  - Owner: `TBD` | PR: `TBD` | Requirement IDs: `TBD` | Test Case IDs: `TBD`

### Sprint 7
- [ ] **T-045** — Implement REST endpoints for runs and optimize  
  - Estimate: `M` | Priority: `P1` | Status: `Not Started`  
  - Depends on: `T-023`  
  - Owner: `TBD` | PR: `TBD` | Requirement IDs: `TBD` | Test Case IDs: `TBD`
- [ ] **T-046** — Implement WebSocket streaming for run updates  
  - Estimate: `S` | Priority: `P1` | Status: `Not Started`  
  - Depends on: `T-045`  
  - Owner: `TBD` | PR: `TBD` | Requirement IDs: `TBD` | Test Case IDs: `TBD`
- [ ] **T-047** — Implement API auth/token guard  
  - Estimate: `S` | Priority: `P1` | Status: `Not Started`  
  - Depends on: `T-045`  
  - Owner: `TBD` | PR: `TBD` | Requirement IDs: `TBD` | Test Case IDs: `TBD`
- [ ] **T-048** — Implement PySide6 run launcher + charts + blotter  
  - Estimate: `L` | Priority: `P1` | Status: `Not Started`  
  - Depends on: `T-023`  
  - Owner: `TBD` | PR: `TBD` | Requirement IDs: `TBD` | Test Case IDs: `TBD`
- [ ] **T-049** — Implement optimization leaderboard UI view  
  - Estimate: `M` | Priority: `P1` | Status: `Not Started`  
  - Depends on: `T-048`  
  - Owner: `TBD` | PR: `TBD` | Requirement IDs: `TBD` | Test Case IDs: `TBD`
- [ ] **T-050** — Implement reporting pipeline (md/html + repro footer)  
  - Estimate: `M` | Priority: `P1` | Status: `Not Started`  
  - Depends on: `T-021,T-024`  
  - Owner: `TBD` | PR: `TBD` | Requirement IDs: `TBD` | Test Case IDs: `TBD`

### Sprint 8
- [ ] **T-051** — Implement WAL journaling and replay routines  
  - Estimate: `L` | Priority: `P0` | Status: `Not Started`  
  - Depends on: `T-023`  
  - Owner: `TBD` | PR: `TBD` | Requirement IDs: `TBD` | Test Case IDs: `TBD`
- [ ] **T-052** — Implement crash recovery + stale lock cleanup  
  - Estimate: `M` | Priority: `P0` | Status: `Not Started`  
  - Depends on: `T-051`  
  - Owner: `TBD` | PR: `TBD` | Requirement IDs: `TBD` | Test Case IDs: `TBD`
- [ ] **T-053** — Implement security hardening checklist in CI  
  - Estimate: `S` | Priority: `P1` | Status: `Not Started`  
  - Depends on: `T-007,T-004`  
  - Owner: `TBD` | PR: `TBD` | Requirement IDs: `TBD` | Test Case IDs: `TBD`
- [ ] **T-054** — Implement observability metrics export + dashboards  
  - Estimate: `M` | Priority: `P1` | Status: `Not Started`  
  - Depends on: `T-005`  
  - Owner: `TBD` | PR: `TBD` | Requirement IDs: `TBD` | Test Case IDs: `TBD`
- [ ] **T-055** — Define SLOs and alert thresholds + runbook  
  - Estimate: `S` | Priority: `P1` | Status: `Not Started`  
  - Depends on: `T-054`  
  - Owner: `TBD` | PR: `TBD` | Requirement IDs: `TBD` | Test Case IDs: `TBD`
- [ ] **T-056** — Final closure: P0 gap audit + sign-off package  
  - Estimate: `M` | Priority: `P0` | Status: `Not Started`  
  - Depends on: `T-001..T-055`  
  - Owner: `TBD` | PR: `TBD` | Requirement IDs: `TBD` | Test Case IDs: `TBD`

---

## Tracker Table

| Task ID | Sprint | Task | Est | Depends On | Priority | Status | Owner | PR Link | Requirement IDs | Test Case IDs |
|---|---|---|---|---|---|---|---|---|---|---|
| T-001 | Sprint 1 | Setup canonical repository layout | M |  | P0 | Not Started | TBD | TBD | TBD | TBD |
| T-002 | Sprint 1 | Configure Python packaging and environment management | S | T-001 | P0 | Not Started | TBD | TBD | TBD | TBD |
| T-003 | Sprint 1 | Configure CMake build for cpp_core + tests + benchmarks | M | T-001 | P0 | Not Started | TBD | TBD | TBD | TBD |
| T-004 | Sprint 1 | Setup CI matrix (Windows/Linux) with lint/test gates | M | T-002,T-003 | P0 | Not Started | TBD | TBD | TBD | TBD |
| T-005 | Sprint 1 | Implement structured logging (Python + C++) with run_id correlation | M | T-003 | P0 | Not Started | TBD | TBD | TBD | TBD |
| T-006 | Sprint 1 | Implement typed config loader (TOML + env overlay) | S | T-002 | P0 | Not Started | TBD | TBD | TBD | TBD |
| T-007 | Sprint 1 | Implement secrets redaction helpers | S | T-006 | P0 | Not Started | TBD | TBD | TBD | TBD |
| T-008 | Sprint 1 | Create Nanobind module skeleton + version() + sum(array) | M | T-003 | P0 | Not Started | TBD | TBD | TBD | TBD |
| T-009 | Sprint 1 | Add bridge smoke tests (dtype/shape/error mapping) | S | T-008 | P0 | Not Started | TBD | TBD | TBD | TBD |
| T-010 | Sprint 2 | Implement market data loaders (parquet/csv) | M | T-002 | P0 | Not Started | TBD | TBD | TBD | TBD |
| T-011 | Sprint 2 | Implement normalization to market arrays contract | M | T-010 | P0 | Not Started | TBD | TBD | TBD | TBD |
| T-012 | Sprint 2 | Implement data validators (monotonic/duplicates/gaps/spread) | M | T-011 | P0 | Not Started | TBD | TBD | TBD | TBD |
| T-013 | Sprint 2 | Implement data version/hash lineage metadata | S | T-011 | P0 | Not Started | TBD | TBD | TBD | TBD |
| T-014 | Sprint 2 | Implement signal adapters with alignment checks | M | T-011 | P0 | Not Started | TBD | TBD | TBD | TBD |
| T-015 | Sprint 2 | Implement baseline signal generators (EMA, Williams %R) | M | T-014 | P0 | Not Started | TBD | TBD | TBD | TBD |
| T-016 | Sprint 3 | Implement C++ SignalEngine deterministic loop | L | T-008,T-011,T-014 | P0 | Not Started | TBD | TBD | TBD | TBD |
| T-017 | Sprint 3 | Implement entry/exit tie-break policy + docs | S | T-016 | P0 | Not Started | TBD | TBD | TBD | TBD |
| T-018 | Sprint 3 | Implement fill model (spread/slippage) | M | T-016 | P0 | Not Started | TBD | TBD | TBD | TBD |
| T-019 | Sprint 3 | Implement commission/swap hooks | S | T-018 | P1 | Not Started | TBD | TBD | TBD | TBD |
| T-020 | Sprint 3 | Implement portfolio accounting (balance/equity/pnl/margin) | L | T-016 | P0 | Not Started | TBD | TBD | TBD | TBD |
| T-021 | Sprint 3 | Implement outputs: trades, equity, metrics baseline | M | T-020 | P0 | Not Started | TBD | TBD | TBD | TBD |
| T-022 | Sprint 3 | Bind run_bars_signals via Nanobind + GIL release | M | T-016,T-008 | P0 | Not Started | TBD | TBD | TBD | TBD |
| T-023 | Sprint 3 | Implement persistence tables (runs/configs/metrics/trades/artifacts) | M | T-013 | P0 | Not Started | TBD | TBD | TBD | TBD |
| T-024 | Sprint 3 | Implement reproducibility bundle writer | S | T-023 | P0 | Not Started | TBD | TBD | TBD | TBD |
| T-025 | Sprint 4 | Implement C++ BatchRunner thread-pool scheduling | L | T-016 | P0 | Not Started | TBD | TBD | TBD | TBD |
| T-026 | Sprint 4 | Implement deterministic per-run seed assignment | S | T-025 | P0 | Not Started | TBD | TBD | TBD | TBD |
| T-027 | Sprint 4 | Implement top-K reduction + leaderboard | M | T-025 | P0 | Not Started | TBD | TBD | TBD | TBD |
| T-028 | Sprint 4 | Implement Python run_batch orchestration | M | T-022,T-025 | P0 | Not Started | TBD | TBD | TBD | TBD |
| T-029 | Sprint 4 | Implement WFO orchestration scaffold | M | T-028 | P1 | Not Started | TBD | TBD | TBD | TBD |
| T-030 | Sprint 4 | Implement optimization_jobs/results persistence | S | T-023,T-028 | P0 | Not Started | TBD | TBD | TBD | TBD |
| T-031 | Sprint 4 | Add perf benchmarks (single/batch/bridge overhead) | M | T-025,T-022 | P0 | Not Started | TBD | TBD | TBD | TBD |
| T-032 | Sprint 5 | Implement EventEngine event queue + dispatch | L | T-016 | P1 | Not Started | TBD | TBD | TBD | TBD |
| T-033 | Sprint 5 | Implement pending orders lifecycle (limit/stop) | M | T-032 | P1 | Not Started | TBD | TBD | TBD | TBD |
| T-034 | Sprint 5 | Implement modify/cancel + partial close | M | T-033 | P1 | Not Started | TBD | TBD | TBD | TBD |
| T-035 | Sprint 5 | Implement intrabar SL/TP policy options | M | T-033 | P1 | Not Started | TBD | TBD | TBD | TBD |
| T-036 | Sprint 5 | Ensure signal/event output schema parity | S | T-032,T-021 | P1 | Not Started | TBD | TBD | TBD | TBD |
| T-037 | Sprint 5 | Add mode comparison diagnostics | S | T-036 | P1 | Not Started | TBD | TBD | TBD | TBD |
| T-038 | Sprint 6 | Implement RiskGovernor hard limits + exposure checks | M | T-020 | P0 | Not Started | TBD | TBD | TBD | TBD |
| T-039 | Sprint 6 | Implement circuit breaker + kill switch | S | T-038 | P0 | Not Started | TBD | TBD | TBD | TBD |
| T-040 | Sprint 6 | Implement MT5 ZeroMQ protocol contracts | L | T-006 | P0 | Not Started | TBD | TBD | TBD | TBD |
| T-041 | Sprint 6 | Implement gateway reconnect + heartbeat | M | T-040 | P0 | Not Started | TBD | TBD | TBD | TBD |
| T-042 | Sprint 6 | Implement startup reconciliation (positions/orders/account) | M | T-041 | P0 | Not Started | TBD | TBD | TBD | TBD |
| T-043 | Sprint 6 | Implement fail-safe halt on ambiguity/disconnect | S | T-042,T-039 | P0 | Not Started | TBD | TBD | TBD | TBD |
| T-044 | Sprint 6 | Implement paper mode parity engine + realism profiles | M | T-022 | P1 | Not Started | TBD | TBD | TBD | TBD |
| T-045 | Sprint 7 | Implement REST endpoints for runs and optimize | M | T-023 | P1 | Not Started | TBD | TBD | TBD | TBD |
| T-046 | Sprint 7 | Implement WebSocket streaming for run updates | S | T-045 | P1 | Not Started | TBD | TBD | TBD | TBD |
| T-047 | Sprint 7 | Implement API auth/token guard | S | T-045 | P1 | Not Started | TBD | TBD | TBD | TBD |
| T-048 | Sprint 7 | Implement PySide6 run launcher + charts + blotter | L | T-023 | P1 | Not Started | TBD | TBD | TBD | TBD |
| T-049 | Sprint 7 | Implement optimization leaderboard UI view | M | T-048 | P1 | Not Started | TBD | TBD | TBD | TBD |
| T-050 | Sprint 7 | Implement reporting pipeline (md/html + repro footer) | M | T-021,T-024 | P1 | Not Started | TBD | TBD | TBD | TBD |
| T-051 | Sprint 8 | Implement WAL journaling and replay routines | L | T-023 | P0 | Not Started | TBD | TBD | TBD | TBD |
| T-052 | Sprint 8 | Implement crash recovery + stale lock cleanup | M | T-051 | P0 | Not Started | TBD | TBD | TBD | TBD |
| T-053 | Sprint 8 | Implement security hardening checklist in CI | S | T-007,T-004 | P1 | Not Started | TBD | TBD | TBD | TBD |
| T-054 | Sprint 8 | Implement observability metrics export + dashboards | M | T-005 | P1 | Not Started | TBD | TBD | TBD | TBD |
| T-055 | Sprint 8 | Define SLOs and alert thresholds + runbook | S | T-054 | P1 | Not Started | TBD | TBD | TBD | TBD |
| T-056 | Sprint 8 | Final closure: P0 gap audit + sign-off package | M | T-001..T-055 | P0 | Not Started | TBD | TBD | TBD | TBD |
| T-057 | Sprint 6 | Implement idempotent order keys for live order submission | M | T-040 | P0 | Not Started | TBD | TBD | TBD | TBD |
| T-058 | Sprint 6 | Implement reconnect retry deduplication window | M | T-041,T-057 | P0 | Not Started | TBD | TBD | TBD | TBD |
| T-059 | Sprint 6 | Implement clock-sync guard and drift thresholds | S | T-041 | P0 | Not Started | TBD | TBD | TBD | TBD |
| T-060 | Sprint 6 | Implement broker rules snapshot cache (min lot/step/stops/sessions) | M | T-040 | P0 | Not Started | TBD | TBD | TBD | TBD |
| T-061 | Sprint 6 | Implement daily reconciliation report (local vs broker diffs) | M | T-042 | P0 | Not Started | TBD | TBD | TBD | TBD |
| T-062 | Sprint 6 | Implement manual kill-switch command channel | S | T-039,T-040 | P0 | Not Started | TBD | TBD | TBD | TBD |
| T-063 | Sprint 6 | Implement latency telemetry (signal->send->ack/fill) + percentile metrics | M | T-040,T-054 | P1 | Not Started | TBD | TBD | TBD | TBD |
| T-064 | Sprint 6 | Implement degraded-mode guards (stale quotes/spread blowout/auto-halt) | M | T-038,T-043 | P0 | Not Started | TBD | TBD | TBD | TBD |
