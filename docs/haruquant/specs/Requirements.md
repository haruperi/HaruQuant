# Software Requirements Specification: HaruQuant Agentic AI System

Status: canonical requirements spec
Scope: system requirements and execution law
Use this when: you need normative requirements, scope, and system obligations
Companion docs: `System_Architecture.md`, `Security.md`, `Observability_Audit.md`
Owner: product and platform architecture
Review cadence: quarterly or when requirements change

**Document Version:** 3.1.1 (Board Approval Version)  
**System:** HaruQuant Autonomous Trading Platform  
**Framework Target:** Google Agent Development Kit (ADK) v2.0+  
**Protocol Target:** Model Context Protocol (MCP) v2025-06-18 or later  
**Classification:** Internal Use - Proprietary  
**Status:** Board Approval Version

---

## 1. Purpose

This Software Requirements Specification defines the requirements for evolving HaruQuant from a conventional trading platform into a production-grade, agentic trading system built around bounded autonomy, strict risk governance, reproducible decision-making, and auditable execution.

The system shall preserve HaruQuant’s existing strengths in backtesting, portfolio simulation, MT5 connectivity, optimization, persistence, and analytics while introducing an agentic control plane for orchestration, research, strategy formation, portfolio analysis, risk gating, monitoring, and broker execution.

All material workflows in the system shall conform to the mandatory execution law:

```text
Reason → Plan → Act → Observe → Evaluate → Refine/Finish
```

This law is a runtime requirement and shall be enforced by workflow state management, evaluation policy, and audit logging.

### 1.1 Objectives

The objectives of this refactor are:

- preserve HaruQuant’s deterministic trading and analytics capabilities
- introduce bounded multi-agent autonomy without permitting uncontrolled execution
- ensure that all live-trading actions are policy-governed and risk-gated
- make every execution-bound decision reproducible, inspectable, and replayable
- provide a dashboard and API surface for human supervision, override governance, and operational monitoring
- support progressive rollout from advisory workflows to bounded autonomous live trading

### 1.2 Non-Objectives

This specification does not require:

- replacing deterministic numerical engines with LLM reasoning
- introducing sub-10ms high-frequency execution logic
- supporting all brokers in the first production release
- delegating legal or compliance interpretation to language models

---

## 2. Scope

### 2.1 In Scope

The system shall include:

- agentic orchestration of research, portfolio, strategy, monitoring, and execution workflows
- integration of external capabilities through MCP-exposed tool interfaces
- portfolio-level and symbol-level risk governance
- live, paper, simulation, and advisory operating modes
- trajectory logging, replay, evaluation, and audit support
- operator-facing dashboard and API for supervision and governance
- strategy promotion workflows from research to live production
- failure handling, reconciliation, and restart recovery for execution-critical workflows

### 2.2 Out of Scope

The system shall not initially include:

- multi-broker live execution beyond MetaTrader 5 in release 1
- mobile-first operator interfaces
- fully autonomous strategy invention without prior bounded validation
- unsupervised regulatory filing or legal interpretation by language models
- latency-sensitive HFT workflows requiring colocated execution infrastructure

### 2.3 Product Vision

HaruQuant shall become a governed agentic trading platform in which:

- user intent, scheduled jobs, market events, and internal triggers may initiate workflows
- specialist agents collaborate through versioned, schema-validated contracts
- no live broker action occurs without current policy evaluation and risk approval
- humans can supervise, approve, pause, or escalate workflows according to role and mode
- every material workflow step is recorded for replay, review, and continuous improvement

---

## 3. Governing Principles and Invariants

### 3.1 Core Invariants

**INV-001** No live execution action shall occur without a valid risk decision.

**INV-002** No agent shall access external side-effecting capabilities except through approved MCP-exposed tool interfaces.

**INV-003** All inter-agent messages shall be schema-validated.

**INV-004** All execution-bound decisions shall be attributable to a workflow, policy version, and decision provenance bundle.

**INV-005** Any uncertainty in execution-critical validation shall fail closed unless an explicitly defined emergency-exit policy applies.

**INV-006** Research conclusions shall not be treated as execution instructions unless converted into a validated trade proposal and passed through risk gating.

### 3.2 Separation of Concerns

**INV-010** Deterministic compute and numerical engines shall remain distinct from language-model reasoning.

**INV-011** Research and execution roles shall remain distinct.

**INV-012** Policy definition shall remain distinct from policy enforcement.

**INV-013** Human supervisory action shall remain distinct from silent programmatic bypass.

**INV-014** Replay and audit storage shall remain distinct from mutable operational state.

### 3.3 Boundaries of Model Authority

**INV-020** Language models may assist with reasoning, decomposition, summarization, hypothesis generation, evaluation, and explanation.

**INV-021** Language models shall not be treated as authoritative sources for live market prices, account balances, broker execution state, regulatory obligations without grounded evidence, or deterministic risk values when deterministic engines are available.

---

## 4. Stakeholders and User Classes

| Role | Responsibilities | Required Capabilities |
|------|------------------|----------------------|
| Trader / Portfolio Manager | Review opportunities, supervise execution, manage positions | Real-time decision support, bounded autonomy controls, position visibility |
| Quant Researcher | Develop strategies, analyze robustness, compare candidates | Research workflows, backtest access, evidence bundles, promotion pipeline |
| Risk Manager | Define limits, monitor exposures, supervise risk events | Mandatory risk gating, policy controls, kill-switch authority, override governance |
| Compliance / Audit | Review decisions, export records, inspect overrides | Immutable logs, replay, compliance profile mapping, export support |
| Operations / DevOps | Deploy and monitor runtime services | Health visibility, failure diagnostics, rollback, reconciliation tooling |
| Frontend Operator | Use dashboard for supervision and workflow control | Live updates, drill-downs, approval queues, alerts |
| External Systems | MT5, data stores, market data, retrieval systems | Secure, authorized, well-defined MCP integration |

---

## 5. System Context

The platform shall operate across the following runtime domains:

1. **Operator Interface Layer**  
   Dashboard, APIs, approval flows, alerts, and replay views.

2. **Agentic Control Layer**  
   Orchestration runtime, workflow engine, state machine enforcement, evaluation control, memory boundaries, and policy application.

3. **Tool Integration Layer**  
   MCP-exposed connectors for broker execution, data access, risk analytics, retrieval, and market-context services.

4. **Deterministic Compute Layer**  
   Backtesting engines, optimization engines, portfolio and risk calculators, reconciliation processes, and analytics jobs.

5. **Persistence and Audit Layer**  
   Relational state, object artifacts, logs, replay bundles, signed audit records, and configuration history.

6. **External System Layer**  
   MetaTrader 5 terminal, market data providers, document stores, calendar/news data, and other approved external systems.

---

## 6. Operating Modes and Autonomy Boundaries

### 6.1 Operating Modes

**MODE-000 Research Only**  
The system may retrieve information, summarize findings, generate hypotheses, and produce reports. It shall not produce executable intents.

**MODE-001 Advisory**  
The system may generate trade proposals and portfolio recommendations but shall not place or simulate broker actions as live intents.

**MODE-002 Paper Execution**  
The system may execute full workflows against simulated or paper accounts, including simulated risk gating and execution recording.

**MODE-003 Human-Approved Live**  
The system may produce live execution intents only after risk approval and human approval by an authorized role.

**MODE-004 Bounded Autonomous Live**  
The system may execute live orders without per-trade human approval only inside a pre-approved strategy, symbol, session, and risk envelope.

### 6.2 Mode Scoping

**FR-001** The active operating mode shall be scoped at minimum by environment, account, strategy family, symbol or symbol group, workflow type, and user or role.

**FR-002** Every workflow shall execute under exactly one active operating mode.

### 6.3 Mode Escalation Rules

**FR-003** If a workflow attempts an action not permitted by its active mode, the system shall deny the action or escalate it to an authorized approval path if policy permits.

**FR-004** No workflow may self-escalate its autonomy level.

---

## 7. Workflow Model and Canonical State Machines

### 7.1 Workflow Law Enforcement

**FR-005** Every material workflow shall explicitly pass through the phases Reason, Plan, Act, Observe, Evaluate, and Refine or Finish.

**FR-006** The workflow engine shall prevent completion of a non-emergency workflow if Observe or Evaluate is skipped.

**FR-007** Emergency-exit workflows may execute action before evaluation only when governed by an explicit emergency-exit policy, and evaluation shall occur post-action.

### 7.2 Workflow State Machine

**FR-008** Each workflow shall implement an explicit finite state machine with at minimum the states CREATED, REASONING, PLANNING, ACTING, OBSERVING, EVALUATING, REFINING, COMPLETED, FAILED, CANCELLED, BLOCKED_BY_RISK, BLOCKED_BY_POLICY, TIMED_OUT, and RECONCILING.

**FR-009** The workflow engine shall validate all state transitions.

### 7.3 Trade Proposal State Machine

**FR-010** Every trade proposal shall implement at minimum the states DRAFT, EVIDENCE_PENDING, READY_FOR_RISK, APPROVED, APPROVED_WITH_LIMITS, REJECTED, EXPIRED, EXECUTION_PENDING, SENT, ACKNOWLEDGED, PARTIALLY_FILLED, FILLED, EXECUTION_FAILED, and CLOSED.

### 7.4 Incident and Kill Switch State Machines

**FR-011** Every safety or operational incident shall implement at minimum the states DETECTED, TRIAGED, ACTIVE, CONTAINED, RESOLVED, POSTMORTEM_PENDING, and CLOSED.

**FR-012** The kill switch shall support at minimum the states ARMED, SOFT_TRIGGERED, HARD_TRIGGERED, RECOVERY_PENDING, and RECOVERY_APPROVED.

**FR-013** The system shall not leave a triggered kill-switch state without authorized recovery action.

---

## 8. Functional Requirements

### 8.1 Autonomous Workflow Requirements

**FR-014** The system shall support workflows triggered by user action, schedule, market event, or internal system event.

**FR-015** Every workflow shall declare objective, constraints, permitted tools, required agents, stop conditions, timeout policy, evaluation criteria, and active operating mode.

**FR-016** The system shall support both symbol-level and portfolio-level workflows.

**FR-017** The same logical workflow model shall support simulation, paper, advisory, and live variants.

### 8.2 Multi-Agent Collaboration Requirements

**FR-018** The platform shall use specialist agents rather than a single monolithic agent.

**FR-019** The minimum agent set shall include OrchestratorAgent, StrategyAgent, RiskGovernorAgent, ExecutionAgent, PortfolioAgent, ResearchAgent, MonitoringAgent, and ComplianceAgent.

**FR-020** The platform may include sub-agents such as RegimeAgent, VolatilityAgent, SlippageAgent, and other domain specialists.

**FR-021** Agents shall communicate through versioned, schema-validated contracts.

**FR-022** Agents shall not access external services directly except through approved tool interfaces.

**FR-023** Agents shall be independently testable in isolation and in integrated workflows.

**FR-024** The orchestration layer shall support sequential, routing, parallel, evaluator-optimizer, and orchestrator-worker patterns where appropriate.

### 8.3 Canonical Contract Requirements

**FR-025** The platform shall define and enforce canonical message families for at minimum WorkflowIntent, WorkflowPlan, TradeHypothesis, RiskAssessmentRequest, RiskAssessmentDecision, ExecutionIntent, ExecutionReceipt, ObservationEvent, EvaluationReport, IncidentAlert, OverrideRequest, OverrideDecision, and ReplayBundle.

**FR-026** Every canonical contract shall include at minimum schema_version, workflow_id, correlation_id, causation_id or parent reference, timestamp, originator identity, environment, and operating mode.

**FR-027** Breaking changes to canonical contracts shall require version increments and compatibility handling.

### 8.4 Risk Gating Requirements

**FR-028** Every live action that can place, modify, scale, hedge, or close a position or order shall require a current RiskGovernor decision.

**FR-029** A risk decision shall become invalid when its freshness threshold expires, when the proposal materially changes, or when market or account conditions invalidate its assumptions.

**FR-030** If risk evaluation is missing, stale, malformed, or non-reproducible, the system shall deny new live entry actions.

**FR-031** RiskGovernor shall evaluate at minimum account equity and free margin, portfolio gross and net exposure, per-symbol and per-currency concentration, per-strategy-family concentration, volatility-adjusted sizing, correlation concentration, spread and slippage conditions, drawdown state, regime restrictions, session restrictions and blackout windows, kill-switch state, policy profile, and operating mode.

**FR-032** RiskGovernor shall return one of the following decisions: APPROVE, APPROVE_WITH_LIMITS, REJECT, or FORCE_EXIT.

**FR-033** APPROVE_WITH_LIMITS shall include machine-enforceable constraints such as size limits, entry deviation tolerance, stop requirements, and expiry time.

**FR-034** The exact rationale, metrics snapshot, policy version, and decision provenance shall be persisted for every risk decision.

### 8.5 Human Governance Requirements

**FR-035** The system shall define explicit supervisory roles and permissions for approvals, overrides, kill-switch actions, and policy changes.

**FR-036** Risk gating shall not be bypassable by ordinary workflow logic or agent self-modification.

**FR-037** If supervisory override is enabled by policy, it shall require authorized role membership, explicit reason code, written rationale, bounded expiry, immutable audit trail, and dual authorization for live execution contrary to REJECT decisions.

**FR-038** The system shall distinguish between approval of workflow initiation, approval of policy change, approval of live execution, and supervisory override of a rejected decision.

### 8.6 Strategy Requirements

**FR-039** StrategyAgent shall generate trade hypotheses, not broker orders.

**FR-040** Every trade hypothesis shall include at minimum symbol, direction, thesis, evidence references, entry rationale, invalidation rationale, intended stop-loss logic, intended take-profit or exit logic, intended holding horizon, confidence score with calibration note, and required validation data.

**FR-041** Strategy hypotheses shall be convertible into validated trade proposals only through canonical schema transformation.

**FR-042** The system shall support multiple strategy families including trend-following, mean reversion, breakout, carry or macro overlay, rebalancing, and volatility-conditioned variants.

**FR-043** The system shall support comparing multiple candidate actions before producing a final proposal.

### 8.7 Strategy Lifecycle Requirements

**FR-044** Every strategy shall exist in one lifecycle state at a time: RESEARCH, BACKTEST_QUALIFIED, ROBUSTNESS_QUALIFIED, PAPER_APPROVED, LIVE_LIMITED, LIVE_PRODUCTION, SUSPENDED, or RETIRED.

**FR-045** Promotion between strategy states shall require defined evidence bundles and approval gates.

**FR-046** The system shall persist promotion rationale, evidence references, approver identity, and effective date for each lifecycle transition.

**FR-047** A strategy may not enter autonomous live execution unless it is in LIVE_LIMITED or LIVE_PRODUCTION and is explicitly allowed by operating mode and policy profile.

### 8.8 Portfolio and Optimization Requirements

**FR-048** The system shall support portfolio-level analysis and optimization that can inspect open positions, pending orders, exposure concentrations, and marginal risk contribution.

**FR-049** Portfolio workflows shall be able to propose resizing, rebalancing, hedging, and de-risking actions.

**FR-050** Portfolio optimization shall be advisory by default and shall require live approval and risk gating before any execution.

**FR-051** Portfolio proposals shall include projected impact on VaR and expected shortfall, margin utilization, concentration risk, and projected distribution of outcomes.

### 8.9 Research Requirements

**FR-052** Research workflows shall support grounded retrieval from approved structured data, internal documents, prior experiments, and approved external sources.

**FR-053** Research outputs shall include evidence references, freshness indicators, assumptions, and limitations.

**FR-054** Research agents shall not directly place live orders or modify broker state.

**FR-055** Low-confidence research workflows shall support refinement loops according to policy.

### 8.10 Execution Requirements

**FR-056** ExecutionAgent shall translate approved execution intents into broker-specific instructions.

**FR-057** Immediately before broker submission, the execution layer shall validate market open state, symbol tradability, price freshness, spread versus allowed threshold, stop and freeze-level constraints, supported fill mode, terminal connectivity, and risk-approval freshness and match.

**FR-058** The execution layer shall support at minimum market orders, pending orders, stop-loss or take-profit modification, partial close, full close, and pending-order cancellation.

**FR-059** Every live execution action shall produce a broker receipt, normalized execution record, idempotency key, and linkage to risk decision and workflow provenance.

**FR-060** Post-send reconciliation shall verify broker state before permitting duplicate retries.

### 8.11 Monitoring and Observation Requirements

**FR-061** The system shall continuously observe broker responses, position changes, margin state, latency, tool health, schema failures, and workflow transitions.

**FR-062** MonitoringAgent shall emit alerts classified at minimum as WARNING, INCIDENT, CRITICAL_INCIDENT, and KILL_SWITCH_TRIGGER.

**FR-063** All observations shall be timestamped, attributable, and correlated to workflow context.

### 8.12 Dashboard and Operator Interaction Requirements

**FR-064** The dashboard shall display real-time or near-real-time status for workflows, positions, proposals, risk decisions, incidents, alerts, and evaluation results.

**FR-065** Operators shall be able to inspect each workflow phase and its inputs, outputs, and rationale.

**FR-066** Operators shall be able to configure, subject to policy and role, operating mode, symbol and strategy allowlists, risk limits, session windows, approval routing, and kill-switch actions.

**FR-067** The dashboard shall display whether a state is authoritative, provisional, or under reconciliation.

---

## 9. Memory and Context Governance

**FR-068** The system shall distinguish at minimum between session memory, workflow memory, long-term research memory, cached market and account context, and immutable replay memory.

**FR-069** No live execution decision shall depend on ungrounded conversational memory or long-term natural-language memory without validation against current structured data.

**FR-070** Execution-critical inputs shall declare freshness policies. If freshness is violated, the action shall fail closed unless an emergency-exit policy permits otherwise.

**FR-071** Replay artifacts shall be immutable and shall not be modified by subsequent agent memory updates.

---

## 10. Data, Provenance, and Reproducibility Requirements

**FR-072** The system shall persist at minimum market snapshots used in decisions, trade hypotheses and proposals, risk assessments, execution intents and receipts, workflow state history, agent trajectory logs, evaluation outputs, operator actions and overrides, strategy promotion artifacts, and replay bundles.

**FR-073** Every execution-bound decision shall record a provenance bundle including at minimum workflow_id and correlation_id, market data snapshot or version reference, account snapshot reference, symbol metadata snapshot, strategy identifier and code hash, feature-pipeline version, policy version, model identifier or model family, prompt or instruction hash where applicable, and schema versions for all critical contracts.

**FR-074** Retention periods shall be configurable by compliance profile. Records under legal hold shall not be purged automatically.

---

## 11. Failure Semantics and Recovery Requirements

**FR-075** Execution-critical failures shall fail closed for new entries and shall reconcile before retry.

**FR-076** The system shall define deterministic handling for at minimum stale market data, stale risk decision, stale account snapshot, tool timeout, broker acknowledgement delay, duplicate receipt, partial persistence failure, process restart during execution workflow, schema validation failure, and conflicting broker and local state.

**FR-077** On restart, the system shall reconcile all in-flight execution intents against broker state using idempotency keys before permitting new live execution.

**FR-078** The system may define a separate emergency-exit policy for forced liquidation or position reduction under extreme risk conditions. Such actions shall still be audited and reconciled.

---

## 12. Non-Functional Requirements

### 12.1 Safety

**NFR-001** A global kill switch shall block new live execution and may optionally trigger force-exit logic according to policy.

**NFR-002** The system shall fail closed on execution-critical uncertainty, timeout, schema failure, or stale validation state unless emergency-exit rules apply.

**NFR-003** RiskGovernor and ExecutionAgent authority boundaries shall be technically enforced and not convention-based.

### 12.2 Observability

**NFR-004** The platform shall provide complete trajectory logging for production workflows.

**NFR-005** Logs shall support filtering, replay, export, and tamper-evident integrity checks.

### 12.3 Performance

**NFR-006** Risk evaluation p95 latency shall be less than or equal to 300 ms for cached local-data workflows under normal production load.

**NFR-007** Execution readiness validation p95 latency shall be less than or equal to 400 ms excluding broker and external network latency.

**NFR-008** End-to-end trade decision workflow p95 latency shall be less than or equal to 2.5 seconds for cached local-data workflows.

**NFR-009** Dashboard state propagation p95 latency from backend event ingestion to operator display shall be less than or equal to 500 ms for authoritative state updates.

**NFR-010** Research first-answer p95 latency shall be less than or equal to 6 seconds for grounded retrieval and synthesis workflows.

**NFR-011** Portfolio optimization advisory run p95 latency shall be less than or equal to 4 seconds for portfolios of up to 20 open positions under standard load.

### 12.4 Reliability

**NFR-012** The platform shall degrade gracefully to advisory-only or read-only modes when execution dependencies are unavailable.

**NFR-013** Duplicate broker actions shall be prevented through idempotency and reconciliation.

**NFR-014** Workflow state shall be versioned and concurrency-safe.

### 12.5 Security

**NFR-015** Secrets shall not be exposed to model context.

**NFR-016** Tool access shall be authenticated and authorized.

**NFR-017** Policy changes, overrides, and operator actions shall be attributable and auditable.

**NFR-018** Contract validation failures shall be observable and actionable.

### 12.6 Reproducibility and Change Control

**NFR-019** Production changes affecting prompts, policies, schemas, risk formulas, or execution logic shall be versioned and rollback-capable.

**NFR-020** Decision provenance shall be sufficient to reconstruct any live execution decision after the fact.

---

## 13. Compliance and Audit Requirements

**FR-079** The platform shall support configurable compliance profiles so that controls, retention, exports, and review paths can be adapted by jurisdiction, entity type, and deployment context.

**FR-080** All critical decisions shall record at minimum timestamp, actor or agent identity, workflow linkage, input and output references or hashes, policy version, and reason codes where applicable.

**FR-081** Supervisory overrides shall record original blocked action, original decision, override approvers, reason code, narrative rationale, expiry, and downstream result.

---

## 14. Validation and Testing Requirements

**FR-082** The system shall include unit tests for canonical contracts and deterministic engines.

**FR-083** The system shall include integration tests for full workflow paths.

**FR-084** The system shall include scenario tests for state-machine transitions.

**FR-085** The system shall include chaos tests for tool timeouts and disconnections.

**FR-086** The system shall include reconciliation tests for duplicate and delayed receipts.

**FR-087** The system shall include replay tests for audit reconstruction.

**FR-088** The system shall include permission and penetration tests for risk-gate enforcement.

**FR-089** The system shall include red-team tests for prompt injection against research-connected agents.

**FR-090** Before bounded autonomous live execution is enabled for a strategy, it shall pass shadow-mode and paper-mode verification according to policy.

---

## 15. Success Criteria

**SC-001** Unauthorized live executions bypassing risk control shall equal zero.

**SC-002** Full traceability shall be available for one hundred percent of live execution decisions.

**SC-003** Replay reconstruction success rate for execution-critical workflows shall be at least 99.5 percent.

**SC-004** Recovery from degraded dependency scenarios shall preserve safety invariants in one hundred percent of tested cases.

**SC-005** Runtime enforcement of autonomy boundaries shall pass one hundred percent of approval-path tests.

**SC-006** Strategy promotion controls shall be enforced for one hundred percent of strategies entering live-limited or live-production states.

---

## 16. Acceptance Criteria

**AC-001** All live side-effecting broker actions shall be gated by enforced authority boundaries.

**AC-002** All material workflows shall implement the required execution law.

**AC-003** Canonical contracts shall be versioned and validated.

**AC-004** Operating modes and approvals shall be enforced in runtime behavior.

**AC-005** Restart reconciliation shall prevent duplicate live execution.

**AC-006** Dashboard and audit views shall reconstruct execution history end to end.

**AC-007** Strategy promotion controls and override controls shall operate as specified.

**AC-008** Performance targets in Section 12 shall be met under agreed load-test conditions.

---

## Appendix A: Glossary

| Term | Definition |
|------|-----------|
| Agentic Control Plane | The orchestration layer responsible for workflow routing, state management, approvals, and evaluation |
| Operating Mode | The bounded autonomy level under which a workflow executes |
| Risk Decision | The machine-enforceable approval outcome issued by RiskGovernor |
| Provenance Bundle | The set of artifacts required to reconstruct and justify a decision |
| Replay Bundle | The immutable record set required to audit or simulate a prior workflow |
| Supervisory Override | A controlled human-governed action that supersedes a blocked decision under policy |
| Fail Closed | Default-deny behavior under uncertainty or validation failure |
| Reconciliation | The process of aligning local workflow state with authoritative broker or system state |

---

## Appendix B: Board Approval Notes

This version incorporates governance, freshness, promotion, and compliance appendices required for executive and technical sign-off.

---

## Appendix C: Role Authority Matrix

The following matrix defines the minimum authority model for HaruQuant. Deployment profiles may tighten these permissions but shall not grant broader authority than defined here without formal approval.

### C.1 Roles

- **VIEWER**: read-only dashboard and replay access
- **OPERATOR**: may start, pause, cancel, and supervise workflows within assigned scope
- **TRADER**: may review and approve eligible live execution actions in supervised-live mode
- **RISK_MANAGER**: may define and approve risk policies, risk limits, and kill-switch recovery actions within policy scope
- **COMPLIANCE_OFFICER**: may review overrides, approvals, audit exports, and legal-hold controls
- **OPS_ADMIN**: may operate infrastructure, restart services, and manage runtime availability without changing trading policy logic
- **SYSTEM_ADMIN**: may manage platform-level configuration and access control; shall not unilaterally approve live trading overrides unless also assigned a trading governance role

### C.2 Authority Principles

**AUTH-001** No single role shall both define trading-risk policy and silently override that same policy in production without audit.

**AUTH-002** Any action that permits live execution contrary to a REJECT decision shall require dual authorization.

**AUTH-003** Infrastructure authority shall not imply trading authority.

**AUTH-004** Read access to replay and audit data may be broader than write authority over execution or policy.

### C.3 Authority Matrix

| Action | Viewer | Operator | Trader | Risk Manager | Compliance Officer | Ops Admin | System Admin |
|---|---:|---:|---:|---:|---:|---:|---:|
| View dashboard, alerts, positions, replay | Y | Y | Y | Y | Y | Y | Y |
| Start research workflow | N | Y | Y | Y | Y | N | Y |
| Start advisory workflow | N | Y | Y | Y | Y | N | Y |
| Start paper workflow | N | Y | Y | Y | N | N | Y |
| Start supervised live workflow | N | Y | Y | Y | N | N | Y |
| Approve single live execution in MODE-003 | N | N | Y | Y | N | N | N |
| Change operating mode for a workflow scope | N | Y* | Y* | Y | N | N | Y* |
| Change risk limits | N | N | N | Y | N | N | N |
| Approve risk policy change | N | N | N | Y | Y | N | N |
| Trigger soft kill switch | N | Y | Y | Y | N | Y | Y |
| Trigger hard kill switch | N | Y | Y | Y | N | Y | Y |
| Recover from soft kill switch | N | N | N | Y | N | Y* | Y* |
| Recover from hard kill switch | N | N | N | Y | Y | N | N |
| Supervisory override of REJECT for live action | N | N | N | Y | Y | N | N |
| Put strategy into LIVE_LIMITED | N | N | Y | Y | N | N | N |
| Put strategy into LIVE_PRODUCTION | N | N | Y | Y | Y | N | N |
| Suspend strategy | N | Y* | Y | Y | N | N | Y* |
| Retire strategy | N | N | Y | Y | Y | N | N |
| Place legal hold on records | N | N | N | N | Y | N | Y* |
| Export regulated audit package | N | N | N | N | Y | N | Y* |
| Restart services / fail over infrastructure | N | N | N | N | N | Y | Y |

`Y*` means permitted only within assigned scope and subject to change-control policy.

### C.4 Dual-Authorization Rules

**AUTH-010** The following actions shall require two distinct authorized approvers:

- supervisory override of a REJECT decision for a live action
- promotion of a strategy to LIVE_PRODUCTION
- recovery from HARD_TRIGGERED kill-switch state
- approval of production risk-policy changes
- approval of compliance-profile changes affecting retention, exports, or review paths

**AUTH-011** The same individual shall not satisfy both approval slots.

**AUTH-012** Dual-authorization actions shall store approver identities, timestamps, reason codes, and approval sequence.

---

## Appendix D: Freshness and TTL Policy

Execution-critical safety depends on bounded freshness. The system shall evaluate freshness before permitting live actions.

### D.1 Freshness Principles

**TTL-001** Every execution-critical artifact shall declare a freshness class and maximum age.

**TTL-002** If freshness cannot be verified, the artifact shall be treated as stale.

**TTL-003** New live entry actions shall fail closed on stale critical artifacts.

**TTL-004** Emergency exits may use degraded freshness rules only if an emergency-exit policy explicitly allows it.

### D.2 Minimum Freshness Classes

| Artifact | Freshness Class | Maximum Age | Action if Stale |
|---|---|---:|---|
| Best bid/ask tick | HOT | 2 seconds | Block new entries; allow emergency exits per policy |
| Spread snapshot | HOT | 2 seconds | Recompute before execution |
| Symbol tradability status | HOT | 5 seconds | Revalidate before execution |
| Account equity/free margin snapshot | HOT | 5 seconds | Block new entries |
| Open positions snapshot | HOT | 5 seconds | Reconcile before execution |
| Risk decision | HOT | 30 seconds | Invalidate and recompute |
| Correlation matrix / concentration snapshot | WARM | 60 seconds | Recompute before risk approval |
| Regime classification | WARM | 5 minutes | Re-evaluate before new entry |
| Volatility state estimate | WARM | 5 minutes | Re-evaluate sizing inputs |
| Economic calendar blackout state | WARM | 5 minutes | Refresh before execution during active sessions |
| Strategy eligibility / lifecycle state | COOL | 10 minutes | Refresh before approving live action |
| Compliance profile and approval policy | COOL | 15 minutes | Refresh before policy-sensitive action |
| Replay bundle metadata | COLD | 24 hours | Refresh only if needed for display |

### D.3 TTL Enforcement Requirements

**TTL-010** Matching between risk decision and execution intent shall include validation that all referenced HOT and WARM artifacts remain within maximum age.

**TTL-011** A material proposal change shall invalidate any prior risk decision even if the TTL has not expired.

**TTL-012** A workflow pause longer than the shortest relevant TTL shall require revalidation before live execution continues.

**TTL-013** Dashboard displays shall visually distinguish current, aging, and stale safety-critical values.

### D.4 Degraded-Mode Freshness

**TTL-020** In degraded mode, the platform may continue research, advisory, replay, and non-side-effecting analytics with stale WARM or COOL artifacts, but not live new-entry execution.

**TTL-021** When broker state and local state disagree beyond TTL limits, the system shall enter RECONCILING before permitting further live actions.

---

## Appendix E: Strategy Promotion Gate Criteria

This appendix defines the minimum promotion controls for moving strategies from research to live deployment.

### E.1 Promotion Principles

**PROM-001** No strategy shall enter a higher lifecycle state without satisfying the evidence requirements for that state.

**PROM-002** Promotion shall be based on evidence bundles, not narrative claims alone.

**PROM-003** Failure in live-limited or live-production monitoring may trigger automatic suspension according to policy.

### E.2 Required Evidence Bundle Components

Every promotion package shall include, at minimum:

- strategy identifier and version
- source code or immutable code hash
- parameter set and parameter constraints
- data range used for evaluation
- market(s), symbol(s), timeframe(s), and session constraints
- backtest summary metrics
- robustness test results
- risk profile summary
- failure cases and known limitations
- proposed operating envelope for live use
- approval record and approver identities

### E.3 Lifecycle Gates

#### RESEARCH → BACKTEST_QUALIFIED

**PROM-010** Required evidence:

- complete backtest run on designated in-sample and out-of-sample ranges
- minimum trade count threshold defined by strategy family policy
- positive expectancy or equivalent target metric under policy
- max drawdown within family threshold
- parameter set recorded and reproducible

#### BACKTEST_QUALIFIED → ROBUSTNESS_QUALIFIED

**PROM-011** Required evidence:

- walk-forward or equivalent robustness validation
- sensitivity or parameter stability analysis
- slippage and spread stress test
- market-regime or cross-period robustness review
- failure notes for adverse conditions

#### ROBUSTNESS_QUALIFIED → PAPER_APPROVED

**PROM-012** Required evidence:

- approval of live operating envelope including symbols, hours, max size, and stop logic
- paper execution simulation path defined
- monitoring and alert thresholds defined
- rollback/suspension criteria defined

#### PAPER_APPROVED → LIVE_LIMITED

**PROM-013** Required evidence:

- successful shadow-mode verification where applicable
- paper-mode behavior consistent with expectations under policy
- risk manager approval
- trader approval
- maximum capital/risk envelope for live-limited deployment
- mandatory human supervision path if required by operating mode

#### LIVE_LIMITED → LIVE_PRODUCTION

**PROM-014** Required evidence:

- live-limited period completed without disqualifying incidents
- live execution quality within approved thresholds for slippage, fill quality, and operational stability
- drift between expected and realized behavior within policy tolerance
- dual authorization by trader and risk manager, with compliance review if required by profile

### E.4 Suspension and Retirement

**PROM-020** A strategy shall be suspended automatically or manually if:

- live drawdown breaches its strategy envelope
- operational incidents exceed policy threshold
- slippage or fill-quality deterioration exceeds threshold
- model, data, or code provenance cannot be verified
- compliance profile no longer permits its deployment mode

**PROM-021** Suspended strategies shall not generate autonomous live execution intents.

**PROM-022** Retirement shall require preservation of final evidence, final rationale, and effective retirement date.

### E.5 Quantitative Threshold Ownership

**PROM-030** Exact numerical thresholds for trade counts, expectancy, drawdown, walk-forward acceptance, live-limited duration, and drift tolerance shall be maintained in policy-controlled strategy-family profiles.

**PROM-031** Threshold changes shall be versioned and auditable.

---

## Appendix F: Compliance Profiles

The platform shall support configurable compliance profiles that determine retention, approval routing, export requirements, and legal-hold behavior.

### F.1 Compliance Profile Principles

**COMP-001** Compliance profiles shall be configuration-driven and versioned.

**COMP-002** A deployment shall operate under exactly one active primary compliance profile, with optional supplemental controls.

**COMP-003** If compliance profile resolution fails, the system shall default to the safer enforcement option for live execution and retention behavior.

### F.2 Minimum Supported Profiles

#### F.2.1 Internal / Non-Regulated Profile

Intended for development, testing, and internal research environments.

Minimum controls:

- reduced retention permitted
- simplified approval routing allowed
- replay and audit still required for execution testing
- no claim of regulatory completeness

#### F.2.2 UAE Enterprise Profile

Intended for enterprise deployment requiring strong auditability, role separation, and configurable retention controls.

Minimum controls:

- role-based approval and override controls
- signed audit logs
- configurable retention with legal hold
- exportable review bundles
- dual authorization for designated live overrides and production policy changes

#### F.2.3 UK / EU Enterprise Profile

Intended for deployments needing stronger formalized recordkeeping and transaction review controls.

Minimum controls:

- signed immutable decision logs
- extended retention support
- best-execution and transaction-review export capability
- stricter override review and compliance sign-off paths where configured
- legal-hold and supervisory review support

#### F.2.4 US Enterprise Profile

Intended for deployments needing strong market-access, supervisory, and audit evidence controls.

Minimum controls:

- strong pre-trade risk control evidence
- immutable override and policy-change trail
- exportable supervisory review packages
- legal-hold support
- dual authorization for designated production actions

### F.3 Compliance-Control Dimensions

Each profile shall define, at minimum:

- default retention schedules
- legal-hold behavior
- override approval requirements
- policy-change approval requirements
- audit export package contents
- review cadence for production controls
- required signatories for designated actions

### F.4 Profile Enforcement Requirements

**COMP-010** The active compliance profile shall be attached to every live execution workflow.

**COMP-011** Policy-sensitive actions shall validate against the active compliance profile before execution.

**COMP-012** Compliance profile changes in production shall require dual authorization and immutable audit logging.

**COMP-013** Exports shall clearly state the profile under which they were generated.

### F.5 Initial Deployment Recommendation

For HaruQuant board approval, the recommended default profile for first controlled production deployment is:

- **UAE Enterprise Profile** for primary deployment
- **Internal / Non-Regulated Profile** for development and isolated testing environments

---

## Appendix G: Board Approval Baselines

The following baselines are approved for Version 3.1.1 unless superseded by policy-controlled configuration:

### G.1 Governance Baseline

- supervisory override of a live REJECT decision requires dual authorization from Risk Manager and Compliance Officer, or Risk Manager and an explicitly designated second approver under the active compliance profile
- HARD_TRIGGERED kill-switch recovery requires dual authorization
- production risk-policy change requires dual authorization
- infrastructure restart authority does not grant live trade approval authority

### G.2 Freshness Baseline

- market tick TTL: 2 seconds
- spread TTL: 2 seconds
- account snapshot TTL: 5 seconds
- positions snapshot TTL: 5 seconds
- risk decision TTL: 30 seconds
- regime and volatility TTL: 5 minutes

### G.3 Promotion Baseline

Exact quantitative thresholds remain policy-controlled, but no strategy may enter LIVE_PRODUCTION without:

- successful LIVE_LIMITED period
- no unresolved critical incidents
- signed promotion record
- approved operating envelope

### G.4 Compliance Baseline

- UAE Enterprise Profile is the initial production baseline
- Internal / Non-Regulated Profile is limited to non-production environments

---

## Appendix H: Merged Approval Statement

This Board Approval Version 3.1.1 includes the core specification and Appendices A through G as a single merged governing document for HaruQuant’s agentic system requirements.

Any implementation, design, or operational policy that conflicts with this document shall require formal revision of this specification or an explicitly versioned exception approved under the active governance process.
