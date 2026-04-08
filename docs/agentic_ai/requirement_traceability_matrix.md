# Requirement Traceability Matrix: HaruQuant Agentic AI System

**Document Version:** 1.0.0  
**Companion To:** `implementation_plan.md`, SRS v3.1.1, Design Specification / System Architecture v1.1.0, Schemas v1.0.0  
**System:** HaruQuant Autonomous Trading Platform  
**Status:** Execution Traceability Matrix

---

## 1. Purpose

This matrix maps the approved requirements to implementation work packages and atomic tasks from `implementation_plan.md`. Its purpose is to let engineering, QA, governance, and audit teams verify that every requirement has a concrete implementation path, test expectation, and delivery location.

---

## 2. How to Use This Matrix

### Status Codes
- `PLANNED` — requirement has mapped implementation tasks
- `PARTIAL` — requirement is only partly covered and needs a follow-up backlog item
- `NEEDS-EXPANSION` — requirement exists but needs more implementation detail before build starts

### Task Reference Format
Task references below point to the matching implementation plan section, for example:
- `P1.6.3` = Phase 1 → Section 6.3 → 3rd atomic task in that section
- `P4.9.2` = Phase 4 → Section 9.2 → 2nd atomic task in that section

For practical execution, use this matrix together with `implementation_plan.md`.

---

## 3. Phase Section Key

- `P0.4.*` = Cross-Cutting Global Backlog
- `P0.5.*` = Phase 0 — Delivery Foundations
- `P1.6.1.*` = Canonical Contracts
- `P1.6.2.*` = Schema Registry
- `P1.6.3.*` = Database Baseline
- `P1.6.4.*` = Repository Layer
- `P1.6.5.*` = Workflow Skeleton
- `P1.6.6.*` = Policy and Approval Skeleton
- `P1.6.7.*` = API and Dashboard Skeleton
- `P2.7.1.*` = Freshness and Snapshot Infrastructure
- `P2.7.2.*` = Risk Engine Core
- `P2.7.3.*` = Kill Switch
- `P2.7.4.*` = Execution Readiness Validator
- `P2.7.5.*` = MT5 MCP Boundary
- `P2.7.6.*` = Reconciliation Engine
- `P3.8.1.*` = ADK Runtime Foundation
- `P3.8.2.*` = Prompt and Version Registry
- `P3.8.3.*` = Core Agents
- `P3.8.4.*` = Optional Sub-Agents
- `P3.8.5.*` = Workflow Patterns
- `P3.8.6.*` = Evaluator Infrastructure
- `P3.8.7.*` = Observability and Trajectory Logs
- `P4.9.1.*` = Proposal Pipeline
- `P4.9.2.*` = Execution Service
- `P4.9.3.*` = Approval Flows
- `P4.9.4.*` = Monitoring and Incident Management
- `P4.9.5.*` = Replay and Audit
- `P4.9.6.*` = Operator Dashboard
- `P5.10.1.*` = Portfolio Analytics Service
- `P5.10.2.*` = Strategy Registry and Lifecycle
- `P5.10.3.*` = Evidence Bundle Automation
- `P6.11.1.*` = Legacy Wrapping
- `P6.11.2.*` = Shadow Mode
- `P6.11.3.*` = Replay Validation
- `P6.11.4.*` = Chaos and Failure Readiness
- `P6.11.5.*` = Security and Red-Team Hardening
- `P6.11.6.*` = Performance and Capacity
- `P6.11.7.*` = Compliance Rollout
- `P12.*` = End-to-End Scenario Backlog
- `P15.*` = Non-Functional Work Packages

---

## 4. Functional Requirement Traceability

| Requirement | Requirement Summary | Primary Task Mapping | Validation Mapping | Status |
|---|---|---|---|---|
| FR-001 | Active mode scoped by environment/account/strategy/symbol/workflow/user-role | P0.4.6, P1.6.6.3, P2.7.2.14 | config tests, policy resolution tests | PLANNED |
| FR-002 | Every workflow under exactly one active operating mode | P0.4.6, P1.6.5.7, P1.6.6.3 | workflow creation tests | PLANNED |
| FR-003 | Deny or escalate actions not permitted by mode | P1.6.6.3, P2.7.2.14, P12 negative scenario 2 | mode mismatch tests, scenario | PLANNED |
| FR-004 | Workflow may not self-escalate autonomy | P1.6.6.3, P2.7.2.14, P12 negative scenario 2 | scenario + policy tests | PLANNED |
| FR-005 | Every workflow passes Reason→Plan→Act→Observe→Evaluate→Refine/Finish | P1.6.5.2, P1.6.5.6, P3.8.5.1 | FSM tests, ordered phase tests | PLANNED |
| FR-006 | Workflow engine prevents skipped Observe/Evaluate | P1.6.5.6 | phase skipping rejection tests | PLANNED |
| FR-007 | Emergency-exit can act before evaluate only by policy | P1.6.6.3, P2.7.3.*, P6.11.4.* | chaos/scenario tests | PLANNED |
| FR-008 | Workflow FSM minimum states | P1.6.3.3, P1.6.5.1 to P1.6.5.6 | enum + transition tests | PLANNED |
| FR-009 | Workflow engine validates all state transitions | P1.6.5.6, P1.6.5.8 | transition tests | PLANNED |
| FR-010 | Trade proposal FSM minimum states | P1.6.3.5, P1.6.5.3, P4.9.1.3 | proposal state tests | PLANNED |
| FR-011 | Incident FSM minimum states | P1.6.5.4, P4.9.4.3 | incident FSM tests | PLANNED |
| FR-012 | Kill-switch FSM minimum states | P1.6.5.5, P2.7.3.1 | kill-switch transition tests | PLANNED |
| FR-013 | Kill-switch recovery requires authorized action | P1.6.5.5, P2.7.3.3, P4.9.3.4 | dual-auth recovery tests | PLANNED |
| FR-014 | Workflows triggered by user/schedule/market/internal event | P1.6.5.7, P6.11.2.2, P12 core scenarios | workflow creation + scenario tests | PLANNED |
| FR-015 | Workflow declares objective, constraints, tools, agents, stop conditions, timeout, criteria, mode | P1.6.1.1-2, P1.6.5.7-9, P4.9.4.6 | workflow creation tests | PLANNED |
| FR-016 | Support symbol-level and portfolio-level workflows | P1.6.5.7, P5.10.1.* | workflow + portfolio tests | PLANNED |
| FR-017 | Same logical workflow supports simulation/paper/advisory/live | P6.11.2.*, P12 core scenarios | multi-mode scenario tests | PLANNED |
| FR-018 | Specialist agents not monolithic agent | P3.8.3.*, P3.8.5.* | agent runtime integration tests | PLANNED |
| FR-019 | Minimum agent set required | P3.8.3.1-8 | per-agent contract tests | PLANNED |
| FR-020 | Optional sub-agents allowed | P3.8.4.* | sub-agent output tests | PLANNED |
| FR-021 | Agents communicate through versioned schema-validated contracts | P1.6.1.*, P1.6.2.*, P3.8.1.6 | contract validation tests | PLANNED |
| FR-022 | Agents use only approved tool interfaces | P2.7.5.*, P3.8.1.4, P12 negative scenario 6 | allowlist + auth tests | PLANNED |
| FR-023 | Agents independently testable in isolation and integrated workflows | P0.4.4, P3.8.3.*, P14 test matrix | unit/integration layering | PLANNED |
| FR-024 | Support sequential/routing/parallel/evaluator-optimizer/orchestrator-worker | P3.8.5.1-6 | workflow pattern tests | PLANNED |
| FR-025 | Define canonical message families | P1.6.1.1-16 | schema validation tests | PLANNED |
| FR-026 | Every canonical contract includes required metadata | P1.6.1.2, P0.4.5 | envelope validation tests | PLANNED |
| FR-027 | Breaking changes require version increments and compatibility handling | P1.6.2.* | schema registry version tests | PLANNED |
| FR-028 | Every live action requires current RiskGovernor decision | P2.7.2.*, P2.7.4.7, P4.9.2.1 | risk gating tests | PLANNED |
| FR-029 | Risk decision invalid on expiry/material change/invalidation | P2.7.2.18-19, P2.7.4.7 | expiry/invalidation tests | PLANNED |
| FR-030 | Missing/stale/malformed/non-reproducible risk eval denies new live entry | P2.7.2.19, P2.7.4.7-8, P12 negative scenario 1 | rejection tests | PLANNED |
| FR-031 | RiskGovernor evaluates full required metric set | P2.7.1.*, P2.7.2.2-15 | unit tests by metric dimension | PLANNED |
| FR-032 | RiskGovernor returns APPROVE / APPROVE_WITH_LIMITS / REJECT / FORCE_EXIT | P1.6.1.8, P2.7.2.16 | decision matrix tests | PLANNED |
| FR-033 | APPROVE_WITH_LIMITS includes machine-enforceable constraints | P1.6.1.8, P1.6.3.8, P2.7.2.16-17 | constraint persistence tests | PLANNED |
| FR-034 | Persist rationale, metrics snapshot, policy version, provenance | P2.7.2.17, P1.6.3.7, P4.9.5.* | persistence + replay tests | PLANNED |
| FR-035 | Explicit supervisory roles and permissions | P1.6.6.*, P1.6.7.2, P6.11.5.1 | RBAC and endpoint auth tests | PLANNED |
| FR-036 | Risk gating not bypassable by workflow logic or self-modification | P2.7.2.*, P3.8.3.8, P15.15.1 | hard-gate verification tests | PLANNED |
| FR-037 | Overrides require role, reason, rationale, expiry, audit, dual auth on REJECT bypass | P1.6.6.6-7, P4.9.3.3 | override tests | PLANNED |
| FR-038 | Distinguish workflow-init approval, policy change, live execution approval, override | P1.6.6.4-7, P4.9.3.1-4 | approval flow tests | PLANNED |
| FR-039 | StrategyAgent generates hypotheses not broker orders | P3.8.3.2, P12 negative scenario 5 | hypothesis schema tests | PLANNED |
| FR-040 | Trade hypothesis includes full required fields | P1.6.1.5, P3.8.3.2, P4.9.1.1 | schema tests | PLANNED |
| FR-041 | Hypotheses become proposals only via canonical transformation | P1.6.1.6, P4.9.1.1 | transform validity tests | PLANNED |
| FR-042 | Support multiple strategy families | P1.6.3.4, P3.8.3.2, P5.10.2.* | strategy registry tests | PLANNED |
| FR-043 | Compare multiple candidate actions before final proposal | P3.8.3.2, P3.8.5.5, P4.9.1.1 | orchestrator-worker / proposal tests | PLANNED |
| FR-044 | Strategy lifecycle states | P1.6.3 governance tables, P5.10.2.1-2,7-8 | lifecycle tests | PLANNED |
| FR-045 | Promotion requires defined evidence and approval gates | P5.10.2.3-4, P5.10.3.* | promotion gate tests | PLANNED |
| FR-046 | Persist promotion rationale/evidence/approver/effective date | P1.6.3 governance migrations, P5.10.2.5 | promotion persistence tests | PLANNED |
| FR-047 | Autonomous live only for allowed lifecycle + mode + policy | P5.10.2.6, P1.6.6.3, P12 core scenario 5 | envelope tests | PLANNED |
| FR-048 | Portfolio-level analysis/optimization inspects positions/orders/exposure/marginal risk | P5.10.1.1-8 | portfolio analytics tests | PLANNED |
| FR-049 | Portfolio workflows propose resize/rebalance/hedge/de-risk | P5.10.1.3-6 | proposal generator tests | PLANNED |
| FR-050 | Portfolio optimization advisory by default; live requires gating | P5.10.1.9, P4.9.2.*, P2.7.2.* | advisory-only enforcement tests | PLANNED |
| FR-051 | Portfolio proposals include projected VaR/ES, margin, concentration, outcomes | P5.10.1.7-8 plus portfolio modeling | projected impact tests | PARTIAL |
| FR-052 | Research workflows support grounded retrieval from approved sources | P3.8.3.3, P6.11.1.*, P6.11.5.4-5 | retrieval + security tests | PLANNED |
| FR-053 | Research outputs include evidence refs, freshness, assumptions, limitations | P3.8.3.3, P3.8.6.3, P5.10.3.1 | output tests | PLANNED |
| FR-054 | Research agents cannot place orders or modify broker state | P3.8.1.4, P12 negative scenario 5 | forbidden tool tests | PLANNED |
| FR-055 | Low-confidence research workflows support refinement loops | P3.8.5.4-6, P3.8.6.4 | refine-loop tests | PLANNED |
| FR-056 | ExecutionAgent translates approved intents into broker-specific instructions | P3.8.3.7, P4.9.2.1-4 | intent translation tests | PLANNED |
| FR-057 | Pre-submit execution validation of all required dimensions | P2.7.4.1-8 | readiness validator tests | PLANNED |
| FR-058 | Support market/pending/SLTP modify/partial/full close/cancel | P2.7.5.3, P4.9.2.8 | action-type handler tests | PLANNED |
| FR-059 | Every live execution produces receipt, normalized record, idempotency key, linkage | P1.6.3 execution tables, P4.9.2.2,5,6 | persistence tests | PLANNED |
| FR-060 | Post-send reconciliation before duplicate retries | P2.7.6.*, P12 negative scenario 4 | reconciliation tests | PLANNED |
| FR-061 | Observe broker responses, position changes, margin, latency, tool health, schema failures, transitions | P4.9.4.1,4,5, P3.8.7.* | observation + monitoring tests | PLANNED |
| FR-062 | MonitoringAgent emits minimum alert classes | P3.8.3.4, P4.9.4.2 | classification tests | PLANNED |
| FR-063 | All observations timestamped, attributable, correlated | P0.4.2, P1.6.1.10, P3.8.7.2 | correlation tests | PLANNED |
| FR-064 | Dashboard shows real-time/near-real-time workflows, positions, proposals, risk, incidents, alerts, evaluations | P1.6.7.*, P4.9.6.*, P4.9.4.* | UI and streaming tests | PLANNED |
| FR-065 | Operators inspect workflow phases and inputs/outputs/rationale | P4.9.6.1-5 | UI detail tests | PLANNED |
| FR-066 | Operators configure mode/allowlists/limits/windows/routing/kill-switch subject to policy/role | P1.6.7.*, P4.9.3.*, P4.9.6.*, P6.11.5.1 | auth/UI tests | PARTIAL |
| FR-067 | Dashboard displays authoritative/provisional/reconciling state | P4.9.2.7, P4.9.6.7 | state badge tests | PLANNED |
| FR-068 | Distinguish session/workflow/long-term/cached/replay memory | P3.8.1.2-3, P4.9.5.*, P6.11.1.* | memory isolation tests | PLANNED |
| FR-069 | Live decisions cannot depend on ungrounded memory without structured validation | P2.7.4.*, P3.8.6.3, P6.11.5.5 | validation + security tests | PLANNED |
| FR-070 | Execution-critical inputs declare freshness policies; fail closed on violation | P0.4.4, P2.7.1.*, P2.7.4.3 | TTL tests | PLANNED |
| FR-071 | Replay artifacts immutable and not modified by later memory updates | P4.9.5.*, P6.11.3.* | replay immutability tests | PLANNED |
| FR-072 | Persist minimum required decision/execution/workflow/trajectory/eval/override/promotion/replay artifacts | P1.6.3.*, P3.8.7.*, P4.9.5.*, P5.10.3.* | persistence + replay tests | PLANNED |
| FR-073 | Every execution-bound decision records full provenance bundle | P2.7.2.17, P3.8.2.3, P3.8.7.3-5, P4.9.5.1 | provenance completeness tests | PLANNED |
| FR-074 | Retention configurable by profile; legal hold blocks purge | P4.9.5.3-4, P6.11.7.4-5 | legal-hold tests | PLANNED |
| FR-075 | Execution-critical failures fail closed for new entries and reconcile before retry | P2.7.6.4, P12 negative scenario 4 | scenario/chaos tests | PLANNED |
| FR-076 | Deterministic handling for stale data/timeouts/restarts/schema errors/conflicts | P6.11.4.*, P2.7.6.*, P1.6.2.4 | chaos + contract tests | PLANNED |
| FR-077 | On restart reconcile all in-flight intents before new live execution | P2.7.6.1-5, P6.11.4.5 | restart scenario tests | PLANNED |
| FR-078 | Emergency-exit policy for forced liquidation/reduction audited and reconciled | P2.7.3.*, P2.7.6.*, P4.9.5.* | emergency scenario tests | PLANNED |

---

## 5. Non-Functional Requirement Traceability

| Requirement | Requirement Summary | Primary Task Mapping | Validation Mapping | Status |
|---|---|---|---|---|
| NFR-001 | Global kill switch blocks new live execution, may force exit by policy | P2.7.3.*, P15.15.1 | kill-switch tests | PLANNED |
| NFR-002 | Fail closed on uncertainty/timeout/schema failure/stale validation unless emergency exit | P1.6.2.4, P2.7.4.*, P2.7.6.*, P6.11.4.* | chaos + readiness tests | PLANNED |
| NFR-003 | RiskGovernor and ExecutionAgent authority boundaries technically enforced | P2.7.5.6, P3.8.1.4, P3.8.3.8, P15.15.1 | allowlist + boundary tests | PLANNED |
| NFR-004 | Complete trajectory logging for production workflows | P0.4.2-3, P3.8.7.*, P15.15.2 | telemetry completeness tests | PLANNED |
| NFR-005 | Real-time/near-real-time operator visibility and alerting | P0.4.3, P4.9.4.*, P4.9.6.6 | live event tests | PLANNED |
| NFR-006 | Performance budgets across workflow/risk/execution/control plane | P6.11.6.*, P15.15.3 | perf benchmarks | PLANNED |
| NFR-007 | UI responsiveness/query efficiency | P6.11.6.4, P4.9.6.* | UI perf smoke tests | PLANNED |
| NFR-008 | Scalable event-driven design for workflow and observations | P0.5.1 ADR, P0.4.3, P4.9.4.1 | architecture + integration | NEEDS-EXPANSION |
| NFR-009 | Horizontal scalability for stateless control services | P0.4.6, P6.11.6.2 | deployment/perf tests | PARTIAL |
| NFR-010 | Maintainable modular codebase and clean delivery pipeline | P0.4.1-7, P0.5.2.* | CI/lint/type tests | PLANNED |
| NFR-011 | Strong automated testing posture | P0.5.2.2, P14, P12, P6.11.4-6 | full test matrix | PLANNED |
| NFR-012 | State transitions and control rules deterministic and testable | P1.6.5.*, P2.7.3.* | FSM tests | PLANNED |
| NFR-013 | Reliability and recovery of execution-critical flows | P2.7.6.*, P6.11.4.* | restart/recon tests | PLANNED |
| NFR-014 | Safe degradation modes | P2.7.6.*, P4.9.4.*, P6.11.4.* | chaos tests | PLANNED |
| NFR-015 | Secure authz/authn/service authorization | P1.6.7.2, P2.7.5.6, P6.11.5.1-2 | security tests | PLANNED |
| NFR-016 | Secret isolation and rotation; secrets excluded from model/UI context | P3.8.1.5, P6.11.5.3, P15.15.4 | secret isolation tests | PLANNED |
| NFR-017 | Defend against prompt injection / retrieval contamination | P6.11.5.4-5 | red-team tests | PLANNED |
| NFR-018 | Traceable engineering process and testability | P0.5.2.*, P0.4.5 | process checks | PLANNED |
| NFR-019 | Audit integrity / tamper evidence | P4.9.5.2,5, P6.11.5.6 | integrity verification tests | PLANNED |
| NFR-020 | Replayability / reproducibility / immutable manifests | P4.9.5.*, P6.11.3.*, P15.15.5 | replay tests | PLANNED |

---

## 6. Invariant Traceability

| Invariant | Summary | Primary Task Mapping | Validation Mapping | Status |
|---|---|---|---|---|
| INV-001 | No live execution without valid risk decision | P2.7.2.*, P2.7.4.7, P4.9.2.1 | risk gate tests | PLANNED |
| INV-002 | No external side effects except through approved MCP interfaces | P2.7.5.*, P3.8.1.4, P6.11.1.* | forbidden tool tests | PLANNED |
| INV-003 | All inter-agent messages schema-validated | P1.6.1.*, P1.6.2.*, P3.8.1.6 | contract tests | PLANNED |
| INV-004 | Execution-bound decisions attributable to workflow/policy/provenance | P2.7.2.17, P3.8.7.*, P4.9.5.1 | provenance tests | PLANNED |
| INV-005 | Execution-critical uncertainty fails closed unless emergency-exit policy | P2.7.4.*, P6.11.4.* | chaos tests | PLANNED |
| INV-006 | Research not treated as execution instructions unless transformed and gated | P4.9.1.1-3, P12 negative scenario 5 | scenario tests | PLANNED |
| INV-010 | Deterministic compute distinct from LLM reasoning | P2.7.2.*, P3.8.3.8 | architectural boundary tests | PLANNED |
| INV-011 | Research and execution roles remain distinct | P3.8.3.3,7, P12 negative scenario 5 | role isolation tests | PLANNED |
| INV-012 | Policy definition distinct from policy enforcement | P1.6.6.*, P2.7.2.14-15 | policy resolution vs enforcement tests | PLANNED |
| INV-013 | Human supervisory action distinct from silent bypass | P1.6.6.*, P4.9.3.* | approval/override audit tests | PLANNED |
| INV-014 | Replay/audit storage distinct from mutable operational state | P1.6.3 audit tables, P4.9.5.*, P6.11.3.* | replay immutability tests | PLANNED |
| INV-020 | LLMs not authoritative for deterministic or live authoritative data | P2.7.1.*, P2.7.4.*, P3.8.1.5, P3.8.6.3 | validation tests | PLANNED |
| INV-021 | LLMs not authoritative for live prices/balances/execution state/regulatory obligations without grounding | P2.7.1.*, P2.7.5.1-2, P6.11.5.4-5 | grounding/security tests | PLANNED |

---

## 7. Compliance / Promotion / TTL Coverage

### 7.1 Compliance Requirements
The implementation plan already references compliance tasks, but the key mapping is:

| Group | Primary Coverage |
|---|---|
| compliance profiles | P1.6.6.2, P4.9.5.3, P6.11.7.* |
| dual authorization | P1.6.6.5, P2.7.3.3, P4.9.3.* |
| legal hold / retention | P4.9.5.4, P6.11.7.5 |
| export labeling | P4.9.5.3, P6.11.7.4 |
| live workflow profile attachment | P2.7.2.15, P6.11.7.3 |

### 7.2 Promotion Requirements
| Group | Primary Coverage |
|---|---|
| lifecycle registry | P5.10.2.1-2 |
| evidence validation | P5.10.2.3, P5.10.3.* |
| approval routing | P5.10.2.4 |
| promotion persistence | P5.10.2.5 |
| live envelope update | P5.10.2.6 |
| suspension / retirement | P5.10.2.7-8 |

### 7.3 TTL / Freshness Requirements
| Group | Primary Coverage |
|---|---|
| shared TTL utilities | P0.4.4 |
| market/account/portfolio freshness | P2.7.1.1-5 |
| risk decision invalidation/expiry | P2.7.2.18-19 |
| execution freshness checks | P2.7.4.3,7 |
| stale-state monitoring | P4.9.4.4 |
| stale-data chaos tests | P6.11.4.1-2 |

---

## 8. Identified Gaps Requiring Small Additions

These are not blockers, but they would improve completeness:

### Gap A — FR-051 projected distribution of outcomes
Current plan covers projected VaR/ES and margin, but “projected distribution of outcomes” should be explicit.
**Add task:**
- [ ] Implement projected outcome distribution simulator for portfolio proposals.  
  **Refs:** FR-051  
  **Commit:** `feat(portfolio): add projected outcome distribution simulator`

### Gap B — FR-066 operator configuration write paths
Current plan covers dashboard screens and policy/approval scaffolding, but explicit operator endpoints/UI flows for allowlists, session windows, approval routing, and risk limits should be listed separately.
**Add tasks:**
- [ ] Implement operator API endpoints for risk limits and symbol/strategy allowlists.  
  **Refs:** FR-066  
  **Commit:** `feat(api): add operator configuration endpoints for limits and allowlists`

- [ ] Implement operator UI forms for session windows, approval routing, and kill-switch controls.  
  **Refs:** FR-066  
  **Commit:** `feat(ui): add governance configuration forms`

### Gap C — NFR-008/NFR-009 infrastructure scaling detail
The plan implies scalable architecture but could add explicit infra work.
**Add tasks:**
- [ ] Implement queue/backpressure strategy for high-volume observation and transition events.  
  **Refs:** NFR-008  
  **Commit:** `feat(infra): add backpressure strategy for workflow event streams`

- [ ] Implement stateless service deployment templates with horizontal scaling policy.  
  **Refs:** NFR-009  
  **Commit:** `feat(infra): add scalable deployment templates for stateless services`

---

## 9. Recommended Next Action

Before coding starts, update `implementation_plan.md` with the four gap-closure tasks in Section 8, then freeze:
1. Phase 1 scope
2. Phase 2 scope
3. test conventions
4. requirement traceability policy for PRs

That will make the plan more audit-ready and reduce drift later.

---

## 10. Approval Checklist for This Matrix

- [ ] Engineering Lead reviewed mappings
- [ ] QA Lead confirmed test coverage mapping
- [ ] Risk Lead confirmed FR-028 to FR-034 coverage
- [ ] Compliance Lead confirmed retention/export/approval mappings
- [ ] Architecture Lead approved gap list and additions
