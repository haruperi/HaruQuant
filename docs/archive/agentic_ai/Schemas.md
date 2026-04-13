# Database & Canonical Schemas Specification: HaruQuant Agentic AI System

**Document Version:** 1.0.0
**Companion To:** SRS v3.1.1 and Design Specification / System Architecture v1.1.0
**System:** HaruQuant Autonomous Trading Platform
**Classification:** Internal Use - Proprietary
**Status:** Implementation Specification

---

## 1. Purpose

This specification defines both the relational database design and the canonical message contracts for HaruQuant. It translates the approved requirements for operational state, auditability, inter-agent communication, and execution-bound decisions into implementation-ready schemas.

## 2. Scope
This document covers:

- canonical shared envelope
- identifier conventions
- schema registry rules
- versioning and compatibility
- message families
- payload definitions
- validation rules
- error contracts
- hash/signature requirements
- freshness and provenance fields
- example JSON and Pydantic models

This document does not define:
- SQL DDL
- REST endpoint paths
- MCP tool manifests in full
- infrastructure deployment settings

## 3. Design Principles

### 3.1 Database Principles
**DB-001 Relational source of operational truth**  
PostgreSQL is the system of record for operational workflow, governance, execution, and policy state.

**DB-002 Immutable artifacts outside OLTP tables where appropriate**  
Heavy snapshots, replay payloads, and raw receipts may be stored in object storage with DB metadata and hashes.

**DB-003 Versioned mutable state**  
Operational tables use explicit versioning or optimistic concurrency where needed.

**DB-004 Idempotent execution protection**  
Execution paths use unique constraints and reconciliation-safe identifiers.

**DB-005 Audit-friendly design**  
Critical state changes are linked to actors, timestamps, workflow context, and integrity references.

**DB-006 Separation of mutable state and replay state**  
Replay bundles and signed audit payloads are immutable and distinct from mutable operational records.

### 3.2 Schema Principles
**CS-001 Typed everywhere**  
All inter-agent, service, and execution-critical messages must validate against explicit schemas.

**CS-002 Shared envelope first**  
Every canonical contract uses a common metadata envelope.

**CS-003 Versioned contracts**  
Breaking changes require a schema version increment and compatibility handling.

**CS-004 Replayable payloads**  
Execution-critical payloads must contain or reference enough metadata for audit reconstruction.

**CS-005 Fail closed on malformed execution-critical data**  
If validation fails for execution-critical contracts, the receiving component rejects the message and emits a validation incident.

**CS-006 Separation of payload and transport**  
Canonical contract fields are transport-independent and may be used over REST, internal queues, Redis streams, replay bundles, or audit exports.

## 4. Database Platform and Standards
### 6.1 Primary Platform

Recommended primary relational engine:
- PostgreSQL 16+

### 6.2 SQL Standards

- snake_case naming
- singular primary key names using `_id`
- UTC timestamps in `timestamptz`
- JSONB for controlled semi-structured metadata
- explicit foreign keys unless there is a deliberate scale-driven exception
- no business logic hidden in triggers unless documented and tested

### 6.3 Schema Namespaces

Recommended namespaces:

- `core` for workflow and execution state
- `risk` for risk decisions and metrics metadata
- `gov` for approvals, policies, compliance, roles
- `audit` for audit chains and replay metadata
- `research` for research references and evidence metadata
- `ref` for reference data and enumerated lookup tables

If a single-schema deployment is preferred initially, retain these as logical module groupings in migrations.

---

## 7. High-Level Data Domains

| Domain | Purpose |
|---|---|
| workflow state | workflow lifecycle, steps, transitions |
| proposal pipeline | hypotheses, proposals, gating state |
| risk | requests, decisions, constraints, metric refs |
| execution | intents, send attempts, receipts, reconciliation |
| portfolio state | positions, pending orders, snapshots refs |
| incidents | alerts, incidents, kill-switch events |
| governance | approvals, votes, overrides, policies, compliance profiles |
| strategy lifecycle | registry, promotions, suspensions, retirements |
| audit and replay | trajectory logs metadata, replay bundles, integrity manifests |
| research | evidence bundles, retrieval result refs |
| identity and authorization | operator/service identity refs and scope mapping |

---

## 7. Core Table Specifications

## 7.1 core.workflows

Purpose:
- one row per workflow instance

Columns:
- workflow_id `text` PK
- workflow_type `text` not null
- environment `text` not null
- operating_mode `text` not null
- state `text` not null
- objective `text` not null
- scope_json `jsonb` not null default '{}'
- initiator_type `text` not null
- initiator_id `text` not null
- timeout_policy_json `jsonb` not null default '{}'
- stop_conditions_json `jsonb` not null default '[]'
- current_step_id `text` null
- version_no `integer` not null default 1
- created_at `timestamptz` not null default now()
- updated_at `timestamptz` not null default now()
- completed_at `timestamptz` null
- terminal_reason `text` null

Constraints:
- check operating_mode in allowed values
- check state in workflow FSM states
- unique `(workflow_id)`

Indexes:
- `(state, updated_at desc)`
- `(workflow_type, created_at desc)`
- `(environment, operating_mode, created_at desc)`

## 7.2 core.workflow_transitions

Purpose:
- immutable history of workflow state transitions

Columns:
- transition_id `bigserial` PK
- workflow_id `text` not null FK -> core.workflows.workflow_id
- from_state `text` not null
- to_state `text` not null
- phase_name `text` null
- transition_reason `text` null
- actor_type `text` not null
- actor_id `text` not null
- correlation_id `text` not null
- causation_id `text` null
- occurred_at `timestamptz` not null default now()
- metadata_json `jsonb` not null default '{}'

Indexes:
- `(workflow_id, occurred_at)`
- `(correlation_id)`
- `(to_state, occurred_at desc)`

Partitioning:
- candidate for monthly range partitioning by `occurred_at` in high-volume environments

## 7.3 core.workflow_steps

Purpose:
- normalized per-step execution records

Columns:
- step_id `text` PK
- workflow_id `text` not null FK
- step_order `integer` not null
- step_type `text` not null
- assigned_agent `text` null
- input_contract_type `text` null
- input_ref `text` null
- output_contract_type `text` null
- output_ref `text` null
- status `text` not null
- started_at `timestamptz` null
- completed_at `timestamptz` null
- latency_ms `integer` null
- iteration_no `integer` not null default 0
- metadata_json `jsonb` not null default '{}'

Indexes:
- `(workflow_id, step_order)`
- `(assigned_agent, started_at desc)`

## 7.4 core.trade_hypotheses

Purpose:
- strategy outputs before proposal transformation

Columns:
- hypothesis_id `text` PK
- workflow_id `text` not null FK
- strategy_id `text` null
- symbol `text` not null
- direction `text` not null
- thesis_text `text` not null
- entry_rationale `text` not null
- invalidation_rationale `text` not null
- stop_loss_logic_json `jsonb` not null
- take_profit_logic_json `jsonb` null
- holding_horizon `text` not null
- confidence_score `numeric(5,4)` not null
- calibration_note `text` null
- strategy_family `text` not null
- feature_version `text` not null
- strategy_code_hash `text` not null
- evidence_bundle_id `text` null
- created_at `timestamptz` not null default now()

Indexes:
- `(workflow_id, created_at desc)`
- `(symbol, created_at desc)`
- `(strategy_id, created_at desc)`

## 7.5 core.trade_proposals

Purpose:
- validated execution candidates produced from hypotheses

Columns:
- proposal_id `text` PK
- workflow_id `text` not null FK
- hypothesis_id `text` not null FK -> core.trade_hypotheses.hypothesis_id
- state `text` not null
- symbol `text` not null
- direction `text` not null
- candidate_price_logic_json `jsonb` not null
- proposed_size_json `jsonb` not null
- operating_envelope_json `jsonb` not null default '{}'
- session_restrictions_json `jsonb` not null default '{}'
- expiry_at `timestamptz` null
- transformation_version `text` not null
- readiness_state `text` not null
- created_at `timestamptz` not null default now()
- updated_at `timestamptz` not null default now()

Indexes:
- `(state, updated_at desc)`
- `(symbol, state, created_at desc)`
- `(workflow_id, created_at desc)`

## 7.6 risk.risk_assessment_requests

Purpose:
- persisted request context for risk evaluations

Columns:
- risk_request_id `text` PK
- workflow_id `text` not null FK
- proposal_id `text` not null FK -> core.trade_proposals.proposal_id
- action_type `text` not null
- account_snapshot_ref `text` null
- portfolio_snapshot_ref `text` null
- market_snapshot_ref `text` null
- requested_freshness_json `jsonb` not null default '{}'
- strategy_lifecycle_state `text` not null
- active_policy_bundle_json `jsonb` not null
- compliance_profile_id `text` null
- current_kill_switch_state `text` not null
- created_at `timestamptz` not null default now()

Indexes:
- `(proposal_id, created_at desc)`
- `(workflow_id, created_at desc)`

## 7.7 risk.risk_decisions

Purpose:
- mandatory gating decisions for execution-bound actions

Columns:
- risk_decision_id `text` PK
- risk_request_id `text` not null FK -> risk.risk_assessment_requests.risk_request_id
- proposal_id `text` not null FK -> core.trade_proposals.proposal_id
- workflow_id `text` not null FK -> core.workflows.workflow_id
- decision `text` not null
- rationale_text `text` not null
- risk_metrics_snapshot_json `jsonb` not null
- freshness_expiry `timestamptz` not null
- policy_version_id `text` not null
- formula_version `text` not null
- provenance_bundle_id `text` null
- approval_token `text` null
- freshness_status `text` not null default 'fresh'
- created_at `timestamptz` not null default now()

Constraints:
- unique `(approval_token)` where approval_token is not null
- check decision in `APPROVE, APPROVE_WITH_LIMITS, REJECT, FORCE_EXIT`

Indexes:
- `(proposal_id, created_at desc)`
- `(decision, created_at desc)`
- `(freshness_expiry)`
- `(approval_token)`

## 7.8 risk.risk_constraints

Purpose:
- machine-enforceable limits associated with a risk decision

Columns:
- constraint_id `bigserial` PK
- risk_decision_id `text` not null FK -> risk.risk_decisions.risk_decision_id
- constraint_type `text` not null
- constraint_value_json `jsonb` not null
- created_at `timestamptz` not null default now()

Indexes:
- `(risk_decision_id)`
- `(constraint_type)`

## 7.9 core.execution_intents

Purpose:
- approved broker action requests

Columns:
- execution_intent_id `text` PK
- workflow_id `text` not null FK
- proposal_id `text` not null FK
- risk_decision_id `text` not null FK -> risk.risk_decisions.risk_decision_id
- action_type `text` not null
- symbol `text` not null
- side `text` not null
- order_type `text` not null
- size_json `jsonb` not null
- price_params_json `jsonb` not null default '{}'
- sl_tp_params_json `jsonb` not null default '{}'
- idempotency_key `text` not null
- client_order_id `text` null
- status `text` not null
- expiry_at `timestamptz` null
- pre_send_validation_snapshot_ref `text` null
- created_at `timestamptz` not null default now()
- updated_at `timestamptz` not null default now()

Constraints:
- unique `(idempotency_key)`

Indexes:
- `(status, created_at desc)`
- `(proposal_id)`
- `(risk_decision_id)`
- `(symbol, created_at desc)`
- `(client_order_id)`

## 7.10 core.execution_send_attempts

Purpose:
- track each broker submission attempt

Columns:
- send_attempt_id `bigserial` PK
- execution_intent_id `text` not null FK -> core.execution_intents.execution_intent_id
- attempt_no `integer` not null
- submitted_payload_hash `text` not null
- transport_status `text` not null
- broker_request_ref `text` null
- error_code `text` null
- error_message `text` null
- started_at `timestamptz` not null default now()
- finished_at `timestamptz` null
- latency_ms `integer` null

Constraints:
- unique `(execution_intent_id, attempt_no)`

Indexes:
- `(execution_intent_id, attempt_no)`
- `(transport_status, started_at desc)`

## 7.11 core.execution_receipts

Purpose:
- normalized broker receipts and authoritative/external responses

Columns:
- receipt_id `text` PK
- execution_intent_id `text` not null FK
- broker `text` not null default 'mt5'
- broker_order_id `text` null
- broker_deal_id `text` null
- receipt_status `text` not null
- requested_price `numeric(18,8)` null
- fill_price `numeric(18,8)` null
- fill_qty `numeric(18,4)` null
- spread_points `numeric(18,8)` null
- slippage_points `numeric(18,8)` null
- slippage_bps `numeric(18,8)` null
- raw_receipt_ref `text` null
- broker_message `text` null
- broker_retcode `integer` null
- authoritative_state `text` not null default 'PROVISIONAL'
- received_at `timestamptz` not null default now()

Indexes:
- `(execution_intent_id, received_at desc)`
- `(broker_order_id)`
- `(broker_deal_id)`
- `(receipt_status, received_at desc)`

## 7.12 core.reconciliation_runs

Purpose:
- track reconciliation outcomes for uncertain or restarted execution flows

Columns:
- reconciliation_run_id `bigserial` PK
- execution_intent_id `text` not null FK -> core.execution_intents.execution_intent_id
- run_reason `text` not null
- result_state `text` not null
- broker_truth_json `jsonb` not null default '{}'
- local_truth_json `jsonb` not null default '{}'
- conflict_flag `boolean` not null default false
- incident_id `text` null
- started_at `timestamptz` not null default now()
- completed_at `timestamptz` null

Indexes:
- `(execution_intent_id, started_at desc)`
- `(result_state, started_at desc)`
- `(conflict_flag, started_at desc)`

## 7.13 core.broker_positions

Purpose:
- normalized latest known broker position state

Columns:
- broker_position_id `text` PK
- environment `text` not null
- account_id `text` not null
- symbol `text` not null
- side `text` not null
- quantity `numeric(18,4)` not null
- avg_price `numeric(18,8)` not null
- stop_loss `numeric(18,8)` null
- take_profit `numeric(18,8)` null
- authoritative_snapshot_at `timestamptz` not null
- local_status `text` not null
- metadata_json `jsonb` not null default '{}'

Indexes:
- `(account_id, symbol)`
- `(symbol, authoritative_snapshot_at desc)`
- `(local_status, authoritative_snapshot_at desc)`

## 7.14 core.observations

Purpose:
- workflow-correlated observations and monitoring facts

Columns:
- observation_id `text` PK
- workflow_id `text` not null FK
- observation_type `text` not null
- severity `text` not null
- source `text` not null
- payload_ref `text` null
- payload_json `jsonb` null
- authority_state `text` not null
- freshness_status `text` not null
- occurred_at `timestamptz` not null default now()

Indexes:
- `(workflow_id, occurred_at desc)`
- `(severity, occurred_at desc)`
- `(source, occurred_at desc)`

## 7.15 core.evaluation_reports

Purpose:
- evaluator outputs for workflows, steps, proposals, or reports

Columns:
- evaluation_id `text` PK
- workflow_id `text` null FK
- target_type `text` not null
- target_ref `text` not null
- rubric_name `text` not null
- rubric_scores_json `jsonb` not null
- overall_score `numeric(6,4)` not null
- verdict `text` not null
- issues_json `jsonb` not null default '[]'
- improvement_actions_json `jsonb` not null default '[]'
- evaluator_identity `text` not null
- evaluation_model_id `text` null
- created_at `timestamptz` not null default now()

Indexes:
- `(workflow_id, created_at desc)`
- `(target_type, target_ref)`
- `(rubric_name, created_at desc)`

## 7.16 core.incidents

Purpose:
- incident lifecycle state

Columns:
- incident_id `text` PK
- severity `text` not null
- state `text` not null
- alert_type `text` not null
- source `text` not null
- summary `text` not null
- opened_at `timestamptz` not null default now()
- resolved_at `timestamptz` null
- recommended_action `text` null
- metadata_json `jsonb` not null default '{}'

Indexes:
- `(state, opened_at desc)`
- `(severity, opened_at desc)`

## 7.17 gov.kill_switch_events

Purpose:
- kill switch state changes and recoveries

Columns:
- kill_event_id `bigserial` PK
- previous_state `text` not null
- new_state `text` not null
- trigger_type `text` not null
- reason_code `text` not null
- actor_type `text` not null
- actor_id `text` not null
- workflow_id `text` null
- created_at `timestamptz` not null default now()
- metadata_json `jsonb` not null default '{}'

Indexes:
- `(new_state, created_at desc)`
- `(created_at desc)`

## 7.18 gov.approvals

Purpose:
- approval request metadata

Columns:
- approval_id `text` PK
- action_type `text` not null
- target_ref_type `text` not null
- target_ref_id `text` not null
- required_count `integer` not null
- state `text` not null
- compliance_profile_id `text` null
- expires_at `timestamptz` null
- created_by_actor_type `text` not null
- created_by_actor_id `text` not null
- created_at `timestamptz` not null default now()
- decided_at `timestamptz` null
- metadata_json `jsonb` not null default '{}'

Indexes:
- `(state, created_at desc)`
- `(target_ref_type, target_ref_id)`
- `(expires_at)`

## 7.19 gov.approval_votes

Purpose:
- one row per approver decision

Columns:
- vote_id `bigserial` PK
- approval_id `text` not null FK -> gov.approvals.approval_id
- approver_role `text` not null
- approver_id `text` not null
- decision `text` not null
- reason_code `text` null
- rationale `text` null
- voted_at `timestamptz` not null default now()

Constraints:
- unique `(approval_id, approver_id)`

Indexes:
- `(approval_id, voted_at)`
- `(approver_id, voted_at desc)`

## 7.20 gov.override_requests

Purpose:
- requests to supersede blocked actions

Columns:
- override_request_id `text` PK
- original_decision_ref `text` not null
- original_action_ref `text` not null
- requested_action_json `jsonb` not null
- reason_code `text` not null
- rationale `text` not null
- requested_expiry `timestamptz` null
- required_roles_json `jsonb` not null default '[]'
- state `text` not null
- created_by_actor_id `text` not null
- created_at `timestamptz` not null default now()

Indexes:
- `(state, created_at desc)`

## 7.21 gov.override_decisions

Purpose:
- final result of override process

Columns:
- override_decision_id `text` PK
- override_request_id `text` not null FK -> gov.override_requests.override_request_id
- decision `text` not null
- effective_until `timestamptz` null
- downstream_execution_ref `text` null
- audit_ref `text` null
- created_at `timestamptz` not null default now()

Indexes:
- `(override_request_id)`
- `(decision, created_at desc)`

## 7.22 gov.policies

Purpose:
- versioned policies and active windows

Columns:
- policy_version_id `text` PK
- policy_type `text` not null
- version `text` not null
- content_hash `text` not null
- content_ref `text` null
- effective_from `timestamptz` not null
- effective_to `timestamptz` null
- status `text` not null
- created_at `timestamptz` not null default now()
- created_by `text` not null

Constraints:
- unique `(policy_type, version)`

Indexes:
- `(policy_type, status, effective_from desc)`
- `(effective_from, effective_to)`

## 7.23 gov.compliance_profiles

Purpose:
- active compliance profile definitions

Columns:
- compliance_profile_id `text` PK
- name `text` not null
- version `text` not null
- profile_json `jsonb` not null
- active_flag `boolean` not null default false
- created_at `timestamptz` not null default now()

Constraints:
- unique `(name, version)`

Indexes:
- `(name, active_flag)`

## 7.24 gov.strategy_registry

Purpose:
- strategy lifecycle registry

Columns:
- strategy_id `text` PK
- strategy_name `text` not null
- strategy_family `text` not null
- current_lifecycle_state `text` not null
- code_hash `text` not null
- parameter_hash `text` not null
- owner_id `text` null
- created_at `timestamptz` not null default now()
- updated_at `timestamptz` not null default now()

Indexes:
- `(current_lifecycle_state, updated_at desc)`
- `(strategy_family, updated_at desc)`

## 7.25 gov.strategy_promotions

Purpose:
- lifecycle transition evidence and approvals

Columns:
- promotion_id `text` PK
- strategy_id `text` not null FK -> gov.strategy_registry.strategy_id
- from_state `text` not null
- to_state `text` not null
- evidence_bundle_id `text` not null
- approver_1_id `text` not null
- approver_2_id `text` null
- effective_at `timestamptz` not null
- rationale `text` null
- created_at `timestamptz` not null default now()

Indexes:
- `(strategy_id, effective_at desc)`
- `(to_state, effective_at desc)`

## 7.26 research.evidence_bundles

Purpose:
- metadata for research evidence packages

Columns:
- evidence_bundle_id `text` PK
- workflow_id `text` null FK -> core.workflows.workflow_id
- bundle_type `text` not null
- summary `text` not null
- content_ref `text` null
- content_hash `text` not null
- freshness_status `text` not null
- created_at `timestamptz` not null default now()

Indexes:
- `(workflow_id, created_at desc)`
- `(bundle_type, created_at desc)`

## 7.27 audit.trajectory_logs

Purpose:
- metadata index for step-level trajectory logs stored in artifact storage or DB

Columns:
- log_id `text` PK
- workflow_id `text` not null FK
- correlation_id `text` not null
- agent_name `text` not null
- phase `text` not null
- iteration_no `integer` not null
- input_schema `text` not null
- input_hash `text` not null
- output_schema `text` not null
- output_hash `text` not null
- tool_calls_json `jsonb` not null default '[]'
- observation_payload_ref `text` null
- evaluation_output_ref `text` null
- latency_ms `integer` not null
- token_usage_json `jsonb` null
- final_state `text` not null
- signature `text` null
- artifact_ref `text` null
- created_at `timestamptz` not null default now()

Indexes:
- `(workflow_id, created_at)`
- `(correlation_id)`
- `(agent_name, created_at desc)`

Partitioning:
- strong candidate for monthly partitioning

## 7.28 audit.replay_bundles

Purpose:
- immutable replay package metadata

Columns:
- replay_bundle_id `text` PK
- workflow_id `text` not null FK -> core.workflows.workflow_id
- bundle_hash `text` not null
- object_store_uri `text` not null
- completeness_status `text` not null
- export_profile `text` null
- integrity_manifest_ref `text` null
- created_at `timestamptz` not null default now()

Indexes:
- `(workflow_id, created_at desc)`
- `(bundle_hash)`

## 7.29 audit.legal_holds

Purpose:
- prevent purge of protected records

Columns:
- legal_hold_id `bigserial` PK
- target_type `text` not null
- target_ref_id `text` not null
- hold_reason `text` not null
- placed_by_actor_id `text` not null
- placed_at `timestamptz` not null default now()
- released_at `timestamptz` null

Indexes:
- `(target_type, target_ref_id)`
- `(released_at)`

---

## 7. Reference and Lookup Tables

Recommended small lookup/reference tables:
- `ref.workflow_states`
- `ref.proposal_states`
- `ref.decision_types`
- `ref.approval_states`
- `ref.incident_states`
- `ref.kill_switch_states`
- `ref.operating_modes`
- `ref.strategy_lifecycle_states`
- `ref.severity_levels`

These may be implemented as strict lookup tables or as application-validated enums depending on deployment preference. For highly governed environments, lookup tables are preferred.

---

## 7. Object Storage and Artifact Linking

### 7.1 Artifact Classes

Use object storage for:
- full market/account/portfolio snapshots
- raw broker receipts
- replay bundles
- evaluation detail payloads
- research evidence package contents
- signed audit manifests

### 7.2 Artifact Reference Pattern

All artifact refs should be opaque IDs or URIs plus hash metadata.

Recommended metadata fields:
- artifact_ref
- object_store_uri
- content_hash
- content_type
- compression_type
- created_at

### 7.3 DB vs Artifact Guidance

Store inline in DB if:
- payload is small
- queried frequently
- needed for filtering or reporting

Store in object storage if:
- payload is large or nested
- immutable and retrieved by reference
- primarily for replay/audit/export

---

## 8. Integrity, Concurrency, and Idempotency Rules

### 8.1 Workflow Concurrency

Use optimistic concurrency on mutable workflow records:
- update by `(workflow_id, version_no)`
- increment `version_no` on successful write
- stale version write failure triggers re-plan path

### 8.2 Execution Idempotency

Protect live side effects through:
- unique constraint on `core.execution_intents.idempotency_key`
- optional unique client_order_id if broker mapping allows
- reconciliation before retrying uncertain sends

### 8.3 Approval Integrity

- one approver can vote only once per approval
- approval completion should be materialized in `gov.approvals.state`
- dual-auth actions must verify distinct approver identities

### 8.4 Audit Integrity

Recommended:
- append-only inserts for transition, vote, incident, and log tables
- hash chaining for audit rows or signed manifests for grouped artifacts
- prohibit destructive updates except via archival or legal-hold-aware administrative process

---

## 9. Partitioning, Retention, and Archival

### 9.1 Partitioning Candidates

Likely monthly or weekly partitions for:
- `core.workflow_transitions`
- `core.observations`
- `audit.trajectory_logs`

Potential partitioning by time plus environment for very large deployments.

### 9.2 Retention Policy Model

Retention is compliance-profile-driven.

Recommended categories:
- operational hot data in primary DB
- warm archive in cheaper storage
- immutable replay bundles retained per profile
- legal hold overrides automated purge

### 9.3 Purge Rules

No automatic purge if:
- target is under legal hold
- target is linked to unresolved incident
- target is part of required replay/audit package under active policy

### 9.4 Archival Process

1. select eligible rows by profile and age
2. verify no legal hold
3. export to archival artifact package with manifest
4. confirm integrity
5. soft-delete or move partition per policy

---

## 10. Migration and Change Control

### 10.1 Migration Rules

- additive migrations preferred
- destructive migrations require explicit approval
- every migration must be reversible where practical
- schema versions should align with application release notes

### 10.2 Migration File Conventions

Recommended naming:
- `YYYYMMDDHHMM__create_workflows.sql`
- `YYYYMMDDHHMM__add_execution_send_attempts.sql`

### 10.3 Seed Data

Initial seeds should include:
- operating modes
- compliance profiles
- workflow states
- proposal states
- decision enums
- baseline policies
- kill-switch states
- strategy lifecycle states

---

## 11. Example DDL Fragments

### 11.1 workflows

```sql
create table core.workflows (
    workflow_id text primary key,
    workflow_type text not null,
    environment text not null,
    operating_mode text not null,
    state text not null,
    objective text not null,
    scope_json jsonb not null default '{}'::jsonb,
    initiator_type text not null,
    initiator_id text not null,
    timeout_policy_json jsonb not null default '{}'::jsonb,
    stop_conditions_json jsonb not null default '[]'::jsonb,
    current_step_id text null,
    version_no integer not null default 1,
    created_at timestamptz not null default now(),
    updated_at timestamptz not null default now(),
    completed_at timestamptz null,
    terminal_reason text null
);
create index ix_workflows_state_updated on core.workflows (state, updated_at desc);
create index ix_workflows_type_created on core.workflows (workflow_type, created_at desc);
```

### 11.2 risk_decisions

```sql
create table risk.risk_decisions (
    risk_decision_id text primary key,
    risk_request_id text not null references risk.risk_assessment_requests(risk_request_id),
    proposal_id text not null references core.trade_proposals(proposal_id),
    workflow_id text not null references core.workflows(workflow_id),
    decision text not null,
    rationale_text text not null,
    risk_metrics_snapshot_json jsonb not null,
    freshness_expiry timestamptz not null,
    policy_version_id text not null,
    formula_version text not null,
    provenance_bundle_id text null,
    approval_token text null,
    freshness_status text not null default 'fresh',
    created_at timestamptz not null default now(),
    constraint uq_risk_decisions_approval_token unique (approval_token)
);
create index ix_risk_decisions_proposal on risk.risk_decisions (proposal_id, created_at desc);
create index ix_risk_decisions_expiry on risk.risk_decisions (freshness_expiry);
```

### 11.3 execution_intents

```sql
create table core.execution_intents (
    execution_intent_id text primary key,
    workflow_id text not null references core.workflows(workflow_id),
    proposal_id text not null references core.trade_proposals(proposal_id),
    risk_decision_id text not null references risk.risk_decisions(risk_decision_id),
    action_type text not null,
    symbol text not null,
    side text not null,
    order_type text not null,
    size_json jsonb not null,
    price_params_json jsonb not null default '{}'::jsonb,
    sl_tp_params_json jsonb not null default '{}'::jsonb,
    idempotency_key text not null unique,
    client_order_id text null,
    status text not null,
    expiry_at timestamptz null,
    pre_send_validation_snapshot_ref text null,
    created_at timestamptz not null default now(),
    updated_at timestamptz not null default now()
);
create index ix_execution_intents_status_created on core.execution_intents (status, created_at desc);
create index ix_execution_intents_client_order on core.execution_intents (client_order_id);
```

---

## 12. Reporting and Query Guidance

### 12.1 Common Operator Queries

- active workflows by state
- proposals awaiting risk
- decisions expiring soon
- approvals pending by role
- execution intents under reconciliation
- incidents still active
- strategies in LIVE_LIMITED / LIVE_PRODUCTION
- replay bundle completeness gaps

### 12.2 Common Audit Queries

- full workflow transition history
- all live actions linked to a policy version
- override actions and approver identities
- all executions under a compliance profile
- all records under legal hold
- all receipts with broker/local conflict

### 12.3 Performance Guidance

- avoid scanning large JSONB fields for core dashboard views
- denormalize selective searchable fields into relational columns
- use artifact refs for heavy payloads
- partition high-volume event tables
- use partial indexes for active states where appropriate

---

## 13. Acceptance Checklist

The DB schema is production-ready only if:

- all core tables are created
- PK/FK relationships validate
- workflow and execution uniqueness guarantees exist
- idempotency uniqueness is enforced
- approval distinct-voter rule is enforced
- partitioning plan is defined for high-volume tables
- retention and legal-hold strategy is defined
- migration rollback policy exists
- replay and artifact refs are covered
- seed/reference data is documented

---

## 14. Suggested Next Steps

After this document:
1. generate full SQL migration scripts
2. define ORM models and repository layer
3. define partitioning and archival jobs
4. bind DB tables to canonical schemas and replay pipeline
5. build reporting queries and dashboard read models


---

## 8. Schema Registry Model
### 12.1 Registry Responsibilities

The schema registry shall:

- store every canonical contract definition
- map `contract_type` to active schema versions
- expose compatibility metadata
- track effective dates and deprecation dates
- support runtime validation
- support replay interpretation of historical contracts

### 12.2 Registry Record

Each registry record must include:

- contract_type
- schema_version
- semantic_version
- status: `draft | active | deprecated | retired`
- effective_from
- deprecated_from optional
- compatibility_policy
- payload_hash
- JSON Schema reference
- Pydantic model reference
- owning domain team
- changelog summary

### 12.3 Versioning Policy

Use semantic versioning:
- major: breaking change
- minor: backward-compatible additive change
- patch: documentation or non-structural validation clarification

Examples:
- `1.0.0` initial production contract
- `1.1.0` additive optional field
- `2.0.0` removed/renamed/changed required field or incompatible enum semantics

---

## 13. Shared Envelope Specification

### 13.1 Canonical Envelope

Every canonical message must include the following envelope:

```json
{
  "schema_version": "1.0.0",
  "contract_type": "WorkflowIntent",
  "workflow_id": "wf_01JABC...",
  "correlation_id": "corr_01JABC...",
  "causation_id": "evt_01JABC...",
  "timestamp_utc": "2026-04-08T10:15:30Z",
  "originator": {
    "type": "agent",
    "id": "strategy_agent_v4"
  },
  "environment": "prod",
  "operating_mode": "MODE-003",
  "payload": {}
}
```

### 13.2 Envelope Fields

| Field | Type | Required | Description |
|---|---|---:|---|
| schema_version | string | Y | contract schema version |
| contract_type | string | Y | canonical message family |
| workflow_id | string | Y | workflow identifier |
| correlation_id | string | Y | ties related messages together |
| causation_id | string | Y | immediate upstream triggering event/message |
| timestamp_utc | datetime | Y | UTC creation time |
| originator.type | enum | Y | `user | agent | service | tool | operator` |
| originator.id | string | Y | logical originator identifier |
| environment | enum | Y | `dev | test | paper | staging | prod` |
| operating_mode | enum | Y | `MODE-000` to `MODE-004` |
| payload | object | Y | message-specific payload |

### 13.3 Optional Envelope Extensions

Optional but recommended:
- tenant_id
- account_scope_id
- strategy_scope_id
- compliance_profile_id
- content_hash
- signature
- trace_id
- replay_bundle_hint

### 13.4 Envelope Pydantic Base

```python
from datetime import datetime
from typing import Any, Dict, Literal, Optional
from pydantic import BaseModel, Field

class Originator(BaseModel):
    type: Literal["user", "agent", "service", "tool", "operator"]
    id: str

class CanonicalEnvelope(BaseModel):
    schema_version: str = "1.0.0"
    contract_type: str
    workflow_id: str
    correlation_id: str
    causation_id: str
    timestamp_utc: datetime = Field(default_factory=datetime.utcnow)
    originator: Originator
    environment: Literal["dev", "test", "paper", "staging", "prod"]
    operating_mode: Literal["MODE-000", "MODE-001", "MODE-002", "MODE-003", "MODE-004"]
    payload: Dict[str, Any]
    tenant_id: Optional[str] = None
    account_scope_id: Optional[str] = None
    strategy_scope_id: Optional[str] = None
    compliance_profile_id: Optional[str] = None
    content_hash: Optional[str] = None
    signature: Optional[str] = None
    trace_id: Optional[str] = None
```

---

## 14. Shared Primitive Types

### 14.1 Identifier Types

Recommended prefixes:
- workflow_id → `wf_`
- correlation_id → `corr_`
- causation/event id → `evt_`
- hypothesis_id → `hyp_`
- proposal_id → `prop_`
- risk_decision_id → `risk_`
- execution_intent_id → `exec_`
- receipt_id → `rcpt_`
- incident_id → `inc_`
- replay_bundle_id → `rpb_`
- approval_id → `appr_`
- strategy_id → `strat_`

### 14.2 Common Enums

```python
OperatingMode = Literal["MODE-000", "MODE-001", "MODE-002", "MODE-003", "MODE-004"]
DecisionEnum = Literal["APPROVE", "APPROVE_WITH_LIMITS", "REJECT", "FORCE_EXIT"]
SeverityEnum = Literal["INFO", "WARNING", "INCIDENT", "CRITICAL_INCIDENT", "KILL_SWITCH_TRIGGER"]
AuthorityStateEnum = Literal["AUTHORITATIVE", "PROVISIONAL", "UNDER_RECONCILIATION"]
ApprovalStateEnum = Literal["PENDING", "PARTIALLY_APPROVED", "APPROVED", "REJECTED", "EXPIRED"]
```

### 14.3 Evidence Primitive

```python
from datetime import datetime
from typing import Literal
from pydantic import BaseModel, confloat

class EvidenceItem(BaseModel):
    source: str
    source_type: Literal["sql", "vector", "web", "market", "broker", "memory", "document", "experiment"]
    summary: str
    confidence: confloat(ge=0.0, le=1.0)
    timestamp_utc: datetime
    freshness_seconds: int
    content_hash: str | None = None
```

### 14.4 Limit Constraint Primitive

```python
from typing import Any, Dict, Literal
from pydantic import BaseModel

class LimitConstraint(BaseModel):
    constraint_type: Literal[
        "max_size", "max_deviation", "mandatory_stop", "mandatory_tp",
        "valid_until", "session_window", "only_reduce", "symbol_allowlist",
        "max_slippage_bps", "max_spread_points"
    ]
    value: Dict[str, Any]
```

### 14.5 Provenance Primitive

```python
from typing import Optional
from pydantic import BaseModel

class ProvenanceBundleRef(BaseModel):
    bundle_id: str
    market_snapshot_ref: Optional[str] = None
    account_snapshot_ref: Optional[str] = None
    symbol_metadata_snapshot_ref: Optional[str] = None
    strategy_id: Optional[str] = None
    strategy_code_hash: Optional[str] = None
    feature_pipeline_version: Optional[str] = None
    policy_version: Optional[str] = None
    model_id: Optional[str] = None
    prompt_hash: Optional[str] = None
```

---

## 11. Canonical Message Families

### 11.1 WorkflowIntent

Purpose:
- starts or resumes a workflow

Payload fields:
- objective
- workflow_type
- trigger_type
- requested_scope
- constraints
- permitted_tools
- stop_conditions
- timeout_policy
- evaluation_criteria

Example:

```json
{
  "contract_type": "WorkflowIntent",
  "schema_version": "1.0.0",
  "workflow_id": "wf_01",
  "correlation_id": "corr_01",
  "causation_id": "evt_01",
  "timestamp_utc": "2026-04-08T10:15:30Z",
  "originator": {"type": "user", "id": "user_123"},
  "environment": "prod",
  "operating_mode": "MODE-001",
  "payload": {
    "objective": "Review EURUSD trade idea",
    "workflow_type": "trade_review",
    "trigger_type": "user_action",
    "requested_scope": {
      "account_id": "acct_prod_01",
      "symbol_group": ["EURUSD"]
    },
    "constraints": {
      "max_iterations": 3
    },
    "permitted_tools": ["market_data_mcp", "sql_mcp", "risk_analytics_mcp"],
    "stop_conditions": ["human_escalation", "proposal_completed"],
    "timeout_policy": {"seconds": 120},
    "evaluation_criteria": ["schema_compliance", "risk_awareness"]
  }
}
```

Pydantic:

```python
from typing import Dict, List, Literal, Optional
from pydantic import BaseModel

class WorkflowIntentPayload(BaseModel):
    objective: str
    workflow_type: Literal[
        "trade_review", "portfolio_opt", "research_report",
        "paper_execution", "live_execution", "incident_triage",
        "promotion_review", "emergency_exit"
    ]
    trigger_type: Literal["user_action", "schedule", "market_event", "internal_event"]
    requested_scope: Dict[str, object]
    constraints: Dict[str, object] = {}
    permitted_tools: List[str] = []
    stop_conditions: List[str] = []
    timeout_policy: Dict[str, object] = {}
    evaluation_criteria: List[str] = []
```

### 11.2 WorkflowPlan

Purpose:
- formalizes the executable plan after reasoning

Payload fields:
- plan_id
- selected_pattern
- phase_steps
- assigned_agents
- tool_permissions
- success_conditions
- escalation_conditions

### 11.3 TradeHypothesis

Purpose:
- output of StrategyAgent; not executable

Payload fields:
- hypothesis_id
- symbol
- direction
- thesis
- entry_rationale
- invalidation_rationale
- stop_loss_logic
- take_profit_logic
- holding_horizon
- confidence
- calibration_note
- evidence
- required_validation_data
- strategy_family
- feature_version
- strategy_code_hash

Pydantic:

```python
from typing import List, Literal, Optional
from pydantic import BaseModel, confloat

class TradeHypothesisPayload(BaseModel):
    hypothesis_id: str
    symbol: str
    direction: Literal["buy", "sell"]
    thesis: str
    entry_rationale: str
    invalidation_rationale: str
    stop_loss_logic: Dict[str, object]
    take_profit_logic: Dict[str, object] | None = None
    holding_horizon: Literal["intraday", "swing", "position"]
    confidence: confloat(ge=0.0, le=1.0)
    calibration_note: str
    evidence: List[EvidenceItem]
    required_validation_data: List[str]
    strategy_family: str
    feature_version: str
    strategy_code_hash: str
```

### 11.4 TradeProposal

Purpose:
- validated transformation of a hypothesis toward risk review

Payload fields:
- proposal_id
- source_hypothesis_id
- symbol
- direction
- candidate_price_logic
- proposed_size
- operating_envelope
- session_restrictions
- expiry_at
- transformation_version
- readiness_state

### 11.5 RiskAssessmentRequest

Purpose:
- input to RiskGovernor

Payload fields:
- risk_request_id
- proposal_id
- action_type
- account_snapshot_ref
- portfolio_snapshot_ref
- market_snapshot_ref
- requested_freshness_classes
- strategy_lifecycle_state
- active_policy_bundle
- compliance_profile_id
- current_kill_switch_state

### 11.6 RiskAssessmentDecision

Purpose:
- output of RiskGovernor and mandatory gate for live side effects

Payload fields:
- risk_decision_id
- proposal_id
- decision
- reasons
- limit_constraints
- risk_metrics_snapshot
- freshness_expiry
- policy_version
- formula_version
- provenance_bundle_ref
- approval_token optional
- force_exit_symbols optional

Example:

```json
{
  "contract_type": "RiskAssessmentDecision",
  "schema_version": "1.0.0",
  "workflow_id": "wf_01",
  "correlation_id": "corr_01",
  "causation_id": "evt_07",
  "timestamp_utc": "2026-04-08T10:16:10Z",
  "originator": {"type": "agent", "id": "risk_governor_agent"},
  "environment": "prod",
  "operating_mode": "MODE-003",
  "payload": {
    "risk_decision_id": "risk_01",
    "proposal_id": "prop_01",
    "decision": "APPROVE_WITH_LIMITS",
    "reasons": [
      "Portfolio correlation acceptable",
      "Position size reduced due to elevated volatility percentile"
    ],
    "limit_constraints": [
      {
        "constraint_type": "max_size",
        "value": {"volume_lots": 0.30}
      },
      {
        "constraint_type": "max_deviation",
        "value": {"points": 8}
      }
    ],
    "risk_metrics_snapshot": {
      "var_95": 0.024,
      "expected_shortfall_95": 0.031,
      "exposure_pct": 0.07,
      "correlation_score": 0.44
    },
    "freshness_expiry": "2026-04-08T10:16:40Z",
    "policy_version": "risk_policy_3.2.1",
    "formula_version": "risk_formula_1.4.0",
    "provenance_bundle_ref": {
      "bundle_id": "prov_01",
      "account_snapshot_ref": "acctsnap_101",
      "market_snapshot_ref": "mktsnap_455"
    },
    "approval_token": "token_abc123"
  }
}
```

Pydantic:

```python
from datetime import datetime
from typing import Dict, List, Literal, Optional
from pydantic import BaseModel

class RiskAssessmentDecisionPayload(BaseModel):
    risk_decision_id: str
    proposal_id: str
    decision: Literal["APPROVE", "APPROVE_WITH_LIMITS", "REJECT", "FORCE_EXIT"]
    reasons: List[str]
    limit_constraints: List[LimitConstraint] = []
    risk_metrics_snapshot: Dict[str, float]
    freshness_expiry: datetime
    policy_version: str
    formula_version: str
    provenance_bundle_ref: ProvenanceBundleRef
    approval_token: Optional[str] = None
    force_exit_symbols: List[str] = []
```

### 11.7 ExecutionIntent

Purpose:
- approved broker action request

Payload fields:
- execution_intent_id
- proposal_id
- risk_decision_id
- broker_action_type
- symbol
- side
- size
- order_type
- price_params
- sl_tp_params
- idempotency_key
- expiry_time
- pre_send_validation_snapshot_ref

### 11.8 ExecutionReceipt

Purpose:
- normalized broker response

Payload fields:
- receipt_id
- execution_intent_id
- broker
- broker_order_id
- broker_deal_id
- status
- requested_price
- fill_price
- fill_qty
- spread_points
- slippage_points
- slippage_bps
- broker_message
- broker_retcode
- receipt_hash
- authoritative_state

### 11.9 ObservationEvent

Purpose:
- observed state change, tool output, or environment signal tied to workflow context

Payload fields:
- observation_id
- observation_type
- severity
- source
- payload_ref_or_inline
- authority_state
- freshness_status
- observed_at

### 11.10 EvaluationReport

Purpose:
- workflow or step evaluation result

Payload fields:
- evaluation_id
- target_type
- target_ref
- rubric_name
- rubric_scores
- overall_score
- verdict
- issues
- improvement_actions
- evaluator_identity
- evaluation_model_id

### 11.11 IncidentAlert

Purpose:
- incident or warning emission

Payload fields:
- incident_id optional
- severity
- alert_type
- summary
- source
- related_refs
- recommended_action
- incident_state if applicable

### 11.12 OverrideRequest

Purpose:
- request to supersede a blocked decision under policy

Payload fields:
- override_request_id
- original_decision_ref
- original_action_ref
- requested_action
- reason_code
- rationale
- requested_expiry
- required_roles

### 11.13 OverrideDecision

Purpose:
- result of override workflow

Payload fields:
- override_decision_id
- override_request_id
- decision
- approver_records
- effective_until
- downstream_execution_ref optional
- audit_ref

### 11.14 ReplayBundle

Purpose:
- immutable workflow reconstruction package

Payload fields:
- replay_bundle_id
- workflow_id
- completeness_status
- included_refs
- integrity_manifest
- export_profile
- generated_at

---

## 12. Validation, Compatibility, and Evolution Rules

### 12.1 Validation Levels

Each contract must pass:
1. JSON/Pydantic schema validation
2. enum/value validation
3. reference existence validation where needed
4. freshness validation for execution-critical contracts
5. policy validation for governed actions

### 12.2 Compatibility Rules

- consumers must tolerate unknown additive fields in the same major version
- required field removal or semantic change requires major version increase
- deprecated fields may coexist for one major version window
- replay engine must be able to resolve historical versions via registry metadata

### 12.3 Required Hashes and Signatures

Execution-critical contracts must include or be associated with:
- content_hash
- provenance bundle reference
- signature or signed storage manifest where applicable

Recommended hashing:
- canonical JSON serialization
- SHA-256 hash
- base64 or hex encoding

### 12.4 Freshness Requirements in Schemas

Execution-critical payloads must carry:
- snapshot refs
- freshness-expiry or TTL-aligned time fields
- sufficient metadata to verify HOT/WARM artifact validity

### 12.5 Failure Contract

Validation failure response envelope:

```json
{
  "schema_version": "1.0.0",
  "contract_type": "ValidationFailure",
  "workflow_id": "wf_01",
  "correlation_id": "corr_01",
  "causation_id": "evt_09",
  "timestamp_utc": "2026-04-08T10:16:12Z",
  "originator": {"type": "service", "id": "execution_service"},
  "environment": "prod",
  "operating_mode": "MODE-003",
  "payload": {
    "failure_id": "vf_01",
    "failed_contract_type": "ExecutionIntent",
    "failed_schema_version": "1.0.0",
    "error_code": "STALE_RISK_DECISION",
    "error_message": "Risk decision expired prior to broker submission",
    "field_errors": [],
    "action_taken": "BLOCKED_BY_POLICY"
  }
}
```

---

## 13. JSON Schema Packaging Standard

For each canonical contract, the repository must provide:
- `schema.json`
- `model.py`
- `examples/valid/*.json`
- `examples/invalid/*.json`
- `CHANGELOG.md`
- `README.md`

Suggested repository layout:

```text
contracts/
  workflow_intent/
    schema.json
    model.py
    README.md
    examples/
  workflow_plan/
  trade_hypothesis/
  trade_proposal/
  risk_assessment_request/
  risk_assessment_decision/
  execution_intent/
  execution_receipt/
  observation_event/
  evaluation_report/
  incident_alert/
  override_request/
  override_decision/
  replay_bundle/
```

---

## 14. Reference Implementation Notes

### 14.1 Recommended Base Classes

```python
class CanonicalMessage(BaseModel):
    envelope: CanonicalEnvelope

class VersionedPayload(BaseModel):
    schema_version: str = "1.0.0"
```

### 14.2 Recommended Validation Flow

```python
def validate_canonical_message(message: dict, registry) -> CanonicalMessage:
    envelope = CanonicalEnvelope.model_validate(message)
    schema = registry.resolve(
        contract_type=envelope.contract_type,
        schema_version=envelope.schema_version
    )
    payload_model = schema.payload_model
    payload_model.model_validate(envelope.payload)
    return CanonicalMessage(envelope=envelope)
```

### 14.3 Recommended Canonical Serialization

- sort keys
- use UTC ISO-8601 with `Z`
- no NaN/Infinity
- decimals serialized explicitly
- normalized enum casing

---

## 11. Acceptance Checklist

A canonical schema family is production-ready only if all are true:

- schema registered and active
- JSON Schema published
- Pydantic model implemented
- valid/invalid examples added
- compatibility notes documented
- replay compatibility confirmed
- tests exist for parsing and round-tripping
- execution-critical freshness fields defined where applicable
- hashes/signature approach documented

---

## 12. Suggested Next Steps

After this document:
1. generate machine-readable JSON Schema files for every canonical contract
2. implement the schema registry
3. bind each schema to API, workflow, and MCP use points
4. generate contract validation tests and fixtures