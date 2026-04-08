# ADR 0004: Operator API Query Strategy

- Status: Accepted
- Date: 2026-04-08
- Owners: HaruQuant engineering
- Related Plan Item: `docs/agentic_ai/implementation_plan.md`

## Context

The target operator dashboard needs:
- near-real-time status views for workflows, positions, risk decisions, incidents, and evaluation results
- drill-down inspection of workflow phases, inputs, outputs, and rationale
- a clean interface boundary for operator commands and read-side queries

The architecture documents already lean toward a simple BFF shape:
- the interface layer names `API Gateway / BFF`
- the component matrix lists the primary pattern as `REST + WS/SSE`
- the API design section states `REST for commands and queries`

Current repo state:
- the existing backend is FastAPI-based
- there is no existing GraphQL schema, gateway, or client stack to preserve
- the current migration priority is delivery speed and governance clarity rather than query-language flexibility

Constraints that matter now:
- the first operator surfaces should be simple to secure, document, and test
- live dashboard updates still need streaming support
- hot dashboard views may later need denormalized read models without forcing a query-language change

## Decision

HaruQuant will use REST as the initial operator API query model, paired with WebSocket or SSE for live dashboard updates.

Scope of this decision:
- operator-facing read and command endpoints exposed by the API Gateway / BFF
- OpenAPI-described request and response contracts
- live event delivery for dashboard status changes

This decision does not finalize:
- the exact denormalized read models needed for dashboard hot paths
- whether GraphQL may be introduced later for specialized aggregation needs
- the final split between WebSocket and SSE for each live update channel

## Consequences

Positive:
- aligns directly with the existing FastAPI stack and the architecture documents already approved
- keeps the first API surface easy to document with OpenAPI and straightforward to test
- avoids introducing GraphQL schema management, resolver complexity, and client caching decisions early
- keeps query performance work focused on read models and endpoint design rather than transport choice

Negative:
- some dashboard screens may require multiple REST endpoints or purpose-built aggregate responses
- frontend teams do not get GraphQL-style field selection or schema introspection out of the box
- additional endpoint shaping may be needed as operator workflows grow

## Alternatives Considered

### REST plus GraphQL from the start

- summary: use REST for commands and GraphQL for dashboard queries
- reason not chosen: adds schema and resolver complexity before the operator read model and access patterns are proven

### GraphQL only

- summary: unify commands and queries behind a single GraphQL API
- reason not chosen: poor fit for the architecture documents, weak alignment with simple command semantics, and unnecessary migration overhead from the current FastAPI baseline

## Implementation Notes

- keep the API Gateway / BFF REST-first
- use WebSocket or SSE for near-real-time operator updates
- add selective denormalized read models for high-traffic dashboard views when profiling justifies them
- keep endpoint payloads oriented around operator tasks rather than thin table mirrors

Re-evaluation triggers:
- repeated frontend overfetch/underfetch pain across multiple operator surfaces
- proliferation of custom aggregation endpoints that become hard to maintain
- a proven need for cross-domain query composition beyond what focused REST resources provide cleanly

## Follow-Up

- [ ] define the first set of operator read endpoints for workflows, approvals, incidents, and replay views
- [ ] define which dashboard views need denormalized read models before Phase 4 live control plane work
