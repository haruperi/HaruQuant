# ADR 0002: Object Store Choice for Replay and Audit Artifacts

- Status: Accepted
- Date: 2026-04-08
- Owners: HaruQuant engineering
- Related Plan Item: `docs/agentic_ai/implementation_plan.md`

## Context

The target agentic architecture requires an object store for:
- immutable replay bundles
- append-mostly workflow and execution artifacts
- trajectory and evaluation payloads that should not live entirely in OLTP tables
- audit export packages and other compliance-shaped artifact bundles

The design and schema documents already separate operational truth from heavy immutable artifacts:
- PostgreSQL remains the system of record for workflow and governance state
- replay bundles and large immutable payloads belong in object storage with DB metadata and hashes

Constraints that matter now:
- the first migration phases need a simple and portable artifact store
- local development should work without a cloud dependency
- production must support retention controls, object immutability patterns, and clean integration with hash-index metadata in PostgreSQL

## Decision

HaruQuant will standardize on an S3-compatible object store interface for replay, audit, and artifact storage.

Environment mapping:
- local/dev/test: MinIO or another local S3-compatible service
- staging/prod: a managed S3-compatible object store

Scope of this decision:
- replay bundle payloads
- trajectory and evaluation artifact blobs
- audit export packages
- large snapshot payloads that should be referenced from PostgreSQL rather than stored inline

This decision does not finalize:
- the exact cloud vendor for production
- bucket retention and legal-hold policy details
- the final artifact key layout beyond the need for deterministic naming conventions

## Consequences

Positive:
- gives one storage API across local, test, and production environments
- aligns with the target architecture’s `S3[(Artifact Store)]` baseline
- keeps heavy immutable artifacts out of PostgreSQL tables
- supports later retention, versioning, and immutability controls without redesigning the application contract

Negative:
- introduces one more infrastructure dependency beyond PostgreSQL and Redis
- legal-hold and retention policies still need explicit implementation rather than coming “for free”
- local MinIO compatibility testing must be maintained to prevent drift from production behavior

## Alternatives Considered

### Local filesystem only

- summary: write replay and audit artifacts directly to the repo host filesystem
- reason not chosen: weak portability, weak governance story for immutability/retention, and poor fit for multi-environment deployment

### Store heavy artifacts entirely in PostgreSQL

- summary: keep replay payloads and export bundles in database tables or large JSONB blobs
- reason not chosen: increases OLTP storage pressure and mixes mutable operational state with large immutable artifacts

### Vendor-specific cloud object store abstraction

- summary: bind directly to a single cloud provider API
- reason not chosen: unnecessarily narrows the deployment model before the production hosting decision is finalized

## Implementation Notes

- store authoritative artifact metadata and hashes in PostgreSQL
- store large immutable payloads in an S3-compatible bucket
- make the application depend on an internal artifact-store interface rather than direct vendor calls
- use deterministic object keys derived from canonical IDs where possible

Follow-up design work still needed:
- bucket naming and prefix conventions
- retention, versioning, and legal-hold mappings by compliance profile
- artifact integrity manifest format and upload verification flow

## Follow-Up

- [ ] define artifact key naming conventions for replay, trajectory, and export objects
- [ ] define the metadata contract that links PostgreSQL rows to object-store blobs

