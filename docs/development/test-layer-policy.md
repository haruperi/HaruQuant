# Multi-Layer Test Policy

## Purpose

This document defines the test-layer boundaries for the HaruQuant agentic migration.

It exists to keep tests:
- correctly scoped
- easy to place in the repo
- predictable in CI
- aligned with the requirements in `docs/agentic_ai/implementation_plan.md`

Detailed unit-test writing rules already exist in:
- `docs/haruquant/Unit_Tests_Rules.md`

This document defines the higher-level layering policy.

## Test Layers

### Unit

Location:
- `tests/unit/`

Purpose:
- verify small isolated logic units
- validate deterministic domain behavior
- validate canonical contracts, validators, serializers, and pure helpers

Rules:
- no network access
- no live broker access
- no real database dependency
- no cross-service process dependency
- should run in seconds

Examples:
- contract validation
- policy evaluation helpers
- TTL and freshness evaluation
- ID generation

### Integration

Location:
- `tests/integration/`

Purpose:
- verify collaboration between modules, adapters, and service boundaries
- validate storage, messaging, and API wiring against realistic dependencies

Rules:
- may use controlled local dependencies or test doubles
- should validate real boundary behavior, not only mocks
- should avoid external internet services

Examples:
- API plus repository flow
- DB repository behavior
- event bus publishing and consumption
- object-store adapter integration

### Scenario

Location:
- `tests/scenario/`

Purpose:
- verify complete workflow and state-machine behavior
- prove that workflow phases, approvals, and mode restrictions behave correctly

Rules:
- focus on end-to-end behavior inside one bounded system scenario
- validate transitions, gating, and expected terminal states
- use readable business-oriented fixtures and assertions

Examples:
- advisory workflow end-to-end
- mode mismatch rejection
- approval-required execution path

### Chaos

Location:
- `tests/chaos/`

Purpose:
- verify fail-closed and degraded-mode behavior under dependency failure or uncertainty

Rules:
- inject timeouts, stale data, duplicate events, disconnects, and restarts
- assert safety invariants first
- these tests may be slower and run in narrower CI stages than unit tests

Examples:
- broker ack delay
- stale market data
- policy service outage
- restart during in-flight execution

### Security

Location:
- `tests/security/`

Purpose:
- verify authorization, secret isolation, prompt/tool restrictions, and abuse resistance

Rules:
- test the actual access rules and trust boundaries
- include both allowed and denied paths
- prioritize privileged actions, operator roles, and agent/tool restrictions

Examples:
- RBAC for operator endpoints
- forbidden tool use by research workflows
- service-to-service authorization
- prompt injection and retrieval contamination defenses

### Replay

Location:
- `tests/replay/`

Purpose:
- verify that stored artifacts can reconstruct decisions and workflows deterministically

Rules:
- use persisted or fixture-backed historical artifacts
- assert immutability, completeness, and reproducibility
- compare replayed outputs with expected originals where possible

Examples:
- replay bundle completeness
- replay-vs-original comparison
- deterministic reconstruction of workflow state

## Placement Rules

Choose the lowest layer that proves the requirement correctly:
- use `unit` when isolated logic is enough
- use `integration` when a boundary must be exercised
- use `scenario` when workflow behavior matters
- use `chaos` when failure handling is the thing being verified
- use `security` when authorization or abuse resistance is central
- use `replay` when reconstruction and auditability are central

Avoid:
- writing a scenario test when a unit test is enough
- placing failure-injection tests under `integration`
- placing authorization coverage only in non-security suites

## CI Expectations

Default expectation:
- `unit` runs on every change
- `integration` runs on normal backend changes
- `scenario`, `chaos`, `security`, and `replay` run in targeted CI stages as the migration surfaces are added

If a task in the implementation plan names a layer explicitly, that layer is required for completion.

## Requirement Alignment

The agentic migration specifically requires:
- unit coverage for deterministic engines and contracts
- integration coverage for full workflow paths
- scenario coverage for state-machine transitions
- chaos coverage for degraded dependency behavior
- security coverage for authz, tool restrictions, and prompt/retrieval safety
- replay coverage for audit reconstruction
