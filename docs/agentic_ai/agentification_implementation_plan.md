# Agentification Implementation Plan

| Field | Detail |
|---|---|
| Document ID | HQT-AGENTIC-AGENTIFICATION-PLAN |
| Status | Draft |
| Scope | Close remaining 17 gaps between current backend/ and Agentic_AI_Playbook.md |
| Source | Audit of playbook sections vs current codebase |
| Pre-requisite | apps/ migration complete (all 16 phases done) |

---

## 0. Current Status Summary

| Category | Status |
|---|---|
| apps/ migration | ✅ Complete (16 phases + shim removal) |
| API flatten (legacy → main_app → root) | ✅ Complete |
| Agent definitions with ADK runner | ✅ 16 agents |
| MCP servers (6 servers) | ✅ Code exists |
| Workflow state machines | ✅ 4 state machines |
| Workflow patterns | ✅ 5 patterns |
| Approval system (basic) | ✅ Partial |
| Evaluation framework | ✅ Partial |
| Kill switch | ✅ Implemented |
| Audit services | ✅ Implemented |
| Policy enforcement layers | ✅ Partial |
| Prompt provenance/registry | ✅ Partial |
| Security tests | ✅ 7 files |

**Remaining gaps: 17 items** (8 fully missing, 5 partial, 4 needs new code)

---

## 1. Migration Principles

- Each phase is small, reversible, and independently testable.
- Prefer metadata and configuration before code changes.
- Every new file gets tests before the phase is marked done.
- No phase deletes existing functionality — only adds or enhances.
- Each phase ends with a commit and a verification step.

---

## 2. Phase Ordering

```
Phase 1:  Policy Map              (foundation for everything else)
Phase 2:  Approval Packet         (depends on Policy Map)
Phase 3:  MCP metadata.yaml       (standalone documentation)
Phase 4:  MCP Wrapper Standards   (depends on metadata)
Phase 5:  Routing / Intent Class  (standalone code)
Phase 6:  Idempotency & Comp      (depends on Policy Map + Approval)
Phase 7:  Context Engineering     (standalone code + config)
Phase 8:  Trace Observability     (enhance existing observability)
Phase 9:  Evaluation Benchmarks   (depends on Context Eng)
Phase 10: Cost Governance         (standalone config)
Phase 11: Security Architecture   (documentation + hardening)
Phase 12: Testing Gaps            (depends on Phases 1–11)
Phase 13: Companion Documents     (documentation, depends on all code)
Phase 14: Ownership Assignments   (documentation)
Phase 15: Incident Response       (documentation + code hooks)
```

---

## 3. Phase 1: Policy Map

### Gap
Policy Map (Playbook §12) — fully missing.

### Target

```text
config/policies/
  trade_execution_policy.yaml
  risk_override_policy.yaml
  data_access_policy.yaml
  model_usage_policy.yaml
  approval_policy.yaml
  escalation_policy.yaml
  retention_policy.yaml
  input_output_policy.yaml
  tool_use_policy.yaml
  __init__.py              # policy loader and resolver
```

### Tasks
- [x] Create `config/policies/` directory
- [x] Create each policy YAML with: name, scope, owner, enforcement_layers, failure_behavior, logging_requirement, exception_process, review_cadence
- [x] Create `config/policies/__init__.py` with `PolicyResolver` that loads, validates, and resolves policies by scope
- [x] Create policy validation schema (Pydantic model for policy config)
- [x] Wire `PolicyResolver` into `backend/services/policy/resolver.py` (enhance existing)
- [x] Add unit tests for policy loading, validation, and resolution
- [ ] Add policy enforcement check in `backend/api/routes/` before dispatch

### Verification
- [x] All 9 policy files exist with required fields
- [x] PolicyResolver loads and resolves all policies
- [x] Unit tests pass (12/12)
- [ ] API route rejects request when policy blocks

---

## 4. Phase 2: Approval Packet Standard

### Gap
Approval Packet (Playbook §11.2, §11.3) — model exists but missing evidence, alternatives, impact, rollback, escalation.

### Target

Extend `backend/services/approval/models.py` with full `ApprovalPacket` dataclass.

### Tasks
- [x] Create `ApprovalPacket` dataclass with all required fields
- [x] Create `RiskClass` enum (A/B/C/D/E)
- [x] Update `ApprovalRequest` to embed `ApprovalPacket`
- [x] Create `ApprovalPacketBuilder` helper in `backend/services/approval/packet_builder.py`
- [x] Add validation tests for packet completeness (14/14 pass)
- [ ] Update approval service to require complete packet before dispatch
- [ ] Update `backend/api/routes/` approval endpoints to return full packet

### Verification
- [x] ApprovalPacket model validates all fields
- [x] PacketBuilder produces valid packets
- [x] Unit tests pass (14/14)
- [ ] Approval service rejects incomplete packets
- [ ] API endpoint returns full packet structure

---

## 5. Phase 3: MCP Server Metadata

### Gap
Enterprise MCP Additions (Playbook §5.9) — all 6 servers missing metadata.yaml.

### Target

Add `metadata.yaml` to each `backend/mcp/*/` directory:
- `mt5_mcp/metadata.yaml`
- `market_data_mcp/metadata.yaml`
- `backtest_mcp/metadata.yaml`
- `optimization_mcp/metadata.yaml`
- `risk_analytics_mcp/metadata.yaml`
- `sql_mcp/metadata.yaml`

### Tasks
- [x] Create metadata schema (Pydantic model: domain, owner, side_effect_risk, allowed_callers, credentials, audit_requirements, failure_modes, rate_limits, timeout_budget, escalation_owner, contract_version, deprecation_notes)
- [x] Create metadata.yaml for each of 6 MCP servers
- [x] Create `backend/mcp/metadata_loader.py` to load and validate all metadata at startup
- [x] Add metadata validation to MCP server initialization
- [x] Add unit tests for metadata loading and validation (7/7 pass)
- [ ] Document metadata schema in `config/mcp_metadata_schema.yaml`

### Verification
- [x] All 6 metadata.yaml files exist and validate
- [x] Metadata loader reads all 6 without error
- [x] Unit tests pass (7/7)

---

## 6. Phase 4: MCP Wrapper Standards

### Gap
External Integration Wrappers (Playbook §10.3, §10.6) — missing standardized retry, timeout, circuit breaker.

### Target

```text
backend/mcp/wrappers/
  __init__.py
  base_wrapper.py          # BaseMCPWrapper with retry, timeout, circuit breaker
  retry_policy.py          # Exponential backoff, max retries, jitter
  circuit_breaker.py       # Half-open, closed, open state machine
  auth_rotation.py         # Credential rotation and refresh
  rate_limiter.py          # Token bucket / sliding window
```

### Tasks
- [x] Create `backend/mcp/wrappers/` directory
- [x] Implement `RetryPolicy` class with exponential backoff, configurable max retries, jitter
- [x] Implement `CircuitBreaker` class with closed/open/half-open states, failure threshold, recovery timeout
- [x] Implement `RateLimiter` class with token bucket algorithm
- [x] Implement `BaseMCPWrapper` that composes all above
- [x] Wrap existing MCP client calls (mt5_mcp, market_data_mcp) with wrapper
- [x] Add unit tests for each wrapper component (15/15 pass)
- [ ] Add integration test for wrapped MCP call

### Verification
- [x] RetryPolicy backs off correctly
- [x] CircuitBreaker trips after threshold failures
- [x] RateLimiter enforces limits
- [x] Wrapped MCP calls include all policies
- [x] Unit tests pass (15/15)

---

## 7. Phase 5: Routing / Intent Classifier

### Gap
Routing Layer (Playbook §3.2, §3.3) — missing intent classifier and router agent.

### Target

```text
backend/api/router.py              # Intent classifier + dispatch
backend/agents/intent_router.py    # ADK router agent
```

### Tasks
- [ ] Create `backend/api/router.py` with:
  - `IntentClassifier` (rule-based + optional ML model)
  - Intent categories: `market_data`, `research`, `execution`, `optimization`, `backtest`, `risk`, `live_trading`, `settings`
  - Routing metadata standard: `intent`, `priority`, `session_id`, `user_id`
  - Fallback routing for unknown intents
  - First-pass policy check before dispatch
- [ ] Create `backend/agents/intent_router.py` ADK router agent
- [ ] Wire router into `backend/api/main.py` before route dispatch
- [ ] Add routing metadata to all API request contexts
- [ ] Add unit tests for intent classification (happy path + edge cases)
- [ ] Add fallback routing test

### Verification
- [ ] IntentClassifier correctly classifies 10+ sample requests
- [ ] Unknown intent falls back to default handler
- [ ] Policy check blocks unauthorized intents
- [ ] Router agent dispatches to correct workflow
- [ ] Unit tests pass

---

## 8. Phase 6: Idempotency & Compensation

### Gap
Idempotency & Compensation (Playbook §13) — key generator exists, no compensation plans.

### Target

```text
backend/services/execution/compensation/
  __init__.py
  base.py                  # CompensationPlan base class
  order_compensation.py    # Compensate for partial order failures
  position_compensation.py # Compensate for position-related failures
  registry.py              # Map action classes to compensation plans
```

### Tasks
- [ ] Create `backend/services/execution/compensation/` directory
- [ ] Define `CompensationPlan` abstract base class with `execute()`, `validate()`, `log()` methods
- [ ] Implement `OrderCompensationPlan` (offsetting order, cancel pending)
- [ ] Implement `PositionCompensationPlan` (close position, adjust size)
- [ ] Create `CompensationRegistry` mapping action classes (A/B/C/D/E) to compensation plans
- [ ] Enhance `generate_execution_idempotency_key()` to include action class and idempotency metadata
- [ ] Add idempotency check middleware before execution dispatch
- [ ] Add exactly-once vs at-least-once semantics documentation per action class
- [ ] Add unit tests for each compensation plan
- [ ] Add integration test for idempotent retry scenario

### Verification
- [ ] CompensationPlan executes and logs
- [ ] CompensationRegistry returns correct plan for action class
- [ ] Idempotency key is deterministic for same input
- [ ] Duplicate request is detected and blocked
- [ ] Unit tests pass

---

## 9. Phase 7: Context Engineering

### Gap
Context Engineering Standard (Playbook §9.4) — fully missing.

### Target

```text
backend/orchestration/context_engineering/
  __init__.py
  budget.py                # Context budget allocation per workflow
  eviction.py              # Stale context eviction rules
  compression.py           # Summarization/compression rules
  precedence.py            # Source-of-truth precedence
  contradiction.py         # Contradiction resolution rules
  validator.py             # Context inclusion checklist
```

### Tasks
- [ ] Create `backend/orchestration/context_engineering/` directory
- [ ] Implement `ContextBudget` with per-workflow allocation (token budget, context window management)
- [ ] Implement `ContextEviction` with staleness thresholds (TTL, LRU, priority-based)
- [ ] Implement `ContextCompression` with summarization rules (sliding window, abstraction levels)
- [ ] Implement `SourcePrecedence` with trust hierarchy (System Policy > Workflow Policy > Session State > User Input > Resources > Documents > Tool Output)
- [ ] Implement `ContradictionResolver` with conflict detection and resolution strategy
- [ ] Implement `ContextValidator` with inclusion checklist (necessary, fresh, trusted, not duplicated, not too verbose, no conflicts)
- [ ] Wire context engineering into workflow execution pipeline
- [ ] Add unit tests for each component
- [ ] Add integration test for context budget enforcement

### Verification
- [ ] ContextBudget enforces token limits
- [ ] ContextEviction removes stale entries
- [ ] ContextCompression reduces token count while preserving meaning
- [ ] SourcePrecedence resolves conflicts correctly
- [ ] ContradictionResolver detects and resolves contradictions
- [ ] ContextValidator rejects invalid context
- [ ] Unit tests pass

---

## 10. Phase 8: Trace-Level Observability

### Gap
Trace Observability (Playbook §16) — partial, missing model_version, cost, span model.

### Target

```text
backend/observability/
  __init__.py
  trace.py                 # Trace model with full field coverage
  span.py                  # Span model (nested spans for workflow steps)
  redaction.py             # Redaction rules implementation
  cost_tracker.py          # Cost tracking per trace/span
```

### Tasks
- [ ] Create `backend/observability/` directory
- [ ] Implement `Trace` model with all required fields: trace_id, session_id, user_id/tenant_id, request_id, task_id, workflow_id, step_id, tool_call_id, agent_name, prompt_version, model_name, model_version, latency, cost, result_status
- [ ] Implement `Span` model with parent-child relationship, start/end timestamps, attributes, events
- [ ] Implement `RedactionRules` engine with field-level redaction patterns (secrets, PII, credentials)
- [ ] Implement `CostTracker` with per-trace and per-span cost aggregation
- [ ] Enhance `backend/orchestration/workflow/persistence.py` to use Trace and Span models
- [ ] Add `prompt_version`, `model_version`, and `cost` fields to workflow step records
- [ ] Add redaction middleware to all logging pipelines
- [ ] Add unit tests for Trace, Span, Redaction, CostTracker
- [ ] Add integration test for full trace → span → persistence pipeline

### Verification
- [ ] Trace model includes all required fields
- [ ] Span model supports nested hierarchy
- [ ] RedactionRules removes sensitive fields
- [ ] CostTracker aggregates correctly
- [ ] Workflow persistence records prompt_version, model_version, cost
- [ ] Unit tests pass

---

## 11. Phase 9: Evaluation Benchmarks

### Gap
Evaluation Benchmarks (Playbook §15.3, §15.4) — fully missing.

### Target

```text
tests/eval/
  __init__.py
  golden_tasks/            # Known-good inputs and expected outputs
    trade_analysis.json
    risk_assessment.json
    research_query.json
  adversarial_tasks/       # Edge cases, injection attempts, ambiguous inputs
    prompt_injection.json
    ambiguous_request.json
    policy_bypass.json
  regression_tasks/        # Previously-failed cases
  domain_hard_cases/       # Domain-specific hard cases
  benchmarks.py            # Benchmark runner and scoring
  promotion_criteria.yaml  # Criteria for promoting prompts/models/tools
```

### Tasks
- [ ] Create `tests/eval/` directory structure
- [ ] Create 10+ golden tasks with known-good inputs and expected outputs
- [ ] Create 5+ adversarial tasks (prompt injection, policy bypass, ambiguous requests)
- [ ] Create 5+ regression tasks (previously-failed cases)
- [ ] Create 3+ domain hard cases (complex multi-agent scenarios)
- [ ] Implement `BenchmarkRunner` that executes tasks against agents and scores results
- [ ] Create `promotion_criteria.yaml` with criteria for promoting prompts/models/tools (regression pass, benchmark pass, security review, rollback plan, owner sign-off)
- [ ] Define refresh cadence (monthly benchmark runs)
- [ ] Define benchmark owner
- [ ] Add unit tests for benchmark runner
- [ ] Add CI job for benchmark execution

### Verification
- [ ] Golden tasks all pass with expected outputs
- [ ] Adversarial tasks are detected and flagged
- [ ] Regression tasks pass
- [ ] Domain hard cases produce acceptable results
- [ ] BenchmarkRunner scores and reports correctly
- [ ] Promotion criteria enforced
- [ ] CI job runs benchmarks

---

## 12. Phase 10: Cost Governance

### Gap
Cost Governance (Playbook §17) — fully missing.

### Target

```text
config/cost/
  routing_policy.yaml      # Model tier routing, max costs, early exit
  cost_tracker_config.yaml # Cost tracking and alerting
backend/services/cost/
  __init__.py
  router.py                # Cost-aware model routing
  budget.py                # Per-workflow and per-request cost budgets
  early_exit.py            # Early exit rules
  fallback.py              # Downgrade behavior and fallback model
  cache.py                 # Caching policy for repeated queries
```

### Tasks
- [ ] Create `config/cost/` directory
- [ ] Create `routing_policy.yaml` with: default model tier per request type, escalation to premium reasoning, max cost per request, max cost per workflow, early exit rules, caching policy, downgrade behavior, fallback model
- [ ] Create `cost_tracker_config.yaml` with alerting thresholds
- [ ] Implement `CostAwareRouter` with model tier selection based on request complexity
- [ ] Implement `CostBudget` with per-workflow and per-request limits
- [ ] Implement `EarlyExitRules` with convergence threshold and step limits
- [ ] Implement `FallbackHandler` with downgrade behavior
- [ ] Implement `QueryCache` for repeated/similar queries
- [ ] Wire cost governance into workflow execution pipeline
- [ ] Add unit tests for each component
- [ ] Add integration test for cost budget enforcement

### Verification
- [ ] CostAwareRouter selects correct model tier
- [ ] CostBudget enforces limits
- [ ] EarlyExitRules stop runaway loops
- [ ] FallbackHandler downgrades gracefully
- [ ] QueryCache reduces redundant calls
- [ ] Unit tests pass

---

## 13. Phase 11: Security Architecture

### Gap
Security Architecture (Playbook §18) — fully missing.

### Target

```text
docs/agentic_ai/
  Security_Architecture.md  # Identity, authn/authz, network boundaries, sandboxing
backend/api/security/
  __init__.py
  identity.py               # Identity model and authn/authz boundaries
  network.py                # Network boundary definitions
  sandbox.py                # Sandboxing requirements
  output_sanitization.py    # Tool output sanitization
```

### Tasks
- [ ] Create `docs/agentic_ai/Security_Architecture.md` with: identity model, authn/authz boundaries, secret management, least privilege model, network boundaries, code execution restrictions, sandboxing requirements, retention and deletion rules
- [ ] Create `backend/api/security/` directory
- [ ] Implement `IdentityModel` with user/service/agent identity types and authentication boundaries
- [ ] Define `NetworkBoundaries` document (internal vs external, trusted vs untrusted)
- [ ] Implement `SandboxPolicy` with code execution restrictions and resource limits
- [ ] Implement `OutputSanitizer` with tool output validation and sanitization rules
- [ ] Add security tests to CI (already have 7, add 3+ more for output sanitization)
- [ ] Add unit tests for security components
- [ ] Add security review checklist to docs

### Verification
- [ ] Security Architecture document covers all required sections
- [ ] IdentityModel validates all identity types
- [ ] Sandboxing requirements documented and enforced
- [ ] OutputSanitizer removes unsafe content
- [ ] Security tests pass in CI
- [ ] Security review checklist complete

---

## 14. Phase 12: Testing Gaps

### Gap
Testing Gaps (Playbook §19) — contract tests and compensation tests missing.

### Target

```text
tests/contracts/
  __init__.py
  test_agent_workflow_contract.py    # Agent ↔ workflow schema compatibility
  test_workflow_mcp_contract.py      # Workflow ↔ MCP schema compatibility
  test_agent_mcp_contract.py         # Agent ↔ MCP schema compatibility
tests/failure/
  __init__.py
  test_timeout_scenarios.py          # Timeout handling
  test_malformed_output.py           # Invalid agent outputs
  test_unavailable_server.py         # MCP server unavailable
  test_stale_context.py              # Stale context handling
  test_invalid_args.py               # Invalid tool arguments
  test_compensation_partial.py       # Partial side effects, idempotent retries
  test_compensation_rollback.py      # Rollback behavior
```

### Tasks
- [ ] Create `tests/contracts/` directory
- [ ] Create contract tests for all agent ↔ workflow schema boundaries
- [ ] Create contract tests for all workflow ↔ MCP schema boundaries
- [ ] Create contract tests for all agent ↔ MCP schema boundaries
- [ ] Create `tests/failure/` directory
- [ ] Create failure tests for: timeout, malformed output, unavailable server, stale context, invalid args
- [ ] Create compensation tests for: partial side effects, idempotent retries, rollback behavior
- [ ] Add all new tests to CI test suite
- [ ] Add failure-path tests for every high-risk workflow

### Verification
- [ ] All contract tests pass
- [ ] All failure-path tests pass
- [ ] All compensation tests pass
- [ ] CI runs all new tests

---

## 15. Phase 13: Companion Documents

### Gap
Companion Documents (Playbook §30) — all 10 missing.

### Target

```text
docs/agentic_ai/
  SRS.md                              # Software Requirements Specification
  Design.md                           # System Design Specification
  Agent_Catalog.md                    # Agent catalog (purpose, schemas, tools, benchmarks, failure modes)
  Workflow_Catalog.md                 # Workflow catalog (patterns, agents, tools, policies, compensation)
  Tool_Resource_Prompt_Catalog.md     # MCP tool/resource/prompt inventory
  Policy_Map.md                       # Policy enforcement map (from Phase 1)
  Approval_and_Escalation_Standard.md # Approval packet standard (from Phase 2)
  Observability_and_Audit_Spec.md     # Observability and audit specification (from Phase 8)
  Operations_Runbook.md               # Operations runbook (Phase 15 overlap)
  ADR_Index.md                        # Architecture Decision Records index
```

### Tasks
- [ ] Create `SRS.md` with functional and non-functional requirements
- [ ] Create `Design.md` with system architecture, component interactions, data flow
- [ ] Create `Agent_Catalog.md` documenting all 16+ agents with: purpose, input/output schema, persona, model, tools/resources/prompts, memory usage, state transitions, policy profile, approval profile, owner, benchmark tasks, failure modes
- [ ] Create `Workflow_Catalog.md` documenting all workflows with: goal, trigger, input/output schema, pattern, agents involved, tools/resources/prompts, policy checks, approval checks, compensation design, observability requirements, evaluation metrics, owner, failure modes
- [ ] Create `Tool_Resource_Prompt_Catalog.md` with inventory of all MCP capabilities
- [ ] Create `Policy_Map.md` from Phase 1 policy files
- [ ] Create `Approval_and_Escalation_Standard.md` from Phase 2 work
- [ ] Create `Observability_and_Audit_Spec.md` from Phase 8 work
- [ ] Create `Operations_Runbook.md` (overlaps with Phase 15)
- [ ] Create `ADR_Index.md` with template and existing decisions

### Verification
- [ ] All 10 documents exist with required sections
- [ ] Agent_Catalog.md documents all agents
- [ ] Workflow_Catalog.md documents all workflows
- [ ] Documents reference each other correctly

---

## 16. Phase 14: Ownership Assignments

### Gap
Ownership & Operating Model (Playbook §23) — fully missing.

### Target

```text
config/ownership/
  component_owners.yaml     # Product, technical, operational, on-call owner per component
  change_control.yaml       # ADR, benchmark, migration, security review requirements
  decommissioning.yaml      # Criteria for retiring prompts, models, workflows, servers
```

### Tasks
- [ ] Create `config/ownership/` directory
- [ ] Create `component_owners.yaml` assigning product owner, technical owner, operational owner, on-call owner per: agent, workflow, MCP server, service, policy
- [ ] Create `change_control.yaml` with: ADR requirement, benchmark results requirement, migration notes requirement, security review requirement, rollback plan requirement, owner sign-off requirement
- [ ] Create `decommissioning.yaml` with criteria for retiring: old prompts, old models, old workflows, old servers, deprecated schemas
- [ ] Create ownership validation script that checks all components have owners
- [ ] Add ownership field to agent catalog and workflow catalog

### Verification
- [ ] All components have assigned owners
- [ ] Change control requirements documented
- [ ] Decommissioning criteria documented
- [ ] Validation script passes

---

## 17. Phase 15: Incident Response

### Gap
Incident Response (Playbook §24) — fully missing.

### Target

```text
docs/agentic_ai/
  runbooks/
    incident_response.md         # Incident classes (Sev 1-4), response checklist
    postmortem_template.md       # Postmortem template
    kill_switch_runbook.md       # Kill switch activation and recovery
    stale_risk_runbook.md        # Stale risk decision response
    failed_workflow_runbook.md   # Failed workflow investigation
    mcp_server_down_runbook.md   # MCP server outage response
backend/services/monitoring/incident_response.py  # Automated incident detection and escalation
```

### Tasks
- [ ] Create `docs/agentic_ai/runbooks/` directory
- [ ] Create `incident_response.md` with: Sev 1-4 classification, response checklist (contain impact, trigger kill switch, preserve logs, identify affected workflows, compensate side effects, notify stakeholders, patch and validate, run postmortem)
- [ ] Create `postmortem_template.md` with: summary, impact, timeline, root cause, contributing factors, policy/control gaps, what worked, what failed, corrective actions, owner and due date
- [ ] Create `kill_switch_runbook.md` with activation procedure, scope (global vs domain), drain vs hard-stop, recovery procedure, post-incident checks
- [ ] Create `stale_risk_runbook.md` with investigation steps and resolution
- [ ] Create `failed_workflow_runbook.md` with log inspection, state inspection, compensation verification, retry procedure
- [ ] Create `mcp_server_down_runbook.md` with detection, fallback activation, recovery verification
- [ ] Create `backend/services/monitoring/incident_response.py` with automated incident detection, severity classification, and escalation routing
- [ ] Wire incident detection into monitoring service
- [ ] Add unit tests for incident detection logic
- [ ] Add integration test for incident escalation

### Verification
- [ ] All runbooks exist with required sections
- [ ] Postmortem template covers all sections
- [ ] Incident detection classifies severity correctly
- [ ] Incident escalation routes to correct owner
- [ ] Unit tests pass
- [ ] Integration test passes

---

## 18. Cross-Cutting Concerns

### 18.1 Testing Strategy

Every phase must include:
- Unit tests for new code
- Integration tests for new workflows
- Contract tests for new schema boundaries
- Failure-path tests for new failure modes

### 18.2 CI/CD Integration

- Add benchmark job to CI (Phase 9)
- Add security test suite to CI (Phase 11)
- Add contract test suite to CI (Phase 12)
- Add failure-path test suite to CI (Phase 12)
- Add cost tracking to CI runs (Phase 10)

### 18.3 Documentation Updates

- Update `Agentic_AI_Playbook.md` with implementation status
- Update `README.md` with new component locations
- Update `docs/haruquant/architecture.md` with new architecture

---

## 19. Phase Dependencies

```
Phase 1:  Policy Map              (no dependencies)
Phase 2:  Approval Packet         (depends on Phase 1)
Phase 3:  MCP metadata.yaml       (no dependencies)
Phase 4:  MCP Wrapper Standards   (depends on Phase 3)
Phase 5:  Routing / Intent Class  (no dependencies)
Phase 6:  Idempotency & Comp      (depends on Phase 1, Phase 2)
Phase 7:  Context Engineering     (no dependencies)
Phase 8:  Trace Observability     (no dependencies)
Phase 9:  Evaluation Benchmarks   (depends on Phase 7)
Phase 10: Cost Governance         (depends on Phase 8)
Phase 11: Security Architecture   (no dependencies)
Phase 12: Testing Gaps            (depends on Phases 1–11)
Phase 13: Companion Documents     (depends on all code phases)
Phase 14: Ownership Assignments   (depends on Phase 13)
Phase 15: Incident Response       (no dependencies)
```

---

## 20. Success Criteria

All phases complete when:
1. All 15 phases marked done with verification
2. All new tests pass in CI
3. All companion documents exist with required sections
4. All components have assigned owners
5. All MCP servers have metadata.yaml
6. All workflows have approval packets
7. All policies are enforced
8. All traces include full field coverage
9. All benchmarks pass
10. All runbooks tested
11. Zero gaps remain between Playbook and codebase
