# HaruQuant Agentic Firm UI Integration

**Purpose:** Define how the HaruQuant Next.js frontend observes, controls, reviews, and audits the full agentic trading firm without bypassing the CEO Agent, Planner, RiskGovernor, or deterministic service boundaries.

**Document type:** UI Integration Specification

**Applies to:** Next.js frontend, API routes, CEO chat runtime, agent task visibility, strategy lifecycle screens, simulation views, risk center, board approvals, audit, cost monitoring, and live/paper execution dashboards.

---

## 1. Goal

Make the full HaruQuant agentic firm observable and controllable from the Next.js frontend.

The UI must allow the user to:

- Chat with the CEO Agent.
- See what the internal Planner decided.
- Monitor agent tasks across departments.
- Review research, strategy specs, codegen, backtests, robustness, risk, portfolio, execution, audit, and cost outputs.
- Approve or reject governed actions.
- Understand why actions were blocked.
- Inspect evidence and audit trails.
- Operate the system like a trading firm instead of debugging logs manually.

The UI must not allow specialist agents to be called directly from casual chat. User requests enter through the CEO interface. The CEO Agent is the bridge between the user and all departments, and the internal Planner is used only by the CEO.

---

## 2. Core UI Architecture Rules

### 2.1 Chat and orchestration rule

- [ ] All user-facing agent workflows enter through the CEO Agent.
- [ ] The frontend must not call specialist agents directly from chat.
- [ ] The frontend must call `services/ceo_gateway.py` or its API equivalent for CEO conversations.
- [ ] The CEO Agent invokes its internal Planner.
- [ ] The Planner decides which department evidence is required.
- [ ] Specialist agents return structured outputs to the CEO workflow.
- [ ] CEO Agent synthesizes the final user-facing memo.
- [ ] UI displays specialist outputs as evidence, not as uncontrolled final decisions.

### 2.2 Deterministic-service rule

- [ ] UI must show when an output came from optional LLM reasoning.
- [ ] UI must show the deterministic decision result.
- [ ] UI must show policy version.
- [ ] UI must show prompt version where applicable.
- [ ] UI must show tools used.
- [ ] UI must show approval/rejection reasons.
- [ ] UI must show allowed actions.
- [ ] UI must show blocked actions.
- [ ] UI must preserve the distinction between:
  - LLM proposal
  - deterministic policy decision
  - CEO final memo
  - RiskGovernor approval token

### 2.3 Live trading safety rule

- [ ] UI must not expose direct live execution buttons unless governed workflow approval is present.
- [ ] UI must not send orders directly to MT5/cTrader.
- [ ] UI must route execution actions through Order Router.
- [ ] UI must require RiskGovernor approval token for live/paper order workflows.
- [ ] UI must display kill-switch status before any execution action.
- [ ] UI must block live activation actions if Board approval is missing.
- [ ] UI must display account mode clearly:
  - research
  - simulation
  - paper
  - micro-live
  - live
  - disabled

### 2.4 Evidence-first UI rule

- [ ] Every recommendation must show evidence references.
- [ ] Every approval request must show source reports.
- [ ] Every rejection must show deterministic reasons.
- [ ] Every risk block must show the relevant threshold and observed value.
- [ ] Every generated strategy must link to its research hypothesis.
- [ ] Every backtest must link to strategy spec version and code hash.
- [ ] Every portfolio decision must link to risk review and performance evidence.
- [ ] Every live execution must link to approval token and broker response.

---

## 3. UI Application Structure

Recommended Next.js app structure:

```text
apps/
  web/
    app/
      ai-ceo/
        page.tsx
        components/
      agents/
        page.tsx
        components/
      research/
        page.tsx
        components/
      strategy-lab/
        page.tsx
        components/
      backtests/
        page.tsx
        components/
      risk-center/
        page.tsx
        components/
      portfolio/
        page.tsx
        components/
      execution/
        page.tsx
        components/
      board-room/
        page.tsx
        components/
      audit/
        page.tsx
        components/
      costs/
        page.tsx
        components/
      settings/
        page.tsx
        components/

    components/
      agent/
      approvals/
      audit/
      charts/
      evidence/
      layout/
      risk/
      strategy/
      tables/
      timeline/

    lib/
      api/
      contracts/
      formatters/
      permissions/
      realtime/
      validators/

    types/
      agent.ts
      audit.ts
      backtest.ts
      evidence.ts
      portfolio.ts
      risk.ts
      strategy.ts
      workflow.ts
```

---

## 4. Shared UI Contracts

The UI should consume typed API contracts instead of loose dictionaries.

### 4.1 Agent response contract

- [ ] Add TypeScript type for `AgentResponse`.
- [ ] Add TypeScript type for `AgentDecision`.
- [ ] Add TypeScript type for `LLMAnalysis`.
- [ ] Add TypeScript type for `EvidenceItem`.
- [ ] Add TypeScript type for `AgentAudit`.
- [ ] Validate API responses with Zod or equivalent.
- [ ] Show schema validation errors in developer diagnostics.
- [ ] Never render malformed agent decisions as approved.

Recommended shape:

```ts
export type AgentStatus =
  | "success"
  | "rejected"
  | "needs_more_context"
  | "error";

export type ConfidenceLevel = "low" | "medium" | "high";

export type RiskLevel = "low" | "medium" | "high" | "critical";

export interface EvidenceItem {
  source: string;
  description: string;
  value?: unknown;
  confidence: ConfidenceLevel;
}

export interface LLMAnalysis {
  summary: string;
  observations: string[];
  risks: string[];
  suggestions: string[];
  raw_model_output?: string | null;
}

export interface AgentDecision {
  status: AgentStatus;
  decision: string;
  confidence: ConfidenceLevel;
  risk_level: RiskLevel;
  allowed_actions: string[];
  blocked_actions: string[];
  reasons: string[];
}

export interface AgentAudit {
  agent_name: string;
  prompt_version?: string;
  policy_version: string;
  llm_used: boolean;
  tools_used: string[];
  permission_profile: string;
  evidence_refs: string[];
  context_revision?: string;
  model_provider?: string;
  model_name?: string;
  fallback_used?: boolean;
}

export interface AgentResponse {
  request_id: string;
  agent_name: string;
  status: AgentStatus;
  evidence: EvidenceItem[];
  llm_analysis?: LLMAnalysis | null;
  decision: AgentDecision;
  artifacts: Record<string, unknown>;
  audit: AgentAudit;
}
```

### 4.2 Workflow task contract

- [ ] Add workflow ID.
- [ ] Add task ID.
- [ ] Add parent task ID.
- [ ] Add agent/service name.
- [ ] Add department.
- [ ] Add task title.
- [ ] Add status.
- [ ] Add priority.
- [ ] Add dependencies.
- [ ] Add started timestamp.
- [ ] Add completed timestamp.
- [ ] Add duration.
- [ ] Add cost.
- [ ] Add evidence references.
- [ ] Add output artifact references.
- [ ] Add error details.
- [ ] Add retry count.
- [ ] Add blocked reason.

Statuses:

```text
queued
planned
running
waiting_for_evidence
waiting_for_approval
blocked
failed
rejected
completed
cancelled
```

### 4.3 Approval request contract

- [ ] Add approval ID.
- [ ] Add requested action.
- [ ] Add requester agent.
- [ ] Add affected strategy.
- [ ] Add affected portfolio.
- [ ] Add risk level.
- [ ] Add evidence references.
- [ ] Add deterministic policy summary.
- [ ] Add RiskGovernor output if applicable.
- [ ] Add expiration time.
- [ ] Add approval status.
- [ ] Add approver.
- [ ] Add decision timestamp.
- [ ] Add audit trail.

Approval statuses:

```text
draft
pending_user
approved
rejected
expired
cancelled
blocked_by_risk
blocked_by_policy
```

---

## 5. API Integration Layer

### 5.1 Required frontend API clients

- [ ] Add `lib/api/ceoClient.ts`.
- [ ] Add `lib/api/workflowClient.ts`.
- [ ] Add `lib/api/evidenceClient.ts`.
- [ ] Add `lib/api/strategyClient.ts`.
- [ ] Add `lib/api/backtestClient.ts`.
- [ ] Add `lib/api/riskClient.ts`.
- [ ] Add `lib/api/portfolioClient.ts`.
- [ ] Add `lib/api/executionClient.ts`.
- [ ] Add `lib/api/auditClient.ts`.
- [ ] Add `lib/api/costClient.ts`.
- [ ] Add shared error handler.
- [ ] Add request ID propagation.
- [ ] Add trace ID propagation.
- [ ] Add auth/session context propagation.
- [ ] Add response validation.
- [ ] Add retry policy for read-only APIs.
- [ ] Add no-retry policy for governed writes.
- [ ] Add stale-data warnings.

### 5.2 Required backend endpoints

Recommended endpoint groups:

```text
POST   /api/ceo/chat
GET    /api/ceo/conversations/:conversation_id
GET    /api/workflows
GET    /api/workflows/:workflow_id
GET    /api/workflows/:workflow_id/tasks

GET    /api/evidence/:evidence_id
GET    /api/evidence/by-report/:report_id

GET    /api/strategies
GET    /api/strategies/:strategy_id
GET    /api/strategies/:strategy_id/specs
GET    /api/strategies/:strategy_id/code-versions
GET    /api/strategies/:strategy_id/reviews
GET    /api/strategies/:strategy_id/lifecycle

GET    /api/backtests
GET    /api/backtests/:run_id
GET    /api/backtests/:run_id/trades
GET    /api/backtests/:run_id/equity
GET    /api/backtests/:run_id/metrics
GET    /api/backtests/:run_id/report

GET    /api/risk/overview
GET    /api/risk/approvals
GET    /api/risk/blocks
GET    /api/risk/var-cvar
GET    /api/risk/correlation
GET    /api/risk/kill-switch

GET    /api/portfolio/overview
GET    /api/portfolio/allocations
GET    /api/portfolio/lifecycle
GET    /api/portfolio/recommendations

GET    /api/execution/readiness
GET    /api/execution/orders
GET    /api/execution/broker-health
GET    /api/execution/incidents

GET    /api/board/approval-queue
POST   /api/board/approvals/:approval_id/approve
POST   /api/board/approvals/:approval_id/reject

GET    /api/audit
GET    /api/audit/:audit_id

GET    /api/costs/summary
GET    /api/costs/by-agent
GET    /api/costs/by-workflow
```

### 5.3 Governed action API rules

- [ ] All governed write endpoints must require a request ID.
- [ ] All governed write endpoints must require a workflow ID.
- [ ] All governed write endpoints must require explicit user approval.
- [ ] All governed write endpoints must require server-side permission checks.
- [ ] UI must never rely on client-side blocking alone.
- [ ] Approval and rejection actions must write audit records.
- [ ] Live-trading enabling must require Board approval.
- [ ] Risk threshold changes must require separate governance flow.
- [ ] Kill-switch reset must require explicit human approval after critical incidents.

---

## 6. Page: `/ai-ceo`

### 6.1 Goal

Create the primary user interface for the agentic firm.

The `/ai-ceo` page is the main conversation surface where the user speaks to the CEO Agent. CEO handles final synthesis. The internal Planner can be displayed for transparency, but it is not directly callable.

### 6.2 Checklist

- [ ] Create `/ai-ceo`.
- [ ] Add CEO chat panel.
- [ ] Add message history.
- [ ] Add streaming response support.
- [ ] Add final CEO memo view.
- [ ] Add internal planner output panel.
- [ ] Add active task tree panel.
- [ ] Add evidence references panel.
- [ ] Add artifact links panel.
- [ ] Add approval requests panel.
- [ ] Add blocked actions panel.
- [ ] Add deterministic decision summary.
- [ ] Add risk level badge.
- [ ] Add confidence badge.
- [ ] Add model/provider metadata panel.
- [ ] Add prompt version display where available.
- [ ] Add policy version display.
- [ ] Add tools-used display.
- [ ] Add audit metadata drawer.
- [ ] Add copy/export memo action.
- [ ] Add link to related department pages.
- [ ] Add guarded approval controls.
- [ ] Add refusal/blocked response display.
- [ ] Add clarification request UI.
- [ ] Add workflow resume support.
- [ ] Add conversation trace ID.
- [ ] Add cost summary for the workflow.
- [ ] Add "why was this blocked?" explanation panel.

### 6.3 CEO chat layout

Recommended layout:

```text
/ai-ceo

Left:
- Conversation list
- Workflow filters

Center:
- CEO chat
- Final memo
- Clarification prompts

Right:
- Planner trace
- Task tree
- Evidence refs
- Approval queue
- Risk blocks
- Audit drawer
```

### 6.4 Planner transparency rules

- [ ] Show Planner output as internal reasoning summary, not as a user command interface.
- [ ] Show selected departments.
- [ ] Show selected specialist agents/services.
- [ ] Show missing inputs.
- [ ] Show planned backend tools.
- [ ] Show governed action drafts.
- [ ] Show risk level classification.
- [ ] Show why clarification was requested.
- [ ] Show why a request was refused or blocked.
- [ ] Do not allow user to directly edit Planner output into execution.
- [ ] Allow user to provide clarification that goes back to CEO.

### 6.5 Approval controls

- [ ] Show approval cards inside `/ai-ceo`.
- [ ] Require explicit approve/reject buttons.
- [ ] Show evidence bundle before approval.
- [ ] Show risk summary before approval.
- [ ] Show affected strategy/portfolio.
- [ ] Show expiry time.
- [ ] Show consequences.
- [ ] Disable approval if evidence is missing.
- [ ] Disable approval if RiskGovernor blocked the action.
- [ ] Disable approval if kill switch is active.
- [ ] Require confirmation phrase for critical approvals.
- [ ] Log all approval interactions.

---

## 7. Page: `/agents`

### 7.1 Goal

Show the operational state of all agentic workflows and deterministic services.

### 7.2 Checklist

- [ ] Create `/agents`.
- [ ] Show all departments.
- [ ] Show all agents/services.
- [ ] Show agent status.
- [ ] Show task status.
- [ ] Show task dependencies.
- [ ] Show running jobs.
- [ ] Show queued jobs.
- [ ] Show completed jobs.
- [ ] Show failed tasks.
- [ ] Show blocked tasks.
- [ ] Show rejected tasks.
- [ ] Show cost usage.
- [ ] Show model usage.
- [ ] Show tool usage.
- [ ] Show evidence count.
- [ ] Show average duration.
- [ ] Show last run time.
- [ ] Show policy version.
- [ ] Show prompt version.
- [ ] Show permission profile.
- [ ] Show health status.
- [ ] Show evaluator pass/fail state.
- [ ] Show retry count.
- [ ] Show failure reason.
- [ ] Show trace links.

### 7.3 Department groups

Display:

- [ ] Executive
- [ ] Research
- [ ] Strategy Creation
- [ ] Simulation
- [ ] Risk
- [ ] Portfolio
- [ ] Execution
- [ ] Audit
- [ ] Cost

### 7.4 Task board views

- [ ] Kanban view by status.
- [ ] DAG view by dependencies.
- [ ] Timeline view by execution order.
- [ ] Table view for filtering.
- [ ] Department view.
- [ ] Agent view.
- [ ] Workflow view.
- [ ] Cost view.
- [ ] Failure view.

### 7.5 Agent detail drawer

Each agent/service detail should show:

- [ ] Purpose.
- [ ] Department.
- [ ] Allowed actions.
- [ ] Blocked actions.
- [ ] Allowed tools.
- [ ] Permission profile.
- [ ] Last response.
- [ ] Recent runs.
- [ ] Audit metadata.
- [ ] Evaluator results.
- [ ] Open tasks.
- [ ] Failed tasks.
- [ ] Cost.
- [ ] Linked README.
- [ ] Test coverage status if available.

---

## 8. Page: `/research`

### 8.1 Goal

Review market intelligence, technical analysis, strategy scout output, macro context, seasonality, cross-asset analysis, and validated research hypotheses.

### 8.2 Checklist

- [ ] Create `/research`.
- [ ] Show research reports.
- [ ] Show market intelligence reports.
- [ ] Show technical analysis reports.
- [ ] Show strategy scout ideas.
- [ ] Show news/sentiment reports.
- [ ] Show macro/fundamental reports.
- [ ] Show cross-asset reports.
- [ ] Show seasonality reports.
- [ ] Show strategy hypotheses.
- [ ] Show research validation results.
- [ ] Show evidence quality.
- [ ] Show stale research warnings.
- [ ] Show report expiry.
- [ ] Show source reliability.
- [ ] Show candidate ideas.
- [ ] Show rejected ideas.
- [ ] Show recommended next steps.
- [ ] Link approved ideas to Strategy Lab.
- [ ] Link risk warnings to Risk Center.
- [ ] Link data issues to data management.
- [ ] Add filters by symbol/timeframe/asset class/strategy family.
- [ ] Add search by hypothesis ID.
- [ ] Add comparison between research reports.
- [ ] Add research lineage graph.

---

## 9. Page: `/strategy-lab`

### 9.1 Goal

Show strategy ideas, specs, generated code versions, reviews, lifecycle state, and handoffs from research to simulation.

### 9.2 Checklist

- [ ] Create `/strategy-lab`.
- [ ] Show strategy ideas.
- [ ] Show approved research hypotheses.
- [ ] Show strategy specs.
- [ ] Show spec versions.
- [ ] Show code versions.
- [ ] Show codegen output.
- [ ] Show strategy reviews.
- [ ] Show lifecycle status.
- [ ] Show strategy type:
  - simple
  - stateful
  - hybrid
- [ ] Show supported lifecycle:
  - `on_bar()`
  - `get_signal()`
  - `on_event()`
- [ ] Show required signal columns.
- [ ] Show event activator columns.
- [ ] Show parameter schema.
- [ ] Show risk-control compatibility.
- [ ] Show lookahead-bias review.
- [ ] Show tests generated.
- [ ] Show tests passed/failed.
- [ ] Show code hash.
- [ ] Show spec hash.
- [ ] Show linked research evidence.
- [ ] Show linked backtests.
- [ ] Show linked risk reviews.
- [ ] Show linked portfolio decisions.
- [ ] Show strategy lineage.
- [ ] Allow request to create strategy via CEO.
- [ ] Allow request to revise spec via CEO.
- [ ] Allow request to generate code via CEO.
- [ ] Allow request to review strategy via CEO.
- [ ] Do not call Strategy Creator/Codegen/Reviewer directly from UI chat.

### 9.3 Strategy detail tabs

Recommended tabs:

- [ ] Overview
- [ ] Research Evidence
- [ ] Specification
- [ ] Generated Code
- [ ] Review
- [ ] Parameters
- [ ] Risk Controls
- [ ] Tests
- [ ] Backtests
- [ ] Robustness
- [ ] Lifecycle
- [ ] Audit

### 9.4 Lifecycle states

Display lifecycle states:

```text
idea
research_validated
spec_draft
spec_validated
code_generated
code_reviewed
ready_for_backtest
backtested
diagnosed
optimized
robustness_tested
statistically_validated
risk_reviewed
admitted_to_paper
paper_trading
micro_live_candidate
micro_live
live_candidate
live
paused
retired
rejected
```

---

## 10. Page: `/backtests`

### 10.1 Goal

Show reproducible simulation evidence packages and strategy behavior diagnostics.

### 10.2 Checklist

- [ ] Create `/backtests`.
- [ ] Show backtest runs.
- [ ] Show run ID.
- [ ] Show strategy ID.
- [ ] Show strategy spec version.
- [ ] Show strategy code hash.
- [ ] Show data version.
- [ ] Show config hash.
- [ ] Show period.
- [ ] Show symbol/timeframe.
- [ ] Show execution mode.
- [ ] Show spread/slippage/commission assumptions.
- [ ] Show initial balance.
- [ ] Show final balance/equity.
- [ ] Show trades.
- [ ] Show orders.
- [ ] Show deals.
- [ ] Show equity curve.
- [ ] Show drawdown curve.
- [ ] Show monthly returns.
- [ ] Show period analysis.
- [ ] Show long/short split.
- [ ] Show session performance.
- [ ] Show regime performance.
- [ ] Show cost sensitivity.
- [ ] Show benchmark comparison.
- [ ] Show statistical tests.
- [ ] Show acceptance result.
- [ ] Show rejection reasons.
- [ ] Show diagnosis report.
- [ ] Show immutable run package links.
- [ ] Show audit metadata.

### 10.3 Required charts

- [ ] Equity curve.
- [ ] Drawdown curve.
- [ ] Monthly returns heatmap.
- [ ] Trade P&L distribution.
- [ ] R-multiple distribution.
- [ ] Long vs short comparison.
- [ ] Session performance.
- [ ] Hour-of-day performance.
- [ ] Day-of-week performance.
- [ ] Regime performance.
- [ ] Rolling Sharpe/Sortino.
- [ ] Rolling drawdown.
- [ ] Cumulative cost impact.
- [ ] Benchmark comparison.

### 10.4 Run detail tabs

- [ ] Summary
- [ ] Metrics
- [ ] Trades
- [ ] Orders
- [ ] Deals
- [ ] Equity
- [ ] Drawdowns
- [ ] Returns
- [ ] Ratios
- [ ] Risks
- [ ] Efficiency
- [ ] Distributions
- [ ] Benchmark
- [ ] Statistical Tests
- [ ] Diagnosis
- [ ] Audit

---

## 11. Page: `/risk-center`

### 11.1 Goal

Show current and historical risk state, RiskGovernor decisions, exposure, drawdown, VaR/CVaR, kill switch, and approval-token activity.

### 11.2 Checklist

- [ ] Create `/risk-center`.
- [ ] Show portfolio exposure.
- [ ] Show symbol exposure.
- [ ] Show currency-cluster exposure.
- [ ] Show strategy exposure.
- [ ] Show VaR.
- [ ] Show CVaR.
- [ ] Show correlation matrix.
- [ ] Show concentration risk.
- [ ] Show margin usage.
- [ ] Show drawdown state.
- [ ] Show daily loss state.
- [ ] Show weekly loss state.
- [ ] Show open positions.
- [ ] Show RiskGovernor approvals.
- [ ] Show RiskGovernor blocks.
- [ ] Show risk approval tokens.
- [ ] Show token expiration.
- [ ] Show token hash/signature status.
- [ ] Show risk config version hash.
- [ ] Show risk threshold table.
- [ ] Show risk policy status.
- [ ] Show kill-switch status.
- [ ] Show broker anomaly blocks.
- [ ] Show news blocks.
- [ ] Show spread/slippage blocks.
- [ ] Show blocked action reasons.
- [ ] Show risk memo history.
- [ ] Show risk-review recommendations.
- [ ] Show risk audit failures.
- [ ] Show risk health summary.

### 11.3 Risk drilldowns

- [ ] Exposure by symbol.
- [ ] Exposure by currency.
- [ ] Exposure by strategy.
- [ ] Exposure by asset class.
- [ ] Exposure by correlation cluster.
- [ ] Exposure by session.
- [ ] Risk contribution by strategy.
- [ ] Risk contribution by symbol.
- [ ] Drawdown attribution.
- [ ] Daily loss attribution.
- [ ] Margin impact by trade proposal.
- [ ] VaR impact by trade proposal.
- [ ] CVaR impact by trade proposal.

### 11.4 Risk action controls

- [ ] Allow request for risk review through CEO.
- [ ] Allow request for risk memo through CEO.
- [ ] Allow request for portfolio impact analysis through CEO.
- [ ] Do not allow direct RiskGovernor override.
- [ ] Do not allow client-side risk threshold changes.
- [ ] Do not allow direct approval-token creation from UI.
- [ ] Require governed workflow for risk config changes.
- [ ] Require Board approval for risk threshold changes.

---

## 12. Page: `/portfolio`

### 12.1 Goal

Manage strategy lifecycle, allocation recommendations, portfolio composition, and promotion/demotion evidence.

### 12.2 Checklist

- [ ] Create `/portfolio`.
- [ ] Show live strategies.
- [ ] Show paper strategies.
- [ ] Show retired strategies.
- [ ] Show rejected strategies.
- [ ] Show strategy lifecycle table.
- [ ] Show allocation table.
- [ ] Show capital allocation by strategy.
- [ ] Show capital allocation by symbol.
- [ ] Show risk allocation by strategy.
- [ ] Show paper trading performance.
- [ ] Show live trading performance.
- [ ] Show correlation clusters.
- [ ] Show diversification score.
- [ ] Show allocation limits.
- [ ] Show RiskGovernor constraints.
- [ ] Show portfolio manager recommendations.
- [ ] Show promotion candidates.
- [ ] Show demotion candidates.
- [ ] Show pause candidates.
- [ ] Show retirement candidates.
- [ ] Show required Board approvals.
- [ ] Show portfolio decision history.
- [ ] Show decision evidence bundle.

### 12.3 Portfolio decision types

Display and support governed requests for:

- [ ] `admit_to_paper`
- [ ] `reject_strategy`
- [ ] `promote_to_micro_live`
- [ ] `increase_allocation`
- [ ] `decrease_allocation`
- [ ] `pause_strategy`
- [ ] `retire_strategy`

### 12.4 Allocation views

- [ ] Capital allocation view.
- [ ] Risk allocation view.
- [ ] Strategy family allocation view.
- [ ] Symbol exposure view.
- [ ] Currency exposure view.
- [ ] Correlation cluster view.
- [ ] Drawdown contribution view.
- [ ] Performance contribution view.
- [ ] Cost contribution view.

---

## 13. Page: `/execution`

### 13.1 Goal

Observe paper/live execution readiness, order routing, broker bridges, execution anomalies, and incident handling.

### 13.2 Checklist

- [ ] Create `/execution`.
- [ ] Show execution mode.
- [ ] Show live mode enabled/disabled.
- [ ] Show paper mode status.
- [ ] Show approved live strategies.
- [ ] Show strategy signal feed.
- [ ] Show trade proposals.
- [ ] Show RiskGovernor approval checks.
- [ ] Show approval-token validation.
- [ ] Show order router decisions.
- [ ] Show broker bridge status.
- [ ] Show MT5 heartbeat.
- [ ] Show cTrader heartbeat.
- [ ] Show broker account info.
- [ ] Show symbol info.
- [ ] Show latest ticks.
- [ ] Show open positions.
- [ ] Show pending orders.
- [ ] Show order requests.
- [ ] Show broker responses.
- [ ] Show slippage.
- [ ] Show spread.
- [ ] Show execution anomalies.
- [ ] Show rejected orders.
- [ ] Show incident reports.
- [ ] Show kill-switch status.
- [ ] Show audit logging status.
- [ ] Show RiskGovernor health.
- [ ] Show broker connection health.

### 13.3 Execution safety indicators

- [ ] Live mode state.
- [ ] Board approval state.
- [ ] Strategy live status.
- [ ] RiskGovernor availability.
- [ ] Approval token state.
- [ ] Kill switch state.
- [ ] Broker heartbeat state.
- [ ] Spread state.
- [ ] Slippage state.
- [ ] Audit logger state.
- [ ] Order router state.

### 13.4 Execution action restrictions

- [ ] No direct order placement from UI unless routed through governed workflow.
- [ ] No direct broker bridge calls from UI.
- [ ] No direct strategy live activation from UI.
- [ ] No direct kill-switch reset after critical incident.
- [ ] No direct approval-token creation.
- [ ] No direct RiskGovernor override.
- [ ] All execution actions require server-side enforcement.

---

## 14. Page: `/board-room`

### 14.1 Goal

Provide a decision room for approvals, live activation requests, allocation changes, incidents, and weekly/monthly firm reports.

### 14.2 Checklist

- [ ] Create `/board-room`.
- [ ] Show weekly reports.
- [ ] Show monthly reports.
- [ ] Show approval queue.
- [ ] Show approval history.
- [ ] Show live activation requests.
- [ ] Show allocation requests.
- [ ] Show strategy promotion requests.
- [ ] Show strategy pause requests.
- [ ] Show strategy retirement requests.
- [ ] Show risk threshold change requests.
- [ ] Show incident reports.
- [ ] Show kill-switch reset requests.
- [ ] Show cost reports.
- [ ] Show audit reports.
- [ ] Show decisions required from user.
- [ ] Show expired requests.
- [ ] Show blocked-by-risk requests.
- [ ] Show rejected requests.
- [ ] Show evidence bundles.
- [ ] Show CEO recommendation.
- [ ] Show RiskGovernor output.
- [ ] Show Portfolio Manager recommendation.
- [ ] Show audit status.
- [ ] Show final approval controls.

### 14.3 Board approval request card

Each card must include:

- [ ] Request ID.
- [ ] Request type.
- [ ] Requested action.
- [ ] Requesting agent/service.
- [ ] CEO summary.
- [ ] Evidence bundle.
- [ ] Risk summary.
- [ ] Portfolio impact.
- [ ] Expected benefit.
- [ ] Worst-case risk.
- [ ] Rejection impact.
- [ ] Expiration time.
- [ ] Required approval level.
- [ ] Deterministic policy status.
- [ ] Audit metadata.
- [ ] Approve button.
- [ ] Reject button.
- [ ] Ask CEO for clarification action.

### 14.4 Approval levels

- [ ] Low-risk approval.
- [ ] Strategy spec approval.
- [ ] Backtest launch approval.
- [ ] Paper admission approval.
- [ ] Micro-live promotion approval.
- [ ] Live activation approval.
- [ ] Allocation increase approval.
- [ ] Risk policy change approval.
- [ ] Kill-switch reset approval.
- [ ] Critical incident recovery approval.

---

## 15. Page: `/audit`

### 15.1 Goal

Continuously verify that the system obeys its own rules and make violations visible.

### 15.2 Checklist

- [ ] Create `/audit`.
- [ ] Show daily audit report.
- [ ] Show audit findings.
- [ ] Show audit severity.
- [ ] Show critical failures.
- [ ] Show every live order approval link.
- [ ] Show approval-token/order matching status.
- [ ] Show risk-threshold modification checks.
- [ ] Show strategy lifecycle compliance checks.
- [ ] Show Board approval checks.
- [ ] Show evidence reference completeness.
- [ ] Show execution log completeness.
- [ ] Show broker response completeness.
- [ ] Show failed tool calls.
- [ ] Show hidden errors.
- [ ] Show missing audit logs.
- [ ] Show permission violations.
- [ ] Show prompt/policy version drift.
- [ ] Show model routing violations.
- [ ] Show evaluator failures.
- [ ] Show incident audit trail.
- [ ] Show live trading disabled reason when critical.
- [ ] Show export audit report.

### 15.3 Audit severity

Display severity levels:

```text
info
warning
major
critical
```

### 15.4 Critical audit behavior

- [ ] Critical audit failure disables live trading.
- [ ] UI must show global live-disabled banner.
- [ ] UI must show root cause.
- [ ] UI must show required remediation.
- [ ] UI must route reset request through Board Room.
- [ ] UI must not allow hidden override.

---

## 16. Page: `/costs`

### 16.1 Goal

Track model, workflow, backtest, infrastructure, and agent cost.

### 16.2 Checklist

- [ ] Create `/costs`.
- [ ] Show daily cost.
- [ ] Show weekly cost.
- [ ] Show monthly cost.
- [ ] Show cost by agent.
- [ ] Show cost by department.
- [ ] Show cost by workflow.
- [ ] Show cost by strategy.
- [ ] Show cost by model provider.
- [ ] Show cost by model name.
- [ ] Show prompt tokens.
- [ ] Show completion tokens.
- [ ] Show failed-call cost.
- [ ] Show backtest compute cost.
- [ ] Show optimization compute cost.
- [ ] Show cost per accepted strategy.
- [ ] Show cost per rejected strategy.
- [ ] Show cost per paper candidate.
- [ ] Show cost per live candidate.
- [ ] Show cost anomalies.
- [ ] Show model routing decisions.
- [ ] Show recommended cost optimizations.
- [ ] Show budget usage.
- [ ] Show budget alerts.

### 16.3 Cost controls

- [ ] Show model routing policy.
- [ ] Show strong-model usage.
- [ ] Show cheap-model usage.
- [ ] Show local-model usage.
- [ ] Show no-LLM deterministic decisions.
- [ ] Show cost cap status.
- [ ] Show workflow cost estimate before launching expensive jobs.
- [ ] Require approval for high-cost optimization batches.
- [ ] Require approval for large robustness runs.
- [ ] Never allow cost optimization to weaken RiskGovernor or execution safety.

---

## 17. Page: `/settings`

### 17.1 Goal

Expose safe configuration views while keeping dangerous changes governed.

### 17.2 Checklist

- [ ] Create `/settings`.
- [ ] Show read-only risk policy summary.
- [ ] Show read-only model routing policy.
- [ ] Show read-only tool permission policy.
- [ ] Show read-only execution mode.
- [ ] Show read-only broker bridge config.
- [ ] Show read-only data paths.
- [ ] Show read-only strategy lifecycle rules.
- [ ] Show read-only Board approval policy.
- [ ] Show read-only cost budget policy.
- [ ] Show current environment.
- [ ] Show config version hashes.
- [ ] Show policy version hashes.
- [ ] Show last modified timestamps.
- [ ] Show safe UI preferences.
- [ ] Route governed config changes through CEO/Board.
- [ ] Do not allow direct client-side policy edits.

---

## 18. Global Navigation

### 18.1 Required navigation groups

- [ ] AI CEO
- [ ] Agents
- [ ] Research
- [ ] Strategy Lab
- [ ] Backtests
- [ ] Risk Center
- [ ] Portfolio
- [ ] Execution
- [ ] Board Room
- [ ] Audit
- [ ] Costs
- [ ] Settings

### 18.2 Global status bar

Show:

- [ ] Environment.
- [ ] Execution mode.
- [ ] Live enabled/disabled.
- [ ] Kill-switch status.
- [ ] RiskGovernor status.
- [ ] Broker heartbeat.
- [ ] Audit status.
- [ ] Current drawdown.
- [ ] Daily P&L.
- [ ] Open exposure.
- [ ] Active workflow count.
- [ ] Pending approvals.
- [ ] Critical alerts.
- [ ] Current user/session.

### 18.3 Global alert banner

Show alerts for:

- [ ] Kill switch triggered.
- [ ] Critical audit failure.
- [ ] RiskGovernor unavailable.
- [ ] Broker heartbeat failed.
- [ ] Audit logging unavailable.
- [ ] Live mode disabled.
- [ ] Approval required.
- [ ] Expiring approval token.
- [ ] Stale data.
- [ ] High cost anomaly.
- [ ] Failed workflow.
- [ ] Repeated execution failure.

---

## 19. Evidence UI Components

### 19.1 Evidence card

- [ ] Evidence ID.
- [ ] Source type.
- [ ] Source name.
- [ ] Description.
- [ ] Confidence.
- [ ] Reliability score.
- [ ] Freshness score.
- [ ] Retrieved timestamp.
- [ ] Published timestamp if applicable.
- [ ] Claim supported.
- [ ] Used by reports.
- [ ] Used by decisions.
- [ ] Expiry date.
- [ ] Contradiction flag.

### 19.2 Evidence bundle

- [ ] Group evidence by report.
- [ ] Group evidence by department.
- [ ] Group evidence by decision.
- [ ] Show supporting evidence.
- [ ] Show contradicting evidence.
- [ ] Show missing evidence.
- [ ] Show stale evidence.
- [ ] Show evidence lineage.
- [ ] Show open source/details drawer.

### 19.3 Evidence graph

- [ ] Strategy idea to research report.
- [ ] Research report to evidence.
- [ ] Strategy spec to research idea.
- [ ] Code version to spec.
- [ ] Backtest to code hash.
- [ ] Risk review to backtest/robustness.
- [ ] Portfolio decision to risk review.
- [ ] Execution order to approval token.
- [ ] Audit finding to affected object.

---

## 20. Approval UI Components

### 20.1 Approval card

- [ ] Status badge.
- [ ] Risk badge.
- [ ] Request type.
- [ ] Requested action.
- [ ] Affected object.
- [ ] CEO recommendation.
- [ ] RiskGovernor status.
- [ ] Evidence count.
- [ ] Expiration time.
- [ ] Approve/reject controls.
- [ ] Ask CEO for explanation action.
- [ ] View evidence action.
- [ ] View audit action.

### 20.2 Approval guardrails

- [ ] Disable approval if request expired.
- [ ] Disable approval if blocked by RiskGovernor.
- [ ] Disable approval if evidence missing.
- [ ] Disable approval if audit failed.
- [ ] Disable approval if kill switch active.
- [ ] Disable approval if user lacks permission.
- [ ] Require confirmation for live trading actions.
- [ ] Require reason when rejecting.
- [ ] Write audit event for every decision.

---

## 21. Agent Task Components

### 21.1 Task tree

- [ ] Show root workflow.
- [ ] Show child tasks.
- [ ] Show dependencies.
- [ ] Show status.
- [ ] Show agent/service.
- [ ] Show duration.
- [ ] Show cost.
- [ ] Show evidence output.
- [ ] Show artifact output.
- [ ] Show failure reason.
- [ ] Show retry action for safe tasks.
- [ ] Disable retry for governed write tasks unless approved.

### 21.2 Task timeline

- [ ] Show planning phase.
- [ ] Show evidence-gathering phase.
- [ ] Show LLM-analysis phase.
- [ ] Show deterministic-policy phase.
- [ ] Show audit phase.
- [ ] Show evaluator phase.
- [ ] Show final synthesis phase.
- [ ] Show approval phase.
- [ ] Show execution phase if applicable.

---

## 22. Real-Time Updates

### 22.1 Streaming and events

- [ ] Add WebSocket or Server-Sent Events for workflow updates.
- [ ] Stream CEO responses.
- [ ] Stream task status changes.
- [ ] Stream approval status changes.
- [ ] Stream risk alerts.
- [ ] Stream kill-switch events.
- [ ] Stream broker heartbeat changes.
- [ ] Stream paper/live execution events.
- [ ] Stream audit-critical events.
- [ ] Stream cost anomalies.

### 22.2 Realtime safety rules

- [ ] Realtime UI is display-only unless routed through governed API.
- [ ] Never execute client-side actions directly from realtime events.
- [ ] Show stale connection warning.
- [ ] Show reconnect state.
- [ ] Show last update timestamp.
- [ ] Fail closed on missing live safety state.

---

## 23. Authentication and Permissions

### 23.1 User permission groups

Recommended groups:

```text
viewer
research_operator
strategy_operator
simulation_operator
risk_viewer
portfolio_operator
board_approver
admin
```

### 23.2 Permission matrix

- [ ] View CEO chat.
- [ ] Start research workflow.
- [ ] Start strategy creation workflow.
- [ ] Start backtest workflow.
- [ ] Start optimization workflow.
- [ ] Start robustness workflow.
- [ ] View risk details.
- [ ] Request risk review.
- [ ] Approve Board actions.
- [ ] Approve live activation.
- [ ] Reset kill switch.
- [ ] Change config via governed workflow.
- [ ] View audit logs.
- [ ] Export reports.

### 23.3 Security requirements

- [ ] Server-side authorization on every governed endpoint.
- [ ] No secrets in frontend.
- [ ] No broker credentials in frontend.
- [ ] No provider API keys in frontend.
- [ ] No direct database mutation from frontend.
- [ ] No direct execution bridge calls from frontend.
- [ ] CSRF protection for approval actions.
- [ ] Confirmation for critical actions.
- [ ] Immutable audit trail for approvals.
- [ ] Session timeout handling.
- [ ] Read-only fallback if permission state is unavailable.

---

## 24. Data Freshness and Reproducibility

### 24.1 Freshness indicators

- [ ] Show last updated timestamp.
- [ ] Show data source.
- [ ] Show stale-data warning.
- [ ] Show snapshot ID.
- [ ] Show data version.
- [ ] Show config hash.
- [ ] Show strategy code hash.
- [ ] Show risk config hash.
- [ ] Show policy version hash.
- [ ] Show reproducibility status.

### 24.2 Immutable artifact links

- [ ] Link to strategy spec version.
- [ ] Link to generated code version.
- [ ] Link to backtest run package.
- [ ] Link to robustness package.
- [ ] Link to statistical validation package.
- [ ] Link to risk memo.
- [ ] Link to portfolio decision memo.
- [ ] Link to approval token.
- [ ] Link to execution audit.
- [ ] Link to incident report.

---

## 25. Error Handling

### 25.1 Error states

- [ ] API unavailable.
- [ ] CEO gateway unavailable.
- [ ] Planner unavailable.
- [ ] Specialist service unavailable.
- [ ] RiskGovernor unavailable.
- [ ] Broker bridge unavailable.
- [ ] Audit logger unavailable.
- [ ] Evidence missing.
- [ ] Data stale.
- [ ] Permission denied.
- [ ] Approval expired.
- [ ] Token mismatch.
- [ ] Config hash mismatch.
- [ ] Workflow failed.
- [ ] Evaluator failed.
- [ ] Unknown error.

### 25.2 Error UI requirements

- [ ] Show user-friendly error.
- [ ] Show technical details drawer.
- [ ] Show request ID.
- [ ] Show trace ID.
- [ ] Show affected workflow.
- [ ] Show retry option only for safe read-only operations.
- [ ] Show escalation path.
- [ ] Show blocked action reason.
- [ ] Never hide critical failures.
- [ ] Never allow live actions when safety state is unknown.

---

## 26. Reporting and Export

### 26.1 Export formats

- [ ] Markdown.
- [ ] PDF.
- [ ] JSON.
- [ ] CSV for tables.
- [ ] Parquet links for datasets.
- [ ] PNG/SVG for charts.

### 26.2 Exportable reports

- [ ] CEO final memo.
- [ ] Research report.
- [ ] Strategy specification.
- [ ] Strategy review.
- [ ] Backtest report.
- [ ] Robustness report.
- [ ] Statistical validation report.
- [ ] Risk memo.
- [ ] Portfolio report.
- [ ] Board approval package.
- [ ] Incident report.
- [ ] Audit report.
- [ ] Cost report.

### 26.3 Export rules

- [ ] Exports must include report ID.
- [ ] Exports must include timestamp.
- [ ] Exports must include config hashes where applicable.
- [ ] Exports must include evidence references.
- [ ] Exports must include audit metadata.
- [ ] Exports must exclude secrets.
- [ ] Exports must preserve immutable artifact references.

---

## 27. Testing Requirements

### 27.1 Frontend tests

- [ ] Unit tests for API clients.
- [ ] Unit tests for type validators.
- [ ] Unit tests for evidence components.
- [ ] Unit tests for approval components.
- [ ] Unit tests for risk badges.
- [ ] Unit tests for task tree.
- [ ] Unit tests for audit drawer.
- [ ] Unit tests for cost components.
- [ ] Component tests for all pages.
- [ ] Integration tests for CEO chat.
- [ ] Integration tests for approval flow.
- [ ] Integration tests for blocked-by-risk flow.
- [ ] Integration tests for stale-data warnings.
- [ ] Integration tests for permission-denied states.
- [ ] E2E tests for research-to-strategy flow.
- [ ] E2E tests for strategy-to-backtest flow.
- [ ] E2E tests for backtest-to-risk-review flow.
- [ ] E2E tests for paper admission approval.
- [ ] E2E tests for live activation blocked without approval.
- [ ] E2E tests for kill-switch triggered state.
- [ ] E2E tests for audit-critical disables live trading.

### 27.2 Required test cases

- [ ] CEO chat returns final memo.
- [ ] Planner output is visible but not directly executable.
- [ ] Specialist agent output appears as evidence.
- [ ] Approval cannot proceed without evidence.
- [ ] Approval cannot proceed when blocked by RiskGovernor.
- [ ] Live execution controls are hidden or disabled without permission.
- [ ] Kill switch disables execution controls.
- [ ] Audit critical banner appears globally.
- [ ] Stale data warning appears on risk and execution pages.
- [ ] Cost anomaly appears in global alert banner.
- [ ] Broken API shows request ID and safe error.
- [ ] User cannot bypass server-side governed action checks.

---

## 28. Observability and Telemetry

### 28.1 UI telemetry

- [ ] Track page loads.
- [ ] Track API latency.
- [ ] Track failed requests.
- [ ] Track approval interactions.
- [ ] Track blocked interactions.
- [ ] Track user clarifications.
- [ ] Track export actions.
- [ ] Track workflow launches.
- [ ] Track chart load failures.
- [ ] Track stale data occurrences.

### 28.2 Trading safety telemetry

- [ ] Track live-mode visibility.
- [ ] Track execution button render state.
- [ ] Track kill-switch banner display.
- [ ] Track RiskGovernor unavailable display.
- [ ] Track approval disabled reasons.
- [ ] Track policy mismatch warnings.
- [ ] Track token mismatch warnings.

### 28.3 Telemetry rules

- [ ] Do not log secrets.
- [ ] Do not log full broker credentials.
- [ ] Do not log provider API keys.
- [ ] Do not log raw private account values unless explicitly allowed.
- [ ] Preserve request ID and trace ID.
- [ ] Link UI telemetry to backend audit where applicable.

---

## 29. Implementation Build Order

Build in this order:

```text
1. Shared UI contracts and API client layer
2. Global layout, navigation, status bar, and alert banner
3. /ai-ceo page
4. Workflow/task tree components
5. Evidence components
6. Approval components
7. /agents page
8. /research page
9. /strategy-lab page
10. /backtests page
11. /risk-center page
12. /portfolio page
13. /execution page
14. /board-room page
15. /audit page
16. /costs page
17. /settings page
18. Realtime updates
19. Permission and governed-action hardening
20. Full E2E safety tests
```

---

## 30. UI Definition of Done

The UI integration is complete only when:

```text
1. User can interact with the firm through /ai-ceo.
2. CEO is the only chat-facing bridge to departments.
3. Planner is visible for transparency but not independently callable.
4. Agent tasks are observable from /agents.
5. Research evidence is visible and linked.
6. Strategy specs, code versions, reviews, and lifecycle states are visible.
7. Backtest result packages are visible and reproducible.
8. RiskGovernor approvals, blocks, VaR/CVaR, exposure, and kill switch are visible.
9. Portfolio lifecycle and allocation recommendations are visible.
10. Paper/live execution readiness is visible.
11. Board approvals are visible and governed.
12. Audit failures are visible and can disable live trading.
13. Cost usage is visible by agent, workflow, strategy, and model.
14. All governed actions are server-side enforced.
15. UI cannot bypass RiskGovernor, Order Router, Kill Switch, Board approval, or audit.
16. All pages show request IDs, trace IDs, and evidence links where relevant.
17. E2E tests prove that unsafe live actions are blocked.
```

---

## 31. Final Architecture Rule

```text
The frontend observes and requests governed workflows.
It does not directly command specialist agents, RiskGovernor, broker bridges, or execution.
CEO Agent is the user-facing bridge.
Deterministic services remain the final authority for risk, approvals, execution safety, audit, and lifecycle gates.
```
