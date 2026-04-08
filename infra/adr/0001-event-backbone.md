# ADR 0001: Event Backbone Choice

- Status: Accepted
- Date: 2026-04-08
- Owners: HaruQuant engineering
- Related Plan Item: `docs/agentic_ai/implementation_plan.md`

## Context

The target agentic architecture requires an event backbone for:
- workflow state transition events
- observation and monitoring events
- approval and incident notifications
- live dashboard fan-out

The target architecture documents already assume Redis in the baseline topology and list `Redis Streams vs RabbitMQ/Kafka for event backbone` as an open design decision.

Current repo state:
- the existing HaruQuant runtime does not have a production event bus abstraction yet
- there is no existing RabbitMQ or Kafka deployment footprint to preserve
- the migration is intentionally additive and should keep the first backbone choice operationally simple

Constraints that matter now:
- Phase 1 through Phase 4 need a lightweight backbone more than a high-scale distributed log
- the first agentic slices are expected to be small, governance-heavy, and low-throughput
- operator visibility and workflow coordination matter more than massive event retention or stream reprocessing throughput

## Decision

HaruQuant will use Redis Streams as the initial event backbone for the agentic migration.

Scope of this decision:
- workflow and observation event transport
- approval queue signaling
- dashboard-facing near-real-time event fan-out
- short-lived coordination between orchestrator and monitoring paths

This decision does not finalize:
- the long-term immutable audit/event retention store
- large-scale multi-consumer analytics pipelines
- a permanent exclusion of Kafka or RabbitMQ if operational needs change later

## Consequences

Positive:
- aligns with the existing target architecture baseline that already uses Redis for cache/session state
- minimizes operational complexity for the first migration phases
- supports stream-style consumption, replay windows, and consumer groups without introducing a heavier platform early
- keeps the first implementation slice focused on application boundaries rather than infrastructure rollout

Negative:
- Redis Streams is not the best long-term choice if event volume, retention, or fan-out semantics become much larger
- audit-grade retention must still live outside Redis
- future migration may be needed if HaruQuant grows into high-volume event analytics or cross-service streaming workloads

## Alternatives Considered

### RabbitMQ

- summary: mature queueing system with strong delivery semantics
- reason not chosen: adds extra infrastructure without clear first-slice benefit over Redis Streams for the planned low-volume control-plane workflows

### Kafka

- summary: strong distributed log for large-scale streaming and retention
- reason not chosen: heavier operational and schema-governance burden than the current migration phases require

## Implementation Notes

- use Redis Streams for the first event bus abstraction
- keep the application boundary narrow so the transport can be replaced later if needed
- do not use Redis Streams as the system of record for audit retention
- store authoritative workflow, risk, approval, and execution state in PostgreSQL

Re-evaluation triggers:
- materially higher event throughput than expected
- long retention requirements on operational streams
- multi-team consumer growth requiring stronger stream governance

## Follow-Up

- [ ] introduce a small application event bus interface before wiring transport-specific code deeply into services
- [ ] define stream naming, retention defaults, and consumer-group conventions

