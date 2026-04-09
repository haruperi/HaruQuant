# Implementation Plan: HaruQuant Agentic AI System

**Document Version:** 1.0.0  
**Derived From:** SRS v3.1.1, Design Specification / System Architecture v1.1.0, Schemas v1.0.0  
**System:** HaruQuant Autonomous Trading Platform  
**Status:** Execution-Ready Work Breakdown  
**Planning Style:** Atomic implementation checklist with requirement traceability, unit-test expectations, and suggested commit messages

---

## 1. Purpose

This implementation plan converts the approved requirements, architecture, and schema specifications into a phase-by-phase build checklist. It is intentionally granular: each task is small, atomic, and independently completable. Every task includes requirement references, minimum testing expectations, and a suggested commit message template.

This plan follows the recommended implementation order:

1. Governance and skeleton
2. Deterministic safety core
3. Agent runtime
4. Live control plane
5. Portfolio and promotion
6. Migration and hardening

---

## 2. Implementation Conventions

### 2.1 Task Status Legend
- [ ] Not started
- [x] Done
- [~] In progress
- [!] Blocked

### 2.2 Requirement Reference Format
- `FR-*` = Functional requirement
- `NFR-*` = Non-functional requirement
- `INV-*` = Invariant / governing principle
- `PROM-*` = Promotion requirement
- `COMP-*` = Compliance requirement
- `TTL-*` = Freshness / TTL requirement

### 2.3 Definition of Done for Every Task
A task is only complete when all are true:
- code implemented
- tests added and passing
- logs/metrics added where relevant
- schema/contract compatibility verified where relevant
- docs/readme touched where relevant
- commit recorded with clear message

### 2.4 Recommended Repository Streams
- `backend/orchestration`
- `backend/agents`
- `backend/services`
- `backend/contracts`
- `backend/mcp`
- `backend/db`
- `backend/api`
- `frontend/dashboard`
- `infra`
- `tests/unit`
- `tests/integration`
- `tests/scenario`
- `tests/chaos`
- `tests/security`
- `tests/replay`

---

## 3. Phase Overview

| Phase | Objective | Exit Gate |
|---|---|---|
| Phase 0 | Delivery foundations | repo standards, CI, envs, coding/test conventions ready |
| Phase 1 | Governance and skeleton | workflow engine, policy service, schema registry, DB baseline exist |
| Phase 2 | Deterministic safety core | risk, kill switch, execution validation, MT5 boundary, reconciliation exist |
| Phase 3 | Agent runtime | core agents, ADK runtime, prompt/version registry, evaluator wiring exist |
| Phase 4 | Live control plane | execution path, approvals, incidents, replay, audit export exist |
| Phase 5 | Portfolio and promotion | portfolio analytics, lifecycle governance, promotion workflows exist |
| Phase 6 | Migration and hardening | shadow mode, replay validation, chaos/security/perf readiness complete |

---

## 4. Cross-Cutting Global Backlog

## 4.1 Program Setup

- [x] Create monorepo folder structure for services, contracts, MCP, UI, infra, tests.  
  **Refs:** FR-018, FR-023, NFR-010, NFR-011  
  **Unit tests:** none  
  **Commit:** `chore(repo): initialize monorepo structure for agentic system`

- [ ] Add Python project configuration, formatter, linter, import sorter, type checker.  
  **Refs:** NFR-010, NFR-011  
  **Unit tests:** CI smoke check for lint/type commands  
  **Commit:** `chore(devx): add formatter lint and type-check configuration`

- [x] Add JS/TS workspace config for dashboard and shared types.  
  **Refs:** FR-064, NFR-010  
  **Unit tests:** frontend typecheck CI  
  **Commit:** `chore(frontend): initialize dashboard workspace and shared typing`

- [ ] Add pre-commit hooks for formatting, linting, and secret scanning.  
  **Refs:** NFR-015, NFR-016  
  **Unit tests:** pre-commit smoke test in CI  
  **Commit:** `chore(security): add pre-commit checks and secret scanning`

- [x] Add baseline CI pipeline for backend, frontend, migrations, and tests.  
  **Refs:** NFR-010, NFR-011, NFR-018  
  **Unit tests:** CI self-check workflow  
  **Commit:** `chore(ci): add baseline pipeline for build lint typecheck and tests`

- [x] Create environment templates for dev, test, paper, staging, prod.  
  **Refs:** FR-001, FR-002, COMP-002  
  **Unit tests:** env loader parsing test  
  **Commit:** `chore(config): add environment templates for all deployment stages`

- [x] Create shared configuration loader with environment-scoped validation.  
  **Refs:** FR-001, FR-002, NFR-015  
  **Unit tests:** valid/invalid config parsing tests  
  **Commit:** `feat(config): add validated environment-aware settings loader`

## 4.2 Shared Engineering Foundations

- [x] Create shared error model package for domain, validation, policy, broker, and infra errors.  
  **Refs:** FR-076, NFR-002  
  **Unit tests:** exception serialization/deserialization tests  
  **Commit:** `feat(core): add shared domain error hierarchy`

- [x] Create shared logging package with workflow_id/correlation_id propagation.  
  **Refs:** FR-063, NFR-004  
  **Unit tests:** log context injection tests  
  **Commit:** `feat(obs): add structured logging with workflow correlation context`

- [x] Create shared telemetry package for metrics, spans, and event attributes.  
  **Refs:** NFR-004, NFR-005  
  **Unit tests:** metric registration tests  
  **Commit:** `feat(obs): add telemetry helpers for metrics and tracing`

- [x] Create shared time/freshness utility package for TTL checks and time-source abstraction.  
  **Refs:** FR-070, TTL-011, TTL-012  
  **Unit tests:** ttl evaluation and clock abstraction tests  
  **Commit:** `feat(core): add freshness and ttl utility module`

- [x] Create shared identifier generator for workflow, proposal, decision, intent, receipt, incident, replay IDs.  
  **Refs:** FR-026, FR-073  
  **Unit tests:** uniqueness and prefix format tests  
  **Commit:** `feat(core): add canonical identifier generation utilities`

- [x] Create shared optimistic concurrency helper for versioned records.  
  **Refs:** FR-009, CS/DB concurrency rules  
  **Unit tests:** stale version conflict tests  
  **Commit:** `feat(core): add optimistic concurrency helpers`

---

## 5. Phase 0 — Delivery Foundations

### 5.1 Architecture Decision Record Stream

- [x] Create ADR template.  
  **Refs:** NFR-018, NFR-020  
  **Unit tests:** none  
  **Commit:** `docs(adr): add architecture decision record template`

- [x] Write ADR for event backbone choice.  
  **Refs:** NFR-006, NFR-007  
  **Unit tests:** none  
  **Commit:** `docs(adr): record event backbone decision`

- [x] Write ADR for object store choice.  
  **Refs:** FR-072, FR-074, NFR-020  
  **Unit tests:** none  
  **Commit:** `docs(adr): record artifact object store decision`

- [x] Write ADR for vector store choice.  
  **Refs:** FR-052, FR-068  
  **Unit tests:** none  
  **Commit:** `docs(adr): record vector store decision`

- [x] Write ADR for REST vs GraphQL dashboard read model.  
  **Refs:** FR-064, FR-065, NFR-007  
  **Unit tests:** none  
  **Commit:** `docs(adr): record operator api query strategy`

### 5.2 Delivery Policy

- [x] Create branch naming and commit convention guide.  
  **Refs:** NFR-010  
  **Unit tests:** none  
  **Commit:** `docs(devx): add branch and commit conventions`

- [x] Create test-layer policy document for unit/integration/scenario/chaos/security/replay.  
  **Refs:** NFR-018  
  **Unit tests:** none  
  **Commit:** `docs(test): add multi-layer testing policy`

- [x] Create requirement traceability template for PRs.  
  **Refs:** FR-023, NFR-018  
  **Unit tests:** PR template presence check  
  **Commit:** `docs(process): add requirement traceability pull request template`

---

## 6. Phase 1 — Governance and Skeleton

### 6.1 Canonical Contracts Package

- [x] Create `contracts/` repository structure for every canonical contract family.  
  **Refs:** FR-025, FR-026, CS-001 to CS-006  
  **Unit tests:** folder existence smoke test  
  **Commit:** `feat(contracts): scaffold canonical contract package structure`

- [x] Implement shared canonical envelope model.  
  **Refs:** FR-026, CS-002  
  **Unit tests:** required-field validation tests  
  **Commit:** `feat(contracts): add canonical envelope model`

- [x] Implement `WorkflowIntent` schema/model/examples.  
  **Refs:** FR-025, FR-026  
  **Unit tests:** valid/invalid payload tests  
  **Commit:** `feat(contracts): implement workflow intent contract`

- [x] Implement `WorkflowPlan` schema/model/examples.  
  **Refs:** FR-015, FR-025  
  **Unit tests:** valid/invalid payload tests  
  **Commit:** `feat(contracts): implement workflow plan contract`

- [x] Implement `TradeHypothesis` schema/model/examples.  
  **Refs:** FR-039, FR-040, FR-041  
  **Unit tests:** required-field and enum tests  
  **Commit:** `feat(contracts): implement trade hypothesis contract`

- [x] Implement `TradeProposal` schema/model/examples.  
  **Refs:** FR-041, FR-043  
  **Unit tests:** transformation compatibility tests  
  **Commit:** `feat(contracts): implement trade proposal contract`

- [x] Implement `RiskAssessmentRequest` schema/model/examples.  
  **Refs:** FR-028 to FR-031  
  **Unit tests:** freshness and required-context validation tests  
  **Commit:** `feat(contracts): implement risk assessment request contract`

- [x] Implement `RiskAssessmentDecision` schema/model/examples.  
  **Refs:** FR-032, FR-033, FR-034  
  **Unit tests:** decision enum and constraint validation tests  
  **Commit:** `feat(contracts): implement risk assessment decision contract`

- [x] Implement `ExecutionIntent` schema/model/examples.  
  **Refs:** FR-056, FR-059  
  **Unit tests:** idempotency and linkage validation tests  
  **Commit:** `feat(contracts): implement execution intent contract`

- [x] Implement `ExecutionReceipt` schema/model/examples.  
  **Refs:** FR-059, FR-060  
  **Unit tests:** normalized receipt parsing tests  
  **Commit:** `feat(contracts): implement execution receipt contract`

- [x] Implement `ObservationEvent` schema/model/examples.  
  **Refs:** FR-061, FR-063  
  **Unit tests:** source/severity validation tests  
  **Commit:** `feat(contracts): implement observation event contract`

- [x] Implement `EvaluationReport` schema/model/examples.  
  **Refs:** FR-055, FR-072  
  **Unit tests:** rubric-score validation tests  
  **Commit:** `feat(contracts): implement evaluation report contract`

- [x] Implement `IncidentAlert` schema/model/examples.  
  **Refs:** FR-011, FR-062  
  **Unit tests:** severity/state validation tests  
  **Commit:** `feat(contracts): implement incident alert contract`

- [x] Implement `OverrideRequest` schema/model/examples.  
  **Refs:** FR-037, FR-038  
  **Unit tests:** dual-auth field validation tests  
  **Commit:** `feat(contracts): implement override request contract`

- [x] Implement `OverrideDecision` schema/model/examples.  
  **Refs:** FR-037, FR-038  
  **Unit tests:** approval outcome validation tests  
  **Commit:** `feat(contracts): implement override decision contract`

- [x] Implement `ReplayBundle` schema/model/examples.  
  **Refs:** FR-072, FR-073, FR-074  
  **Unit tests:** completeness and manifest validation tests  
  **Commit:** `feat(contracts): implement replay bundle contract`

- [x] Add canonical serialization helpers.  
  **Refs:** CS-004, CS-006  
  **Unit tests:** deterministic sort and round-trip tests  
  **Commit:** `feat(contracts): add canonical serialization utilities`

### 6.2 Schema Registry

- [x] Create schema registry domain model.  
  **Refs:** FR-027, CS-003  
  **Unit tests:** registry record validation tests  
  **Commit:** `feat(schema-registry): add registry domain models`

- [x] Create schema registry persistence table/model.  
  **Refs:** FR-027, NFR-020  
  **Unit tests:** ORM mapping tests  
  **Commit:** `feat(schema-registry): add persistence model for schema registry`

- [x] Implement schema version resolution service.  
  **Refs:** FR-027, CS-003  
  **Unit tests:** active/deprecated version lookup tests  
  **Commit:** `feat(schema-registry): implement version resolution service`

- [x] Implement runtime contract validator against registry.  
  **Refs:** INV-003, FR-021, CS-005  
  **Unit tests:** malformed contract rejection tests  
  **Commit:** `feat(schema-registry): implement runtime contract validation`

- [x] Implement registry seed loader for initial active schemas.  
  **Refs:** FR-025, FR-027  
  **Unit tests:** seed loading tests  
  **Commit:** `feat(schema-registry): add bootstrap schema seeds`

### 6.3 Database Baseline

- [x] Create Alembic or migration framework baseline.  
  **Refs:** NFR-020  
  **Unit tests:** migration smoke test  
  **Commit:** `feat(db): initialize migration framework`

- [x] Create database namespaces/schema bootstrap.  
  **Refs:** DB namespaces in Schemas.md  
  **Unit tests:** migration apply test  
  **Commit:** `feat(db): add core risk gov audit research and ref schemas`

- [x] Create `core.workflows` table migration.  
  **Refs:** FR-008, FR-015  
  **Unit tests:** create/insert/select tests  
  **Commit:** `feat(db): add workflows table`

- [x] Create `core.workflow_transitions` table migration.  
  **Refs:** FR-009, FR-072  
  **Unit tests:** FK/index tests  
  **Commit:** `feat(db): add workflow transitions table`

- [x] Create `core.workflow_steps` table migration.  
  **Refs:** FR-015, FR-072  
  **Unit tests:** FK/index tests  
  **Commit:** `feat(db): add workflow steps table`

- [x] Create `core.trade_hypotheses` table migration.  
  **Refs:** FR-039, FR-040, FR-072  
  **Unit tests:** insert and constraint tests  
  **Commit:** `feat(db): add trade hypotheses table`

- [x] Create `core.trade_proposals` table migration.  
  **Refs:** FR-041, FR-043, FR-072  
  **Unit tests:** FK/index tests  
  **Commit:** `feat(db): add trade proposals table`

- [x] Create `risk.risk_assessment_requests` table migration.  
  **Refs:** FR-028 to FR-031  
  **Unit tests:** insert and FK tests  
  **Commit:** `feat(db): add risk assessment requests table`

- [x] Create `risk.risk_decisions` table migration.  
  **Refs:** FR-032 to FR-034  
  **Unit tests:** decision enum and unique-token tests  
  **Commit:** `feat(db): add risk decisions table`

- [x] Create `risk.risk_constraints` table migration.  
  **Refs:** FR-033  
  **Unit tests:** FK/index tests  
  **Commit:** `feat(db): add risk constraints table`

- [x] Create `core.execution_intents` table migration.  
  **Refs:** FR-056, FR-059, FR-060  
  **Unit tests:** idempotency uniqueness tests  
  **Commit:** `feat(db): add execution intents table`

- [x] Create `core.execution_send_attempts` table migration.  
  **Refs:** FR-060, FR-076  
  **Unit tests:** unique attempt number tests  
  **Commit:** `feat(db): add execution send attempts table`

- [x] Create `core.execution_receipts` table migration.  
  **Refs:** FR-059, FR-060  
  **Unit tests:** normalized receipt insert tests  
  **Commit:** `feat(db): add execution receipts table`

- [x] Create `core.reconciliation_runs` table migration.  
  **Refs:** FR-077  
  **Unit tests:** insert and conflict flag tests  
  **Commit:** `feat(db): add reconciliation runs table`

- [x] Create `core.broker_positions` table migration.  
  **Refs:** FR-048, FR-061  
  **Unit tests:** snapshot upsert tests  
  **Commit:** `feat(db): add broker positions table`

- [x] Create `core.observations` table migration.  
  **Refs:** FR-061, FR-063  
  **Unit tests:** severity/source query tests  
  **Commit:** `feat(db): add observations table`

- [x] Create `core.evaluation_reports` table migration.  
  **Refs:** FR-055, FR-072  
  **Unit tests:** insert and index tests  
  **Commit:** `feat(db): add evaluation reports table`

- [x] Create `core.incidents` table migration.  
  **Refs:** FR-011, FR-062  
  **Unit tests:** state enum tests  
  **Commit:** `feat(db): add incidents table`

- [x] Create governance table migrations (`kill_switch_events`, `approvals`, `approval_votes`, `override_requests`, `override_decisions`, `policies`, `compliance_profiles`, `strategy_registry`, `strategy_promotions`).  
  **Refs:** FR-035 to FR-038, FR-044 to FR-046, COMP-001 to COMP-013  
  **Unit tests:** FK, unique distinct-vote, policy version tests  
  **Commit:** `feat(db): add governance and strategy lifecycle tables`

- [x] Create research and audit tables (`evidence_bundles`, `trajectory_logs`, `replay_bundles`, `legal_holds`).  
  **Refs:** FR-052 to FR-055, FR-072 to FR-074, NFR-004, NFR-019, NFR-020  
  **Unit tests:** insert and retention/legal-hold tests  
  **Commit:** `feat(db): add research and audit tables`

- [x] Create reference/lookup seed tables for workflow/proposal/decision/approval/incident/kill-switch/mode/strategy states.  
  **Refs:** FR-001, FR-008, FR-010 to FR-013, FR-044  
  **Unit tests:** seed integrity tests  
  **Commit:** `feat(db): add reference state lookup seeds`

### 6.4 Repository Layer

- [x] Implement workflow repository.  
  **Refs:** FR-008, FR-009  
  **Unit tests:** CRUD and optimistic lock tests  
  **Commit:** `feat(repo): add workflow repository`

- [x] Implement proposal repository.  
  **Refs:** FR-010, FR-041  
  **Unit tests:** state transition persistence tests  
  **Commit:** `feat(repo): add proposal repository`

- [x] Implement risk repository.  
  **Refs:** FR-028 to FR-034  
  **Unit tests:** decision fetch-by-token and expiry tests  
  **Commit:** `feat(repo): add risk repositories`

- [x] Implement execution repository.  
  **Refs:** FR-059, FR-060, FR-077  
  **Unit tests:** idempotency and attempt persistence tests  
  **Commit:** `feat(repo): add execution repositories`

- [x] Implement governance repository.  
  **Refs:** FR-035 to FR-038  
  **Unit tests:** approval vote distinctness tests  
  **Commit:** `feat(repo): add governance repositories`

- [x] Implement research/audit repository.  
  **Refs:** FR-052, FR-072 to FR-074  
  **Unit tests:** replay/legal-hold repository tests  
  **Commit:** `feat(repo): add research and audit repositories`

### 6.5 Workflow Skeleton

- [x] Create workflow domain state enums.  
  **Refs:** FR-008, FR-009  
  **Unit tests:** enum coverage tests  
  **Commit:** `feat(workflow): add workflow state definitions`

- [x] Create workflow transition rule map.  
  **Refs:** FR-005 to FR-009  
  **Unit tests:** allowed/disallowed transition tests  
  **Commit:** `feat(workflow): add workflow transition rule map`

- [x] Create trade proposal transition rule map.  
  **Refs:** FR-010  
  **Unit tests:** allowed/disallowed proposal transitions  
  **Commit:** `feat(workflow): add proposal transition rule map`

- [x] Create incident transition rule map.  
  **Refs:** FR-011  
  **Unit tests:** incident state transition tests  
  **Commit:** `feat(workflow): add incident transition rule map`

- [x] Create kill-switch transition rule map.  
  **Refs:** FR-012, FR-013  
  **Unit tests:** unauthorized recovery transition tests  
  **Commit:** `feat(workflow): add kill switch transition rule map`

- [x] Implement workflow FSM validator service.  
  **Refs:** FR-006, FR-009, NFR-012  
  **Unit tests:** phase skipping rejection tests  
  **Commit:** `feat(workflow): implement workflow state validator`

- [x] Implement workflow creation service.  
  **Refs:** FR-014, FR-015  
  **Unit tests:** required-objective/constraints/tool declarations tests  
  **Commit:** `feat(workflow): implement workflow creation service`

- [x] Implement workflow transition persistence service.  
  **Refs:** FR-072, NFR-004  
  **Unit tests:** transition append-only behavior tests  
  **Commit:** `feat(workflow): implement workflow transition logger`

- [x] Implement workflow step recorder.  
  **Refs:** FR-015, FR-072  
  **Unit tests:** ordered-step persistence tests  
  **Commit:** `feat(workflow): implement workflow step recorder`

### 6.6 Policy and Approval Skeleton

- [x] Implement policy domain models (bundle, version, scope, enforcement result).  
  **Refs:** FR-035, FR-038, COMP-001  
  **Unit tests:** policy model validation tests  
  **Commit:** `feat(policy): add policy domain models`

- [x] Implement compliance profile domain models.  
  **Refs:** COMP-001 to COMP-013  
  **Unit tests:** profile parsing tests  
  **Commit:** `feat(policy): add compliance profile models`

- [x] Implement policy resolution service by environment/account/strategy/symbol/workflow/role.  
  **Refs:** FR-001, FR-002, FR-003  
  **Unit tests:** scoped resolution tests  
  **Commit:** `feat(policy): implement scoped policy resolution`

- [x] Implement approval domain models and FSM.  
  **Refs:** FR-035, FR-037, FR-038  
  **Unit tests:** approval transition tests  
  **Commit:** `feat(approval): add approval domain model and state machine`

- [x] Implement approval creation service.  
  **Refs:** FR-038  
  **Unit tests:** approval creation and expiry tests  
  **Commit:** `feat(approval): implement approval request creation`

- [x] Implement approval vote service with distinct approver enforcement.  
  **Refs:** FR-037, COMP-012  
  **Unit tests:** duplicate voter rejection tests  
  **Commit:** `feat(approval): implement distinct approver voting rules`

- [x] Implement override request skeleton.  
  **Refs:** FR-037  
  **Unit tests:** missing reason/rationale rejection tests  
  **Commit:** `feat(approval): implement override request skeleton`

### 6.7 API and Dashboard Skeleton

- [x] Create FastAPI app skeleton and dependency wiring.  
  **Refs:** FR-064 to FR-067  
  **Unit tests:** app startup tests  
  **Commit:** `feat(api): initialize operator api application`

- [x] Add authn/authz middleware skeleton.  
  **Refs:** FR-035, NFR-015  
  **Unit tests:** unauthorized route tests  
  **Commit:** `feat(api): add authentication and authorization middleware`

- [x] Add health endpoints for app, db, redis, schema registry.  
  **Refs:** FR-061, NFR-004  
  **Unit tests:** health endpoint response tests  
  **Commit:** `feat(api): add service health endpoints`

- [x] Initialize dashboard shell with navigation, auth guard, and live status layout.  
  **Refs:** FR-064, FR-065  
  **Unit tests:** component render tests  
  **Commit:** `feat(ui): create dashboard shell and navigation`

- [x] Add placeholder pages for workflows, proposals, risk, approvals, incidents, replay, strategies.  
  **Refs:** FR-064 to FR-067  
  **Unit tests:** route smoke tests  
  **Commit:** `feat(ui): add operator page skeletons`

### 6.8 Phase 1 Exit Criteria

- [x] All canonical contract families implemented and registry-backed.  
- [x] Core DB schema applied in fresh environment.  
- [x] Workflow FSM validation working.  
- [x] Policy and approval services resolve and persist.  
- [x] API and dashboard shells boot successfully.  
- [x] Unit test suite for contracts, FSMs, repositories, policy baseline green.  

---

## 7. Phase 2 — Deterministic Safety Core

### 7.1 Freshness and Snapshot Infrastructure

- [x] Implement market snapshot model with TTL metadata.  
  **Refs:** FR-070, TTL-020  
  **Unit tests:** hot/warm/cool freshness tests  
  **Commit:** `feat(risk): add market snapshot model with ttl metadata`

- [x] Implement account snapshot model with TTL metadata.  
  **Refs:** FR-031, FR-070  
  **Unit tests:** account snapshot expiry tests  
  **Commit:** `feat(risk): add account snapshot freshness model`

- [x] Implement portfolio snapshot model with TTL metadata.  
  **Refs:** FR-031, FR-048, FR-070  
  **Unit tests:** portfolio snapshot expiry tests  
  **Commit:** `feat(risk): add portfolio snapshot freshness model`

- [x] Implement symbol metadata cache model.  
  **Refs:** FR-057  
  **Unit tests:** symbol metadata cache retrieval tests  
  **Commit:** `feat(exec): add symbol metadata cache model`

- [x] Implement freshness evaluator utility against Board baselines.  
  **Refs:** FR-029, FR-070, TTL-011, TTL-012  
  **Unit tests:** board TTL baseline tests  
  **Commit:** `feat(core): implement board-baseline freshness evaluator`

### 7.2 Risk Engine Core

- [x] Implement risk request assembler from proposal + snapshots + policy.  
  **Refs:** FR-028 to FR-031  
  **Unit tests:** request assembly completeness tests  
  **Commit:** `feat(risk): implement risk request assembler`

- [x] Implement position and exposure calculators.  
  **Refs:** FR-031, FR-048  
  **Unit tests:** gross/net exposure tests  
  **Commit:** `feat(risk): implement exposure calculators`

- [x] Implement per-symbol concentration calculator.  
  **Refs:** FR-031  
  **Unit tests:** concentration threshold tests  
  **Commit:** `feat(risk): implement per-symbol concentration checks`

- [x] Implement per-currency concentration calculator.  
  **Refs:** FR-031  
  **Unit tests:** multi-currency concentration tests  
  **Commit:** `feat(risk): implement per-currency concentration checks`

- [x] Implement per-strategy-family concentration calculator.  
  **Refs:** FR-031  
  **Unit tests:** family concentration tests  
  **Commit:** `feat(risk): implement strategy family concentration checks`

- [x] Implement margin utilization calculator.  
  **Refs:** FR-031, FR-051  
  **Unit tests:** free-margin utilization tests  
  **Commit:** `feat(risk): implement margin utilization calculator`

- [x] Implement volatility-adjusted sizing calculator.  
  **Refs:** FR-031  
  **Unit tests:** size normalization tests  
  **Commit:** `feat(risk): implement volatility adjusted sizing`

- [ ] Implement correlation concentration calculator.  
  **Refs:** FR-031, FR-048  
  **Unit tests:** pair and portfolio correlation tests  
  **Commit:** `feat(risk): implement correlation concentration checks`

- [ ] Implement drawdown state calculator.  
  **Refs:** FR-031  
  **Unit tests:** drawdown band classification tests  
  **Commit:** `feat(risk): implement drawdown state calculator`

- [ ] Implement regime restriction evaluator.  
  **Refs:** FR-031  
  **Unit tests:** regime allow/deny tests  
  **Commit:** `feat(risk): implement regime restriction evaluation`

- [ ] Implement session restriction and blackout evaluator.  
  **Refs:** FR-031, FR-066  
  **Unit tests:** session window and blackout tests  
  **Commit:** `feat(risk): implement session and blackout checks`

- [ ] Implement spread/slippage pre-check evaluator.  
  **Refs:** FR-031, FR-057  
  **Unit tests:** spread threshold rejection tests  
  **Commit:** `feat(risk): implement spread and slippage prechecks`

- [ ] Implement operating mode compatibility evaluator.  
  **Refs:** FR-001 to FR-004, FR-031  
  **Unit tests:** mode mismatch rejection tests  
  **Commit:** `feat(risk): implement operating mode compatibility checks`

- [ ] Implement compliance profile compatibility evaluator.  
  **Refs:** COMP-010, COMP-011  
  **Unit tests:** profile resolution/blocking tests  
  **Commit:** `feat(risk): implement compliance profile enforcement in risk path`

- [ ] Implement risk decision composer (`APPROVE`, `APPROVE_WITH_LIMITS`, `REJECT`, `FORCE_EXIT`).  
  **Refs:** FR-032, FR-033  
  **Unit tests:** decision outcome matrix tests  
  **Commit:** `feat(risk): implement risk decision composer`

- [ ] Implement risk rationale/provenance packer.  
  **Refs:** FR-034, FR-073  
  **Unit tests:** rationale/provenance completeness tests  
  **Commit:** `feat(risk): persist rationale and provenance fields`

- [ ] Implement risk decision persistence service.  
  **Refs:** FR-034, FR-072  
  **Unit tests:** decision save and constraint persistence tests  
  **Commit:** `feat(risk): implement risk decision persistence`

- [ ] Implement risk-decision invalidation rules for material proposal change.  
  **Refs:** FR-029, TTL-011  
  **Unit tests:** changed proposal invalidation tests  
  **Commit:** `feat(risk): implement proposal-change invalidation rules`

- [ ] Implement risk-decision expiry handling.  
  **Refs:** FR-029, FR-030  
  **Unit tests:** expired decision rejection tests  
  **Commit:** `feat(risk): implement decision expiry enforcement`

### 7.3 Kill Switch

- [ ] Implement kill-switch domain model and state machine.  
  **Refs:** FR-012, FR-013, NFR-001  
  **Unit tests:** transition authorization tests  
  **Commit:** `feat(safety): add kill switch domain state machine`

- [ ] Implement global new-entry block evaluator.  
  **Refs:** NFR-001, NFR-002  
  **Unit tests:** new-entry blocked when triggered tests  
  **Commit:** `feat(safety): enforce new-entry block under kill switch`

- [ ] Implement hard-trigger recovery dual-authorization rule.  
  **Refs:** FR-013, COMP-012, Board baseline  
  **Unit tests:** single approver recovery rejection tests  
  **Commit:** `feat(safety): require dual auth for hard trigger recovery`

- [ ] Implement kill-switch event persistence and audit logging.  
  **Refs:** FR-072, NFR-019  
  **Unit tests:** event append-only tests  
  **Commit:** `feat(safety): persist and audit kill switch events`

### 7.4 Execution Readiness Validator

- [ ] Implement market open validation.  
  **Refs:** FR-057  
  **Unit tests:** closed market rejection tests  
  **Commit:** `feat(exec): implement market-open validation`

- [ ] Implement symbol tradability validation.  
  **Refs:** FR-057  
  **Unit tests:** non-tradable symbol rejection tests  
  **Commit:** `feat(exec): implement symbol tradability validation`

- [ ] Implement price freshness validation.  
  **Refs:** FR-057, FR-070  
  **Unit tests:** stale price rejection tests  
  **Commit:** `feat(exec): implement price freshness validation`

- [ ] Implement stop/freeze-level validation.  
  **Refs:** FR-057  
  **Unit tests:** invalid stop distance tests  
  **Commit:** `feat(exec): implement stop and freeze level validation`

- [ ] Implement fill-mode compatibility validation.  
  **Refs:** FR-057  
  **Unit tests:** unsupported fill mode tests  
  **Commit:** `feat(exec): implement fill mode compatibility validation`

- [ ] Implement terminal connectivity validation.  
  **Refs:** FR-057, FR-061  
  **Unit tests:** disconnected terminal tests  
  **Commit:** `feat(exec): implement terminal connectivity validation`

- [ ] Implement risk-decision freshness and proposal-match validation.  
  **Refs:** FR-057, FR-029, FR-030  
  **Unit tests:** stale or mismatched risk decision tests  
  **Commit:** `feat(exec): validate risk approval freshness and proposal match`

- [ ] Implement readiness validation aggregate result.  
  **Refs:** FR-057, NFR-002  
  **Unit tests:** aggregated failure reason tests  
  **Commit:** `feat(exec): implement execution readiness aggregate validator`

### 7.5 MT5 MCP Boundary

- [ ] Create MT5 MCP server skeleton.  
  **Refs:** INV-002, FR-022, FR-056  
  **Unit tests:** MCP server startup tests  
  **Commit:** `feat(mt5-mcp): initialize mt5 mcp server`

- [ ] Implement read-only MT5 tools for account, positions, orders, symbol metadata, ticks.  
  **Refs:** FR-061, FR-069  
  **Unit tests:** tool contract tests with fixtures  
  **Commit:** `feat(mt5-mcp): add read-only broker tools`

- [ ] Implement side-effecting MT5 tools for place/modify/partial-close/full-close/cancel.  
  **Refs:** FR-058  
  **Unit tests:** tool request/response contract tests  
  **Commit:** `feat(mt5-mcp): add side-effecting broker tools`

- [ ] Implement tool-level stale-input rejection.  
  **Refs:** FR-070, NFR-002  
  **Unit tests:** stale request rejection tests  
  **Commit:** `feat(mt5-mcp): reject stale execution-critical inputs`

- [ ] Implement broker response normalization.  
  **Refs:** FR-059  
  **Unit tests:** retcode-to-normalized-receipt mapping tests  
  **Commit:** `feat(mt5-mcp): normalize broker responses`

- [ ] Implement MT5 tool authorization separation for read-only vs mutating tools.  
  **Refs:** INV-002, NFR-003, NFR-015  
  **Unit tests:** unauthorized mutating tool access tests  
  **Commit:** `feat(mt5-mcp): add role-based tool authorization`

### 7.6 Reconciliation Engine

- [ ] Implement in-flight execution intent loader on startup.  
  **Refs:** FR-077  
  **Unit tests:** startup loading tests  
  **Commit:** `feat(recon): load in-flight intents on startup`

- [ ] Implement broker truth fetch by client_order_id and account state.  
  **Refs:** FR-077  
  **Unit tests:** client-order-id lookup tests  
  **Commit:** `feat(recon): fetch broker truth for in-flight intents`

- [ ] Implement local-vs-broker comparison engine.  
  **Refs:** FR-076, FR-077  
  **Unit tests:** confirmed/absent/conflicting classification tests  
  **Commit:** `feat(recon): compare local and broker execution truth`

- [ ] Implement no-blind-retry guard when ack delay or uncertainty exists.  
  **Refs:** FR-060, FR-075  
  **Unit tests:** retry blocked pending reconciliation tests  
  **Commit:** `feat(recon): block blind retries before reconciliation`

- [ ] Implement reconciliation result persistence.  
  **Refs:** FR-077, FR-072  
  **Unit tests:** reconciliation run persistence tests  
  **Commit:** `feat(recon): persist reconciliation runs`

- [ ] Implement incident raising on unresolved divergence.  
  **Refs:** FR-076, FR-062  
  **Unit tests:** divergence creates incident tests  
  **Commit:** `feat(recon): raise incidents for unresolved broker conflicts`

### 7.7 Phase 2 Exit Criteria

- [ ] Risk engine returns fully persisted decisions with constraints and provenance.  
- [ ] Kill switch technically blocks new live entry.  
- [ ] Execution readiness validator blocks stale or invalid sends.  
- [ ] MT5 MCP boundary exists and separates read-only vs mutating access.  
- [ ] Reconciliation blocks unsafe duplicate retries.  
- [ ] Unit + integration tests for risk, kill-switch, readiness, MT5, reconciliation green.  

---

## 8. Phase 3 — Agent Runtime

### 8.1 ADK Runtime Foundation

- [ ] Create ADK runner wrapper service.  
  **Refs:** FR-018 to FR-024  
  **Unit tests:** runner initialization tests  
  **Commit:** `feat(agent-runtime): add adk runner wrapper`

- [ ] Create session manager abstraction.  
  **Refs:** FR-068  
  **Unit tests:** session state lifecycle tests  
  **Commit:** `feat(agent-runtime): add session manager abstraction`

- [ ] Create workflow-memory binding abstraction.  
  **Refs:** FR-068, FR-071  
  **Unit tests:** workflow memory isolation tests  
  **Commit:** `feat(agent-runtime): add workflow memory bindings`

- [ ] Create tool allowlist enforcement middleware.  
  **Refs:** FR-022, NFR-003, NFR-015  
  **Unit tests:** forbidden tool rejection tests  
  **Commit:** `feat(agent-runtime): enforce per-agent tool allowlists`

- [ ] Create context redaction middleware for secrets and privileged state.  
  **Refs:** INV-020, NFR-015, NFR-016  
  **Unit tests:** secret redaction tests  
  **Commit:** `feat(agent-runtime): add context redaction middleware`

- [ ] Create canonical-output validator for all agent results.  
  **Refs:** FR-021, INV-003  
  **Unit tests:** invalid output rejection tests  
  **Commit:** `feat(agent-runtime): validate agent outputs against canonical schemas`

### 8.2 Prompt and Version Registry

- [ ] Create prompt registry domain model.  
  **Refs:** FR-073, NFR-020  
  **Unit tests:** prompt record validation tests  
  **Commit:** `feat(prompt-registry): add prompt registry models`

- [ ] Implement prompt version resolution service.  
  **Refs:** FR-073  
  **Unit tests:** prompt version lookup tests  
  **Commit:** `feat(prompt-registry): implement prompt version resolution`

- [ ] Implement prompt hash persistence in trajectory/provenance.  
  **Refs:** FR-073, NFR-004  
  **Unit tests:** provenance includes prompt hash tests  
  **Commit:** `feat(prompt-registry): persist prompt hashes in provenance`

### 8.3 Core Agents

- [ ] Implement OrchestratorAgent instructions and wrapper.  
  **Refs:** FR-019, FR-024, FR-005  
  **Unit tests:** goal decomposition stub tests  
  **Commit:** `feat(agents): implement orchestrator agent`

- [ ] Implement StrategyAgent instructions and wrapper.  
  **Refs:** FR-019, FR-039 to FR-043  
  **Unit tests:** hypothesis output schema tests  
  **Commit:** `feat(agents): implement strategy agent`

- [ ] Implement ResearchAgent instructions and wrapper.  
  **Refs:** FR-019, FR-052 to FR-055  
  **Unit tests:** evidence/freshness output tests  
  **Commit:** `feat(agents): implement research agent`

- [ ] Implement MonitoringAgent instructions and wrapper.  
  **Refs:** FR-019, FR-061 to FR-063  
  **Unit tests:** alert classification output tests  
  **Commit:** `feat(agents): implement monitoring agent`

- [ ] Implement PortfolioAgent instructions and wrapper.  
  **Refs:** FR-019, FR-048 to FR-051  
  **Unit tests:** portfolio proposal output tests  
  **Commit:** `feat(agents): implement portfolio agent`

- [ ] Implement ComplianceAgent instructions and wrapper.  
  **Refs:** FR-019, FR-035 to FR-038, COMP-010 to COMP-013  
  **Unit tests:** compliance review output tests  
  **Commit:** `feat(agents): implement compliance agent`

- [ ] Implement ExecutionAgent instructions and wrapper.  
  **Refs:** FR-019, FR-056 to FR-060  
  **Unit tests:** intent translation output tests  
  **Commit:** `feat(agents): implement execution agent`

- [ ] Implement RiskGovernorAgent wrapper as controlled adapter over deterministic risk service.  
  **Refs:** FR-028 to FR-034, NFR-003  
  **Unit tests:** agent cannot bypass deterministic decision source tests  
  **Commit:** `feat(agents): implement risk governor adapter`

### 8.4 Optional Sub-Agents

- [ ] Implement VolatilityAgent.  
  **Refs:** FR-020, FR-031  
  **Unit tests:** volatility summary schema tests  
  **Commit:** `feat(agents): implement volatility sub-agent`

- [ ] Implement RegimeAgent.  
  **Refs:** FR-020, FR-031  
  **Unit tests:** regime output schema tests  
  **Commit:** `feat(agents): implement regime sub-agent`

- [ ] Implement SlippageAgent.  
  **Refs:** FR-020, FR-031, FR-057  
  **Unit tests:** slippage assessment schema tests  
  **Commit:** `feat(agents): implement slippage sub-agent`

- [ ] Implement CorrelationAgent.  
  **Refs:** FR-020, FR-031, FR-048  
  **Unit tests:** correlation output schema tests  
  **Commit:** `feat(agents): implement correlation sub-agent`

- [ ] Implement ExposureAgent.  
  **Refs:** FR-020, FR-031, FR-048  
  **Unit tests:** exposure output schema tests  
  **Commit:** `feat(agents): implement exposure sub-agent`

- [ ] Implement DrawdownAgent.  
  **Refs:** FR-020, FR-031  
  **Unit tests:** drawdown output schema tests  
  **Commit:** `feat(agents): implement drawdown sub-agent`

### 8.5 Workflow Patterns

- [ ] Implement sequential workflow runner.  
  **Refs:** FR-024, FR-005 to FR-007  
  **Unit tests:** ordered phase execution tests  
  **Commit:** `feat(agent-runtime): implement sequential workflow pattern`

- [ ] Implement routing workflow runner.  
  **Refs:** FR-024  
  **Unit tests:** route-selection tests  
  **Commit:** `feat(agent-runtime): implement routing workflow pattern`

- [ ] Implement parallel workflow runner.  
  **Refs:** FR-024  
  **Unit tests:** fan-out/fan-in tests  
  **Commit:** `feat(agent-runtime): implement parallel workflow pattern`

- [ ] Implement evaluator-optimizer workflow runner.  
  **Refs:** FR-024, FR-055  
  **Unit tests:** refine-loop termination tests  
  **Commit:** `feat(agent-runtime): implement evaluator optimizer pattern`

- [ ] Implement orchestrator-worker workflow runner.  
  **Refs:** FR-024  
  **Unit tests:** task graph decomposition tests  
  **Commit:** `feat(agent-runtime): implement orchestrator worker pattern`

- [ ] Implement refine-loop guard against infinite iteration.  
  **Refs:** FR-055, FR-076  
  **Unit tests:** max-iteration escalation tests  
  **Commit:** `feat(agent-runtime): add refine-loop guardrails`

### 8.6 Evaluator Infrastructure

- [ ] Implement evaluator rubric model.  
  **Refs:** FR-055, FR-072  
  **Unit tests:** rubric parsing tests  
  **Commit:** `feat(evaluator): add rubric models`

- [ ] Implement trajectory evaluation service.  
  **Refs:** NFR-004  
  **Unit tests:** trajectory scoring tests  
  **Commit:** `feat(evaluator): implement trajectory evaluation service`

- [ ] Implement unsupported-assertion checks for research outputs.  
  **Refs:** FR-053, FR-054, FR-069  
  **Unit tests:** unsupported claim detection tests  
  **Commit:** `feat(evaluator): add unsupported assertion checks`

- [ ] Implement refinement recommendation generator.  
  **Refs:** FR-055  
  **Unit tests:** improvement action generation tests  
  **Commit:** `feat(evaluator): generate refinement recommendations`

### 8.7 Observability and Trajectory Logs

- [ ] Implement trajectory log model and persistence.  
  **Refs:** FR-072, NFR-004  
  **Unit tests:** trajectory insert tests  
  **Commit:** `feat(obs): implement trajectory log persistence`

- [ ] Capture workflow/correlation IDs in every agent run.  
  **Refs:** FR-063, NFR-004  
  **Unit tests:** propagated ID tests  
  **Commit:** `feat(obs): propagate workflow and correlation ids across agent runs`

- [ ] Capture input/output schema names and hashes.  
  **Refs:** FR-073, NFR-004  
  **Unit tests:** schema hash capture tests  
  **Commit:** `feat(obs): log schema names and hashes`

- [ ] Capture tool calls, hashes, and latency.  
  **Refs:** FR-061, NFR-004  
  **Unit tests:** tool-call logging tests  
  **Commit:** `feat(obs): capture tool call hashes and latency`

- [ ] Capture model, prompt hash, token usage, and final verdict.  
  **Refs:** FR-073, NFR-004  
  **Unit tests:** model provenance log tests  
  **Commit:** `feat(obs): log model prompt and token provenance`

### 8.8 Phase 3 Exit Criteria

- [ ] ADK runtime operational with allowlists and redaction.  
- [ ] Core agents produce schema-valid outputs.  
- [ ] Workflow patterns supported.  
- [ ] Evaluator infrastructure operational.  
- [ ] Trajectory logging complete enough for replay provenance.  
- [ ] Unit + integration tests for runtime, agents, and evaluator green.  

---

## 9. Phase 4 — Live Control Plane

### 9.1 Proposal Pipeline

- [ ] Implement hypothesis-to-proposal transformer.  
  **Refs:** INV-006, FR-041  
  **Unit tests:** transform validity tests  
  **Commit:** `feat(proposals): implement hypothesis to proposal transformation`

- [ ] Implement proposal readiness checker.  
  **Refs:** FR-040, FR-041  
  **Unit tests:** missing validation-data rejection tests  
  **Commit:** `feat(proposals): implement proposal readiness checks`

- [ ] Implement proposal state transition service.  
  **Refs:** FR-010  
  **Unit tests:** state transition guard tests  
  **Commit:** `feat(proposals): implement proposal state transition service`

### 9.2 Execution Service

- [ ] Implement execution intent assembler from approved proposal + risk decision.  
  **Refs:** FR-056, FR-059  
  **Unit tests:** intent linkage tests  
  **Commit:** `feat(execution): implement execution intent assembler`

- [ ] Implement execution idempotency-key generator.  
  **Refs:** FR-059, DP-006  
  **Unit tests:** stable uniqueness tests  
  **Commit:** `feat(execution): implement idempotency key generation`

- [ ] Implement pre-send validation orchestration.  
  **Refs:** FR-057  
  **Unit tests:** readiness chain failure tests  
  **Commit:** `feat(execution): orchestrate pre-send validation chain`

- [ ] Implement execution send service through MT5 MCP.  
  **Refs:** FR-056 to FR-060  
  **Unit tests:** send path integration tests with broker simulator  
  **Commit:** `feat(execution): implement broker send service`

- [ ] Implement send-attempt persistence.  
  **Refs:** FR-059, FR-060  
  **Unit tests:** attempt increment tests  
  **Commit:** `feat(execution): persist execution send attempts`

- [ ] Implement receipt normalization and persistence.  
  **Refs:** FR-059  
  **Unit tests:** receipt mapping tests  
  **Commit:** `feat(execution): normalize and persist receipts`

- [ ] Implement authoritative/provisional/reconciling state propagation.  
  **Refs:** FR-067  
  **Unit tests:** state badge mapping tests  
  **Commit:** `feat(execution): propagate authoritative provisional and reconciling states`

- [ ] Implement pending-order, SL/TP modify, partial-close, full-close, cancel handlers.  
  **Refs:** FR-058  
  **Unit tests:** action-type handler tests  
  **Commit:** `feat(execution): support full broker action set`

### 9.3 Approval Flows

- [ ] Implement live execution approval API endpoints.  
  **Refs:** FR-035, FR-038  
  **Unit tests:** endpoint authorization tests  
  **Commit:** `feat(approval-api): add live execution approval endpoints`

- [ ] Implement policy-change approval flow.  
  **Refs:** FR-038, COMP-012  
  **Unit tests:** dual-auth policy change tests  
  **Commit:** `feat(approval-api): implement policy change approvals`

- [ ] Implement override approval flow with bounded expiry.  
  **Refs:** FR-037  
  **Unit tests:** expiry and rationale enforcement tests  
  **Commit:** `feat(approval-api): implement override approval flow`

- [ ] Implement hard-trigger kill-switch recovery approval flow.  
  **Refs:** FR-013, Board baseline  
  **Unit tests:** dual-auth recovery tests  
  **Commit:** `feat(approval-api): implement kill switch recovery approvals`

### 9.4 Monitoring and Incident Management

- [ ] Implement observation ingestion pipeline.  
  **Refs:** FR-061, FR-063  
  **Unit tests:** observation event ingestion tests  
  **Commit:** `feat(monitoring): implement observation ingestion pipeline`

- [ ] Implement alert classification service.  
  **Refs:** FR-062  
  **Unit tests:** warning/incident/critical/kill-switch classification tests  
  **Commit:** `feat(monitoring): implement alert classification`

- [ ] Implement incident creation and lifecycle service.  
  **Refs:** FR-011  
  **Unit tests:** incident FSM tests  
  **Commit:** `feat(monitoring): implement incident lifecycle service`

- [ ] Implement stale-state detector.  
  **Refs:** FR-061, TTL-021  
  **Unit tests:** stale-state incident tests  
  **Commit:** `feat(monitoring): implement stale-state detector`

- [ ] Implement tool-health monitor.  
  **Refs:** FR-061  
  **Unit tests:** downstream health degradation tests  
  **Commit:** `feat(monitoring): implement tool health monitoring`

- [ ] Implement workflow-timeout detector.  
  **Refs:** FR-015, FR-076  
  **Unit tests:** timeout transition tests  
  **Commit:** `feat(monitoring): implement workflow timeout detection`

### 9.5 Replay and Audit

- [ ] Implement replay bundle assembler.  
  **Refs:** FR-072, FR-073, FR-074  
  **Unit tests:** bundle completeness tests  
  **Commit:** `feat(replay): implement replay bundle assembler`

- [ ] Implement integrity manifest generator.  
  **Refs:** NFR-019, NFR-020  
  **Unit tests:** hash manifest tests  
  **Commit:** `feat(replay): implement integrity manifest generation`

- [ ] Implement audit export service by compliance profile.  
  **Refs:** COMP-013, FR-074  
  **Unit tests:** export profile labeling tests  
  **Commit:** `feat(audit): implement compliance-profile-aware audit export`

- [ ] Implement legal-hold aware retrieval.  
  **Refs:** FR-074, COMP-002  
  **Unit tests:** legal-hold protected export tests  
  **Commit:** `feat(audit): add legal-hold aware retrieval`

- [ ] Implement signed audit log or signed manifest emission.  
  **Refs:** NFR-019, COMP profile controls  
  **Unit tests:** signature verification tests  
  **Commit:** `feat(audit): add signed audit evidence generation`

### 9.6 Operator Dashboard

- [ ] Implement workflow list/read views.  
  **Refs:** FR-064, FR-065  
  **Unit tests:** UI query rendering tests  
  **Commit:** `feat(ui): add workflow list and detail views`

- [ ] Implement proposal queue and risk-decision views.  
  **Refs:** FR-064, FR-065  
  **Unit tests:** component data mapping tests  
  **Commit:** `feat(ui): add proposal and risk decision views`

- [ ] Implement approval queue views.  
  **Refs:** FR-064, FR-066  
  **Unit tests:** pending approval rendering tests  
  **Commit:** `feat(ui): add approval queue screens`

- [ ] Implement incident console.  
  **Refs:** FR-064, FR-066  
  **Unit tests:** incident table and detail tests  
  **Commit:** `feat(ui): add incident console`

- [ ] Implement replay bundle view.  
  **Refs:** FR-065, FR-072  
  **Unit tests:** replay detail rendering tests  
  **Commit:** `feat(ui): add replay bundle view`

- [ ] Implement live event streaming to dashboard.  
  **Refs:** FR-064, NFR-005  
  **Unit tests:** websocket/sse subscription tests  
  **Commit:** `feat(ui): add real-time event streaming`

- [ ] Implement authoritative/provisional/reconciling visual badges.  
  **Refs:** FR-067  
  **Unit tests:** state badge tests  
  **Commit:** `feat(ui): add authority-state visual indicators`

### 9.7 Phase 4 Exit Criteria

- [ ] End-to-end supervised live execution path works in non-production with simulator/paper target.  
- [ ] Approval, override, incident, replay, and export paths exist.  
- [ ] Dashboard exposes operational supervision views.  
- [ ] All live actions create intent, receipt, provenance, and replay artifacts.  
- [ ] Integration + scenario tests for live control plane green.  

---

## 10. Phase 5 — Portfolio and Promotion

### 10.1 Portfolio Analytics Service

- [ ] Implement portfolio snapshot assembler.  
  **Refs:** FR-048  
  **Unit tests:** snapshot completeness tests  
  **Commit:** `feat(portfolio): implement portfolio snapshot assembler`

- [ ] Implement marginal risk contribution calculator.  
  **Refs:** FR-048, FR-051  
  **Unit tests:** marginal contribution tests  
  **Commit:** `feat(portfolio): implement marginal risk contribution`

- [ ] Implement resize proposal generator.  
  **Refs:** FR-049  
  **Unit tests:** resize proposal tests  
  **Commit:** `feat(portfolio): implement resize proposal generation`

- [ ] Implement rebalance proposal generator.  
  **Refs:** FR-049  
  **Unit tests:** rebalance proposal tests  
  **Commit:** `feat(portfolio): implement rebalance proposal generation`

- [ ] Implement hedge proposal generator.  
  **Refs:** FR-049  
  **Unit tests:** hedge proposal tests  
  **Commit:** `feat(portfolio): implement hedge proposal generation`

- [ ] Implement de-risk proposal generator.  
  **Refs:** FR-049  
  **Unit tests:** de-risk proposal tests  
  **Commit:** `feat(portfolio): implement de-risk proposal generation`

- [ ] Implement projected VaR / ES impact calculator.  
  **Refs:** FR-051  
  **Unit tests:** projected risk impact tests  
  **Commit:** `feat(portfolio): implement projected var and es impact`

- [ ] Implement projected margin utilization calculator.  
  **Refs:** FR-051  
  **Unit tests:** projected margin tests  
  **Commit:** `feat(portfolio): implement projected margin impact`

- [ ] Implement advisory-only enforcement on portfolio actions.  
  **Refs:** FR-050  
  **Unit tests:** direct-live-execution rejection tests  
  **Commit:** `feat(portfolio): enforce advisory-only portfolio action mode`

### 10.2 Strategy Registry and Lifecycle

- [ ] Implement strategy registry service.  
  **Refs:** FR-044  
  **Unit tests:** lifecycle state persistence tests  
  **Commit:** `feat(strategy-gov): implement strategy registry service`

- [ ] Implement lifecycle transition validator.  
  **Refs:** FR-044, FR-045  
  **Unit tests:** invalid lifecycle jump rejection tests  
  **Commit:** `feat(strategy-gov): implement lifecycle transition validator`

- [ ] Implement promotion evidence bundle validator.  
  **Refs:** FR-045, PROM-010 to PROM-014  
  **Unit tests:** missing-evidence rejection tests  
  **Commit:** `feat(strategy-gov): implement promotion evidence validation`

- [ ] Implement promotion approval routing.  
  **Refs:** FR-045, FR-046  
  **Unit tests:** required-approver routing tests  
  **Commit:** `feat(strategy-gov): implement promotion approval routing`

- [ ] Implement promotion persistence service.  
  **Refs:** FR-046  
  **Unit tests:** promotion record persistence tests  
  **Commit:** `feat(strategy-gov): implement promotion persistence`

- [ ] Implement live-envelope update on promotion.  
  **Refs:** FR-047, PROM-012 to PROM-014  
  **Unit tests:** operating envelope update tests  
  **Commit:** `feat(strategy-gov): update operating envelope on promotion`

- [ ] Implement suspension triggers.  
  **Refs:** PROM-020, PROM-021  
  **Unit tests:** suspension trigger tests  
  **Commit:** `feat(strategy-gov): implement automatic suspension triggers`

- [ ] Implement retirement flow.  
  **Refs:** FR-044, PROM-022  
  **Unit tests:** retirement preservation tests  
  **Commit:** `feat(strategy-gov): implement strategy retirement flow`

### 10.3 Evidence Bundle Automation

- [ ] Implement evidence bundle content manifest format.  
  **Refs:** FR-053, FR-072, PROM-002  
  **Unit tests:** manifest completeness tests  
  **Commit:** `feat(evidence): implement evidence bundle manifest format`

- [ ] Implement evidence bundle assembler for backtest/robustness/paper/live-limited artifacts.  
  **Refs:** PROM-010 to PROM-014  
  **Unit tests:** lifecycle evidence assembly tests  
  **Commit:** `feat(evidence): assemble lifecycle evidence bundles`

- [ ] Implement evidence bundle hashing and storage.  
  **Refs:** FR-073, NFR-020  
  **Unit tests:** hash integrity tests  
  **Commit:** `feat(evidence): hash and store evidence bundles`

- [ ] Implement evidence bundle review UI.  
  **Refs:** FR-065, FR-066  
  **Unit tests:** bundle review rendering tests  
  **Commit:** `feat(ui): add evidence bundle review screens`

### 10.4 Phase 5 Exit Criteria

- [ ] Portfolio analytics produces advisory proposals with quantified impact.  
- [ ] Strategy lifecycle registry enforces promotion gates.  
- [ ] Evidence bundles are automated and reviewable.  
- [ ] Suspension and retirement logic work.  
- [ ] Unit + integration + promotion-gate tests green.  

---

## 11. Phase 6 — Migration and Hardening

### 11.1 Legacy Wrapping

- [ ] Wrap existing simulation module as `backtest_mcp`.  
  **Refs:** FR-052, Migration design  
  **Unit tests:** MCP wrapper contract tests  
  **Commit:** `feat(migration): wrap simulation module as backtest mcp`

- [ ] Wrap existing optimization module as `optimization_mcp`.  
  **Refs:** FR-052, FR-048  
  **Unit tests:** MCP wrapper contract tests  
  **Commit:** `feat(migration): wrap optimization module as optimization mcp`

- [ ] Wrap existing risk module as `risk_analytics_mcp`.  
  **Refs:** FR-031, FR-048  
  **Unit tests:** MCP wrapper contract tests  
  **Commit:** `feat(migration): wrap risk module as risk analytics mcp`

- [ ] Wrap existing database access as governed `sql_mcp`.  
  **Refs:** INV-002, FR-022  
  **Unit tests:** governed query contract tests  
  **Commit:** `feat(migration): wrap database module as sql mcp`

- [ ] Wrap existing MT5 integration as governed `mt5_mcp` where not yet replaced.  
  **Refs:** INV-002, FR-056  
  **Unit tests:** wrapper compatibility tests  
  **Commit:** `feat(migration): wrap legacy mt5 integration as governed mcp`

### 11.2 Shadow Mode

- [ ] Implement shadow-mode workflow execution flag.  
  **Refs:** MODE-002/003 rollout intent, FR-017  
  **Unit tests:** shadow mode blocks broker side effects tests  
  **Commit:** `feat(shadow): implement shadow mode execution flag`

- [ ] Implement production-like data feed into shadow mode.  
  **Refs:** FR-014, FR-017  
  **Unit tests:** shadow data pipeline tests  
  **Commit:** `feat(shadow): feed production-like data into shadow workflows`

- [ ] Implement expected-vs-realized comparison reporting in shadow mode.  
  **Refs:** PROM-013, PROM-014  
  **Unit tests:** shadow comparison metric tests  
  **Commit:** `feat(shadow): compare shadow expectations against realized outcomes`

### 11.3 Replay Validation

- [ ] Implement replay runner from stored bundles.  
  **Refs:** FR-072 to FR-074  
  **Unit tests:** deterministic replay tests  
  **Commit:** `feat(replay): implement stored bundle replay runner`

- [ ] Implement replay completeness checker.  
  **Refs:** FR-073, NFR-020  
  **Unit tests:** missing-artifact detection tests  
  **Commit:** `feat(replay): implement replay completeness checker`

- [ ] Implement replay-vs-original comparison report.  
  **Refs:** FR-073  
  **Unit tests:** replay comparison diff tests  
  **Commit:** `feat(replay): implement replay versus original comparison`

### 11.4 Chaos and Failure Readiness

- [ ] Implement chaos test for stale market data.  
  **Refs:** FR-076, NFR-002  
  **Unit tests:** n/a, scenario/chaos test  
  **Commit:** `test(chaos): add stale market data chaos scenario`

- [ ] Implement chaos test for stale risk decision.  
  **Refs:** FR-076, FR-029  
  **Unit tests:** n/a, scenario/chaos test  
  **Commit:** `test(chaos): add stale risk decision chaos scenario`

- [ ] Implement chaos test for broker ack delay.  
  **Refs:** FR-076, FR-060  
  **Unit tests:** n/a, scenario/chaos test  
  **Commit:** `test(chaos): add broker ack delay chaos scenario`

- [ ] Implement chaos test for duplicate receipt.  
  **Refs:** FR-076  
  **Unit tests:** n/a, scenario/chaos test  
  **Commit:** `test(chaos): add duplicate receipt chaos scenario`

- [ ] Implement chaos test for process restart during execution.  
  **Refs:** FR-076, FR-077  
  **Unit tests:** n/a, scenario/chaos test  
  **Commit:** `test(chaos): add restart-during-execution scenario`

- [ ] Implement chaos test for policy service outage.  
  **Refs:** FR-076, NFR-002  
  **Unit tests:** n/a, scenario/chaos test  
  **Commit:** `test(chaos): add policy service outage scenario`

### 11.5 Security and Red-Team Hardening

- [ ] Implement RBAC policy tests across all operator endpoints.  
  **Refs:** FR-035, NFR-015  
  **Unit tests:** security tests  
  **Commit:** `test(security): add rbac coverage for operator endpoints`

- [ ] Implement service-to-service auth for MCP calls.  
  **Refs:** INV-002, NFR-015  
  **Unit tests:** unauthorized MCP call rejection tests  
  **Commit:** `feat(security): add service auth for mcp calls`

- [ ] Implement secrets isolation and rotation strategy.  
  **Refs:** NFR-016  
  **Unit tests:** config load redaction tests  
  **Commit:** `feat(security): add secrets isolation and rotation support`

- [ ] Implement prompt-injection defense tests for research retrieval.  
  **Refs:** FR-052 to FR-055, NFR-017  
  **Unit tests:** red-team tests  
  **Commit:** `test(security): add prompt injection red-team scenarios`

- [ ] Implement retrieval contamination defense tests.  
  **Refs:** FR-053, FR-069, NFR-017  
  **Unit tests:** red-team tests  
  **Commit:** `test(security): add retrieval contamination scenarios`

- [ ] Implement audit integrity verification tests.  
  **Refs:** NFR-019, NFR-020  
  **Unit tests:** signature/hash validation tests  
  **Commit:** `test(security): add audit integrity verification tests`

### 11.6 Performance and Capacity

- [ ] Implement Redis cache for hot snapshots with freshness metadata.  
  **Refs:** FR-070, NFR-006 to NFR-011  
  **Unit tests:** cache freshness tests  
  **Commit:** `feat(perf): add hot snapshot caching with freshness metadata`

- [ ] Implement async I/O for MCP integration calls.  
  **Refs:** NFR-006 to NFR-011  
  **Unit tests:** async timeout tests  
  **Commit:** `feat(perf): convert mcp integrations to async io`

- [ ] Partition high-volume tables (`workflow_transitions`, `observations`, `trajectory_logs`).  
  **Refs:** NFR-006, NFR-020  
  **Unit tests:** partition-routing tests  
  **Commit:** `feat(db): partition high-volume event tables`

- [ ] Add selective denormalized read models for dashboard hot paths.  
  **Refs:** FR-064, NFR-007  
  **Unit tests:** query performance smoke tests  
  **Commit:** `feat(read-models): add denormalized operator dashboard read models`

- [ ] Add latency budget monitors and alerts.  
  **Refs:** NFR-004, NFR-006 to NFR-011  
  **Unit tests:** alert threshold tests  
  **Commit:** `feat(obs): add latency budget monitors and alerts`

### 11.7 Compliance Rollout

- [ ] Seed Internal / Non-Regulated compliance profile.  
  **Refs:** COMP-001, COMP-002  
  **Unit tests:** profile seed tests  
  **Commit:** `feat(compliance): seed internal non-regulated profile`

- [ ] Seed UAE Enterprise compliance profile as initial production baseline.  
  **Refs:** COMP-001 to COMP-013, Board baseline  
  **Unit tests:** profile seed tests  
  **Commit:** `feat(compliance): seed uae enterprise profile`

- [ ] Implement profile attachment to every live execution workflow.  
  **Refs:** COMP-010  
  **Unit tests:** missing-profile live workflow rejection tests  
  **Commit:** `feat(compliance): attach active profile to live workflows`

- [ ] Implement export labeling by compliance profile.  
  **Refs:** COMP-013  
  **Unit tests:** export metadata tests  
  **Commit:** `feat(compliance): label exports by active compliance profile`

- [ ] Implement legal-hold-aware purge blocker.  
  **Refs:** FR-074, COMP-003  
  **Unit tests:** purge blocked by legal hold tests  
  **Commit:** `feat(compliance): block purge under legal hold`

### 11.8 Phase 6 Exit Criteria

- [ ] Legacy modules wrapped or replaced behind MCP boundaries.  
- [ ] Shadow mode working with comparison reporting.  
- [ ] Replay validation complete.  
- [ ] Chaos, security, red-team, and perf hardening complete.  
- [ ] Compliance rollout complete for dev and initial production baseline.  

---

## 12. End-to-End Scenario Backlog

### 12.1 Core Scenarios

- [ ] Research-only workflow runs without executable intent creation.  
  **Refs:** MODE-000, FR-052 to FR-055  
  **Tests:** scenario  
  **Commit:** `test(scenario): add research-only workflow scenario`

- [ ] Advisory workflow generates hypothesis and proposal but no live order.  
  **Refs:** MODE-001, FR-039 to FR-043  
  **Tests:** scenario  
  **Commit:** `test(scenario): add advisory proposal workflow scenario`

- [ ] Paper execution workflow completes full loop and stores receipts.  
  **Refs:** MODE-002, FR-017, FR-056 to FR-060  
  **Tests:** scenario  
  **Commit:** `test(scenario): add paper execution workflow scenario`

- [ ] Human-approved live workflow requires risk approval and operator approval.  
  **Refs:** MODE-003, FR-028, FR-035, FR-038  
  **Tests:** scenario  
  **Commit:** `test(scenario): add human-approved live workflow scenario`

- [ ] Bounded autonomous live workflow only executes inside approved envelope.  
  **Refs:** MODE-004, FR-047  
  **Tests:** scenario  
  **Commit:** `test(scenario): add bounded autonomous live workflow scenario`

### 12.2 Negative Scenarios

- [ ] Live entry blocked when risk decision stale.  
  **Refs:** FR-029, FR-030, FR-075  
  **Tests:** scenario  
  **Commit:** `test(scenario): block live entry on stale risk decision`

- [ ] Live entry blocked when workflow attempts unsupported autonomy escalation.  
  **Refs:** FR-003, FR-004  
  **Tests:** scenario  
  **Commit:** `test(scenario): block autonomy self-escalation`

- [ ] Live entry blocked when kill switch triggered.  
  **Refs:** FR-012, NFR-001  
  **Tests:** scenario  
  **Commit:** `test(scenario): block entry under kill switch`

- [ ] Duplicate retry blocked until reconciliation completes.  
  **Refs:** FR-060, FR-077  
  **Tests:** scenario  
  **Commit:** `test(scenario): block duplicate retry until reconciliation`

- [ ] Research agent attempt to issue execution instruction is rejected.  
  **Refs:** FR-054, INV-011  
  **Tests:** scenario  
  **Commit:** `test(scenario): reject research agent execution attempt`

- [ ] Agent attempt to call forbidden external tool is rejected.  
  **Refs:** FR-022, INV-002  
  **Tests:** scenario  
  **Commit:** `test(scenario): reject forbidden external tool access`

---

## 13. Release Slicing Recommendation

### Slice A — Internal Control Plane Prototype
Target:
- contracts
- registry
- workflow FSM
- db schema
- policy/approval skeleton
- UI shell

### Slice B — Paper Safety Loop
Target:
- risk engine
- readiness validator
- MT5 read path
- execution intent/receipt persistence
- reconciliation
- scenario tests in paper/sim mode

### Slice C — Agentic Research and Proposal Loop
Target:
- core agents
- evaluator
- research outputs
- proposal transformation
- trajectory logs

### Slice D — Supervised Live Control Plane
Target:
- execution service
- approval flows
- incidents
- replay/audit export
- dashboard supervision

### Slice E — Portfolio and Promotion
Target:
- portfolio analytics
- strategy lifecycle
- evidence bundle automation

### Slice F — Hardening for Controlled Production
Target:
- shadow mode
- replay validation
- chaos/security/performance/compliance rollout

---

## 14. Minimum Test Matrix by Layer

| Layer | Unit | Integration | Scenario | Chaos | Security | Replay |
|---|---|---|---|---|---|---|
| contracts | required | optional | optional | no | no | yes |
| workflow FSM | required | required | required | optional | no | yes |
| policy/approval | required | required | required | optional | required | yes |
| risk engine | required | required | required | required | no | yes |
| execution service | required | required | required | required | required | yes |
| MT5 MCP | required | required | required | required | required | no |
| agents/runtime | required | required | required | optional | required | yes |
| replay/audit | required | required | required | optional | required | yes |
| dashboard/api | required | required | required | no | required | no |

---

## 15. Non-Functional Work Packages

### 15.1 Safety
- [ ] Verify every live path has hard technical gate before broker mutation.  
  **Refs:** NFR-001, NFR-002, NFR-003  
  **Commit:** `test(readiness): verify hard technical live gates`

### 15.2 Observability
- [ ] Verify all production workflows emit trajectory logs and runtime assertions.  
  **Refs:** NFR-004, NFR-005  
  **Commit:** `test(obs): verify production workflow telemetry completeness`

### 15.3 Performance
- [ ] Verify risk eval p95 <= 300ms in controlled benchmark.  
  **Refs:** performance budgets  
  **Commit:** `test(perf): benchmark risk evaluation latency`

- [ ] Verify execution readiness validation p95 <= 400ms excluding external latency.  
  **Refs:** performance budgets  
  **Commit:** `test(perf): benchmark readiness validation latency`

- [ ] Verify dashboard propagation p95 <= 500ms.  
  **Refs:** performance budgets  
  **Commit:** `test(perf): benchmark dashboard propagation latency`

### 15.4 Security
- [ ] Verify secrets never enter model context or front-end payloads.  
  **Refs:** NFR-015, NFR-016  
  **Commit:** `test(security): verify secret isolation from model and ui payloads`

### 15.5 Auditability
- [ ] Verify every execution-bound decision reconstructs with replay bundle completeness.  
  **Refs:** NFR-019, NFR-020  
  **Commit:** `test(replay): verify execution-bound decision replay completeness`

---

## 16. Final Production Readiness Checklist

- [ ] All FR, NFR, INV, COMP, PROM, and TTL-linked tasks mapped and implemented.
- [ ] All canonical schemas registered, tested, and versioned.
- [ ] All live side effects mediated by execution service + MT5 MCP only.
- [ ] Risk decision required and enforced for every live mutation.
- [ ] Reconciliation blocks blind retries.
- [ ] Kill switch blocks new entries and enforces governed recovery.
- [ ] Replay bundle completeness verified for execution-bound workflows.
- [ ] Compliance profile attached to every live workflow.
- [ ] UAE Enterprise Profile seeded and validated for initial production baseline.
- [ ] Scenario, chaos, security, replay, and performance test suites passing.
- [ ] Shadow mode comparisons reviewed and accepted.
- [ ] Strategy promotion gates operational before autonomous-live rollout.
- [ ] Board-approved baselines encoded as policy, not tribal knowledge.

---

## 17. Suggested First 10 Tasks to Start Immediately

1. [ ] Initialize monorepo structure  
2. [ ] Add formatter/linter/typecheck/CI  
3. [ ] Scaffold canonical contracts package  
4. [ ] Implement canonical envelope  
5. [ ] Initialize migration framework  
6. [ ] Create core workflow tables  
7. [ ] Implement workflow state enums and validator  
8. [ ] Implement policy resolution service  
9. [ ] Implement schema registry  
10. [ ] Create FastAPI and dashboard shells

---

## 18. Notes for Execution

- Build safety-critical deterministic services before expanding agent autonomy.
- Keep every execution-critical field tool-grounded and schema-validated.
- Do not let agent wrappers become hidden enforcement points; enforcement stays in services.
- Prefer additive migrations and reversible changes.
- Keep scenario tests close to requirement references.
- Delay autonomous-live rollout until shadow mode, replay validation, and promotion gates are proven.
