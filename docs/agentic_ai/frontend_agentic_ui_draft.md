# HaruQuant Agentic Frontend Draft

This draft reshapes the frontend around the backend's new operating model:

- agents propose, classify, summarize, and plan
- deterministic services decide, persist, enforce, and audit
- operators supervise workflow state, risk gates, approvals, incidents, replay, evidence, and strategy lifecycle

The existing frontend should stop treating live trading, research, optimization, and performance as isolated legacy tools. Those areas remain useful, but the primary navigation should expose the agentic control plane as the system of record.

## Product Frame

The frontend should answer four operator questions at all times:

1. What is the agentic system doing now?
2. What is blocked, stale, risky, or waiting for a human?
3. What evidence supports the current recommendation or action?
4. What deterministic service owns the next state transition?

This means the UI needs to show provenance, authority state, policy status, and replayability beside every workflow and execution-bound artifact.

## Primary Navigation

| Area | Purpose | Backend Source |
|---|---|---|
| Command Center | Cross-system state, incidents, approvals, live events, broker safety posture | `backend/read_models/operator_dashboard.py`, `/api/operator`, `/api/operator/events/stream` |
| Workflows | Workflow state machine, phase steps, assigned agents, trajectory logs, evaluation reports | `backend/orchestration/workflow`, `backend/agents/runtime`, workflow read models |
| Agent Runs | Agent sessions, prompt versions, tool calls, schema validation, cost and latency | `backend/agents/runtime`, `backend/observability`, `services/execution/cost` |
| Proposals | Trade hypotheses, proposal readiness, queue state, proposal drift, expiry | `backend/contracts/trade_hypothesis`, `backend/contracts/trade_proposal`, `services/strategy/proposals` |
| Risk Gate | Deterministic risk decisions, constraints, freshness, concentration, margin, drawdown, correlation | `backend/contracts/risk_assessment_*`, `services/risk`, `services/risk` |
| Execution Control | Execution intents, readiness, attempts, receipts, reconciliation, compensation | `backend/contracts/execution_*`, `services/execution`, `services/execution/reconciliation` |
| Approvals | Live execution, override, policy change, kill-switch recovery voting | `/api/operator/approvals`, `services/execution/approval` |
| Incidents | Monitoring alerts, stale state, broker conflicts, kill switch state, containment | `services/execution/monitoring`, `services/risk/safety` |
| Evidence | Evidence bundles, lifecycle proof, artifact freshness, manifests | `services/strategy/evidence`, `services/strategy/governance` |
| Replay And Audit | Replay bundles, manifests, signatures, legal hold, export status | `services/strategy/evidence/audit`, `backend/contracts/replay_bundle` |
| Strategy Governance | Strategy registry, lifecycle, promotion, suspension, retirement, operating envelope | `services/strategy/governance` |
| Research Lab | Research-only agent workflows, edge discovery, market regime, scorecards | `backend/agents/research_agent.py`, `backend/api/routes/edge.py` |
| Legacy Tools | Backtest, simulation, SQX import, optimization, performance reports | existing `/api/backtest`, `/api/simulator`, `/api/sqx`, `/api/optimization` |

## Command Center Layout

The landing view should be operational, not promotional.

Top status strip:

- system authority: advisory, paper, limited live, halted
- risk gate: healthy, degraded, blocked, stale
- broker boundary: connected, disconnected, reconciling
- pending human work: approvals, incidents, kill-switch recoveries
- replay coverage: complete, partial, missing refs

Main panels:

- active workflow timeline
- pending approvals
- blocked proposals
- open incidents
- live event feed
- agent mesh health
- policy and schema registry health

## Workflow Detail Page

Every workflow page should be centered on a single canonical workflow ID.

Required sections:

- workflow envelope: objective, constraints, permitted tools, required agents, stop conditions, evaluation criteria
- state machine timeline: created, reasoning, planning, acting, observing, evaluating, refining, blocked, reconciling, completed
- phase steps: step ID, owner agent, input contract, output contract, allowed tools, latency, status
- trajectory logs: prompt version, tool calls, final state, artifact reference, model/provider, cost
- evaluation reports: rubric, score, verdict, target reference
- linked artifacts: proposal, risk decision, execution intent, receipt, incident, evidence, replay bundle

UI rule:

- users may inspect and approve transitions, but the UI must not synthesize allowed transitions client-side; it should render backend-provided allowed actions.

## Agent Runs Page

The backend now has enough agent runtime infrastructure that agent observability deserves a first-class view.

Required sections:

- active and recent agent sessions
- agent catalog: orchestrator, research, strategy, regime, risk governor, execution, compliance, portfolio, exposure, correlation, drawdown, volatility, slippage, monitoring
- tool policy matrix: agent to allowed MCP tools
- prompt provenance: prompt key, version, hash, active status
- output validation: passed, repaired, rejected
- runtime health: provider, model, latency, token or cost estimate, circuit breaker state

## Proposal To Execution Flow

The UI should show one continuous artifact chain:

`WorkflowIntent -> WorkflowPlan -> TradeHypothesis -> TradeProposal -> RiskAssessmentRequest -> RiskAssessmentDecision -> Approval -> ExecutionIntent -> ExecutionReceipt -> Reconciliation -> ReplayBundle`

Each artifact card should include:

- contract type and version
- reference ID
- authority state
- freshness state
- hash or manifest reference where available
- policy decision
- next backend-owned action

## Human Action Model

Mutation controls should be narrow and role-aware.

Allowed action patterns:

- create approval request
- cast approval vote
- acknowledge incident
- request override
- request kill-switch recovery
- cancel or pause workflow when backend says the transition is legal
- export replay or evidence package

Disallowed action patterns:

- direct broker mutation from UI
- client-side bypass of risk, policy, approval, or freshness gates
- client-generated execution intents without backend validation
- free-form agent tool calls outside a declared workflow

## API Surface Needed

Already present:

- `GET /api/operator`
- `GET /api/operator/health`
- `GET /api/operator/events/stream`
- `POST /api/operator/approvals/live-execution`
- `POST /api/operator/approvals/policy-change`
- `POST /api/operator/approvals/override`
- `POST /api/operator/approvals/kill-switch-recovery`
- `POST /api/operator/approvals/live-execution/{approval_id}/votes`
- legacy feature APIs under `/api/strategies`, `/api/backtest`, `/api/simulator`, `/api/live`, `/api/optimization`, `/api/edge-lab`, `/api/dashboard`

Needed for the frontend to become live-data-driven:

| Endpoint | Purpose |
|---|---|
| `GET /api/operator/dashboard` | Counts, health, authority posture, pending operator work |
| `GET /api/operator/workflows` | Workflow queue with state, owner, current step, linked refs |
| `GET /api/operator/workflows/{workflow_id}` | Workflow detail with steps, trajectory logs, evaluations |
| `GET /api/operator/agents` | Agent catalog, runtime status, policy profile |
| `GET /api/operator/agents/runs` | Recent agent executions, validation, cost, latency |
| `GET /api/operator/proposals` | Proposal queue and linked risk decisions |
| `GET /api/operator/risk-decisions` | Risk decisions, constraints, freshness, drift status |
| `GET /api/operator/execution-intents` | Execution readiness and approval state |
| `GET /api/operator/execution-receipts` | Attempts, receipts, reconciliation status |
| `GET /api/operator/approvals` | Approval queue and vote progress |
| `GET /api/operator/incidents` | Incident queue and allowed transitions |
| `GET /api/operator/evidence` | Evidence bundles and freshness |
| `GET /api/operator/replay-bundles` | Replay coverage, manifest, legal-hold/export status |
| `GET /api/operator/strategies/lifecycle` | Strategy lifecycle and promotion gates |

## Frontend Implementation Plan

Phase 1: make the existing operator workspace the default agentic UI shell.

- replace static scaffold text with backend-aligned status panels
- keep mock data behind typed frontend fixtures until read APIs exist
- add an agent runs route
- separate read-only inspection from mutation controls
- introduce a shared `operator-api.ts` client with consistent auth headers and fallback fixtures

Phase 2: connect read models.

- add backend read endpoints for dashboard, workflow queues, trajectory details, approvals, incidents, evidence, replay, and strategy lifecycle
- make all operator pages consume typed read models
- stream events through the existing SSE endpoint and reconcile them into page state

Phase 3: connect governed actions.

- wire approval creation and vote flows
- add incident acknowledgement and kill-switch recovery requests
- add replay and evidence export actions
- expose allowed transitions only from backend responses

Phase 4: migrate legacy views behind agentic workflows.

- strategy editor becomes strategy registry plus lifecycle view
- optimization becomes an agent-run-backed workflow detail
- live trading becomes execution control plus broker truth reconciliation
- performance reports become evidence artifacts linked to strategy lifecycle
- edge lab becomes research workflow creation and scorecard evidence

## Component Map

| Component | Responsibility |
|---|---|
| `OperatorShell` | Agentic control-plane navigation and authority posture |
| `OperatorOverviewPage` | Command center summary and event stream |
| `OperatorWorkflowView` | Workflow queue and selected workflow detail |
| `OperatorAgentRunsView` | Agent runtime health, tool policy, prompts, validation |
| `OperatorProposalRiskView` | Proposal queue and deterministic risk constraints |
| `OperatorApprovalView` | Approval queue and voting state |
| `OperatorIncidentView` | Incident queue and containment guidance |
| `OperatorReplayView` | Replay bundle inspection and export readiness |
| `OperatorEvidenceView` | Evidence bundles and lifecycle proof |
| `OperatorStrategyLifecycleView` | Strategy registry, promotion gates, envelopes |
| `OperatorAuthorityBadge` | Consistent visual treatment for authority states |
| `OperatorLiveEvents` | SSE stream from `/api/operator/events/stream` |

## Design Constraints

- Do not hide safety state behind charts.
- Every execution-bound row needs a contract ref and authority state.
- Every mutation button needs a visible backend-owned gate.
- Every agent output needs provenance, schema status, and linked artifacts.
- Every live action needs risk, approval, execution, receipt, and replay traceability.
- Legacy performance views should remain available, but they should be linked as evidence rather than presented as the command surface.
