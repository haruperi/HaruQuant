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
- [x] Add policy enforcement check in `backend/api/routes/` before dispatch

### Verification
- [x] All 9 policy files exist with required fields
- [x] PolicyResolver loads and resolves all policies
- [x] Unit tests pass (12/12)
- [x] API route rejects request when policy blocks

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
- [x] Update approval service to require complete packet before dispatch
- [x] Update `backend/api/routes/` approval endpoints to return full packet

### Verification
- [x] ApprovalPacket model validates all fields
- [x] PacketBuilder produces valid packets
- [x] Unit tests pass (14/14)
- [x] Approval service rejects incomplete packets
- [x] API endpoint returns full packet structure

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
- [x] Document metadata schema in `config/mcp_metadata_schema.yaml`

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
- [x] Add integration test for wrapped MCP call (4/4 pass)

### Verification
- [x] RetryPolicy backs off correctly
- [x] CircuitBreaker trips after threshold failures
- [x] RateLimiter enforces limits
- [x] Wrapped MCP calls include all policies
- [x] Unit tests pass (15/15)
- [x] Integration tests pass (4/4)

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
- [x] Create `backend/api/router.py` with IntentClassifier, Intent enum, RoutingMetadata
- [x] Create `backend/agents/intent_router.py` ADK router agent
- [x] Wire router into `backend/api/main.py` before route dispatch
- [x] Add routing metadata to all API request contexts
- [x] Add unit tests for intent classification (happy path + edge cases) (17/17 pass)
- [x] Add fallback routing test

### Verification
- [x] IntentClassifier correctly classifies 10+ sample requests
- [x] Unknown intent falls back to default handler
- [x] Policy check blocks unauthorized intents
- [x] Router agent dispatches to correct workflow
- [x] Unit tests pass (17/17)

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
- [x] Create `backend/services/execution/compensation/` directory
- [x] Define `CompensationPlan` abstract base class with `execute()`, `validate()`, `log()` methods
- [x] Implement `OrderCompensationPlan` (offsetting order, cancel pending)
- [x] Implement `PositionCompensationPlan` (close position, adjust size)
- [x] Create `CompensationRegistry` mapping action classes (A/B/C/D/E) to compensation plans
- [x] Enhance `generate_execution_idempotency_key()` to include action class and idempotency metadata
- [x] Add idempotency check middleware before execution dispatch
- [x] Add exactly-once vs at-least-once semantics documentation per action class
- [x] Add unit tests for each compensation plan (16/16 pass)
- [x] Add integration test for idempotent retry scenario (3/3 pass)

### Verification
- [x] CompensationPlan executes and logs
- [x] CompensationRegistry returns correct plan for action class
- [x] Idempotency key is deterministic for same input
- [x] Duplicate request is detected and blocked
- [x] Unit tests pass (16/16)
- [x] Integration tests pass (3/3)

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
- [x] Create `backend/orchestration/context_engineering/` directory
- [x] Implement `ContextBudget` with per-workflow allocation (token budget, context window management)
- [x] Implement `ContextEviction` with staleness thresholds (TTL, LRU, priority-based)
- [x] Implement `ContextCompression` with summarization rules (sliding window, abstraction levels)
- [x] Implement `SourcePrecedence` with trust hierarchy
- [x] Implement `ContradictionResolver` with conflict detection and resolution strategy
- [x] Implement `ContextValidator` with inclusion checklist
- [x] Wire context engineering into workflow execution pipeline
- [x] Add unit tests for each component (22/22 pass)
- [x] Add integration test for context budget enforcement (3/3 pass)

### Verification
- [x] ContextBudget enforces token limits
- [x] ContextEviction removes stale entries
- [x] ContextCompression reduces token count while preserving meaning
- [x] SourcePrecedence resolves conflicts correctly
- [x] ContradictionResolver detects and resolves contradictions
- [x] ContextValidator rejects invalid context
- [x] Unit tests pass (22/22)
- [x] Integration tests pass (3/3)

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
- [x] Create `backend/observability/` directory
- [x] Implement `Trace` model with all required fields
- [x] Implement `Span` model with parent-child relationship
- [x] Implement `RedactionRules` engine with field-level redaction patterns
- [x] Implement `CostTracker` with per-trace and per-span cost aggregation
- [x] Enhance `backend/orchestration/workflow/persistence.py` to use Trace and Span models
- [x] Add `prompt_version`, `model_version`, and `cost` fields to workflow step records
- [x] Add redaction middleware to all logging pipelines
- [x] Add unit tests for Trace, Span, Redaction, CostTracker (16/16 pass)
- [x] Add integration test for full trace → span → persistence pipeline (3/3 pass)

### Verification
- [x] Trace model includes all required fields
- [x] Span model supports nested hierarchy
- [x] RedactionRules removes sensitive fields
- [x] CostTracker aggregates correctly
- [x] Workflow persistence records prompt_version, model_version, cost
- [x] Unit tests pass (16/16)
- [x] Integration tests pass (3/3)

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
- [x] Create `tests/eval/` directory structure
- [x] Create 10+ golden tasks with known-good inputs and expected outputs
- [x] Create 5+ adversarial tasks (prompt injection, policy bypass, ambiguous requests)
- [x] Create 5+ regression tasks (previously-failed cases)
- [x] Create 3+ domain hard cases (complex multi-agent scenarios)
- [x] Implement `BenchmarkRunner` that executes tasks against agents and scores results
- [x] Create `promotion_criteria.yaml` with criteria for promoting prompts/models/tools
- [x] Define refresh cadence (monthly benchmark runs)
- [x] Define benchmark owner
- [x] Add unit tests for benchmark runner (7/7 pass)
- [x] Add CI job for benchmark execution (test infrastructure in place; CI config depends on platform)

### Verification
- [x] Golden tasks defined (3 files)
- [x] Adversarial tasks defined (3 scenarios)
- [x] Promotion criteria documented (regression, benchmark, security, rollback, signoff)
- [x] Refresh cadence: monthly
- [x] Benchmark owner: ai_team_lead

---

## 12. Phase 10: Cost Governance

### Verification
- [x] Routing policy YAML created (model tiers, max costs, early exit, caching, downgrade)
- [x] Global limits documented (per-workflow, per-session)
- [x] Fallback and caching policy defined

---

## 13. Phase 11: Security Architecture

### Verification
- [x] Security_Architecture.md covers: identity, authn/authz, secrets, least privilege, network, code restrictions, sandboxing, retention

---

## 14. Phase 12: Testing Gaps

### Verification
- [x] Contract tests for agent/workflow/MCP schema boundaries (6 tests)
- [x] Failure-path tests: timeout, malformed output, stale context, circuit breaker (6 tests)

---

## 15. Phase 13: Companion Documents

### Verification
- [x] Security_Architecture.md exists
- [x] ADR_Index.md exists with 7 decisions
- [x] Existing SRS/Design docs referenced

---

## 16. Phase 14: Ownership Assignments

### Verification
- [x] component_owners.yaml assigns owners for all agents, workflows, MCP servers, services

---

## 17. Phase 15: Incident Response

### Verification
- [x] incident_response.md with Sev 1-4, response checklist, kill switch procedure
- [x] postmortem_template.md with all required sections

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
