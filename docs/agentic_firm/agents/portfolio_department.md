# HaruQuant Agentic AI System — Portfolio Department

## Goal

Manage the portfolio of strategies, paper/live allocation, execution readiness, operational safety, reporting, audit, and cost governance through production-grade deterministic services and optional LLM-assisted agents.

The Portfolio Department must manage HaruQuant like a trading firm, not like isolated strategy scripts. It decides what strategies are allowed into paper trading, which strategies may be promoted, which allocations should change, which strategies should be paused or retired, and whether the execution environment is healthy enough to continue operating.

## Dependency

Research Department, Strategy Creation Department, Simulation Department, and Risk Department must provide the evidence required for portfolio decisions.

At minimum, the Portfolio Department depends on:

```text
Research reports
Strategy specifications
Generated strategy code
Strategy reviews
Backtest result packages
Backtest diagnosis reports
Optimization comparison reports
Robustness reports
Statistical validation reports
RiskGovernor outputs
Risk memos
Strategy lifecycle table
Paper trading performance
Live trading performance
Execution logs
Audit logs
Cost logs
```

## Core Operating Rule

All agents and services in this department must follow the HaruQuant agent template execution pattern:

```text
Validate Input
-> Gather Evidence / Context
-> Optional LLM Reasoning
-> Deterministic Policy Decision
-> Structured Output
-> Audit Log
-> Evaluation Test
```

The LLM may summarize, classify, compare, explain, rank, or draft reports. It must not make final uncontrolled decisions.

```text
LLM output = proposal
Deterministic policy = final decision
```

## Portfolio Department Hard Restrictions

```text
No portfolio agent may bypass RiskGovernor.
No live order may execute without a valid RiskGovernor approval token.
No live strategy allocation change may happen without Board approval.
No specialist agent may directly change risk thresholds.
No agent may directly modify broker state except the approved Execution Bridge.
No live trading resume may happen after a critical incident without explicit approval.
No execution may proceed if audit logging is unavailable.
No execution may proceed if kill switch is triggered.
```

---

# 1. Department Folder Structure

## Checklist

* [x] Create `agents/portfolio/`.
* [x] Create `agents/portfolio/portfolio_orchestrator_agent/`.
* [x] Create `agents/portfolio/portfolio_manager_agent/`.
* [x] Create `agents/portfolio/allocation_optimizer_agent/`.
* [x] Create `agents/portfolio/strategy_lifecycle_agent/`.
* [x] Create `agents/portfolio/paper_execution_agent/`.
* [x] Create `agents/portfolio/live_execution_agent/`.
* [x] Create `agents/portfolio/execution_readiness_agent/`.
* [x] Create `agents/portfolio/performance_reporter_agent/`.
* [x] Create `agents/portfolio/cost_optimizer_agent/`.
* [x] Create `agents/portfolio/shared/`.
* [x] Create `services/portfolio/`.
* [x] Create `services/portfolio/paper_broker.py`.
* [x] Create `services/portfolio/order_router.py`.
* [x] Create `services/portfolio/kill_switch.py`.
* [x] Create `services/portfolio/incident_service.py`.
* [x] Create `services/portfolio/lifecycle_service.py`.
* [x] Create `services/portfolio/allocation_service.py`.
* [x] Create `services/portfolio/reporting_service.py`.
* [x] Create `services/portfolio/cost_service.py`.
* [x] Create `services/execution/`.
* [x] Create `services/execution/bridges/`.
* [x] Create `services/execution/bridges/mt5_bridge.py`.
* [x] Create `services/execution/bridges/ctrader_bridge.py`.
* [x] Create `services/execution/bridges/base_bridge.py`.
* [x] Create `agents/audit/audit_agent/`.
* [x] Create `agents/audit/shared/`.

## Required Structure Per Agent

Each agent folder must contain:

```text
__init__.py
agent.py
contracts.py
prompts.py
deterministic_policy.py
tools.py
service.py
evaluator.py
README.md
tests/
  test_contracts.py
  test_deterministic_policy.py
  test_service.py
  test_agent_smoke.py
```

## Done Definition

The Portfolio Department has a clean folder structure that follows the same agent template used by Research, Strategy Creation, Simulation, and Risk.

---

# 2. Portfolio Department Orchestrator Agent

## Goal

Coordinate portfolio-level decisions across strategy lifecycle, allocation, execution state, risk evidence, reporting, audit, and cost governance.

## Purpose

The Portfolio Orchestrator Agent receives portfolio-level requests and determines which portfolio agents/services must be called. It does not directly execute trades, approve risk, or modify allocations. It coordinates evidence and routes recommendations to the CEO Agent, Planner Agent, Board workflow, or deterministic services.

## Folder

```text
agents/portfolio/portfolio_orchestrator_agent/
```

## Checklist

* [x] Create `agents/portfolio/portfolio_orchestrator_agent/__init__.py`.
* [x] Create `agents/portfolio/portfolio_orchestrator_agent/agent.py`.
* [x] Create `agents/portfolio/portfolio_orchestrator_agent/contracts.py`.
* [x] Create `agents/portfolio/portfolio_orchestrator_agent/prompts.py`.
* [x] Create `agents/portfolio/portfolio_orchestrator_agent/deterministic_policy.py`.
* [x] Create `agents/portfolio/portfolio_orchestrator_agent/tools.py`.
* [x] Create `agents/portfolio/portfolio_orchestrator_agent/service.py`.
* [x] Create `agents/portfolio/portfolio_orchestrator_agent/evaluator.py`.
* [x] Create `agents/portfolio/portfolio_orchestrator_agent/README.md`.
* [x] Create required tests.
* [x] Validate portfolio request type.
* [x] Validate caller permission.
* [x] Validate request context.
* [x] Determine required evidence.
* [x] Determine required agents/services.
* [x] Route lifecycle requests to Portfolio Manager Agent.
* [x] Route allocation requests to Allocation Optimizer Agent.
* [x] Route paper execution requests to Paper Execution Agent.
* [x] Route live execution requests to Live Execution Agent.
* [x] Route readiness checks to Execution Readiness Agent.
* [x] Route reporting requests to Performance Reporter Agent.
* [x] Route cost requests to Cost Optimizer Agent.
* [x] Route audit checks to Audit Agent.
* [x] Route incidents to Incident Agent/Service.
* [x] Merge portfolio evidence.
* [x] Detect missing upstream evidence.
* [x] Detect conflicting recommendations.
* [x] Escalate Board-required decisions.
* [x] Produce portfolio orchestration result.
* [x] Save orchestration audit record.

## Required Evidence

* [x] Strategy lifecycle state.
* [x] RiskGovernor constraints.
* [x] Latest risk memo.
* [x] Backtest evidence package.
* [x] Robustness report.
* [x] Statistical validation report.
* [x] Paper trading report.
* [x] Live performance report.
* [x] Execution health status.
* [x] Audit health status.
* [x] Cost budget status.

## LLM Responsibilities

* [x] Summarize portfolio request.
* [x] Explain evidence conflicts.
* [x] Draft CEO-facing portfolio memo.
* [x] Draft Board decision summary.
* [x] Summarize recommended next actions.

## Deterministic Policy Rules

* [x] Reject request if required evidence is missing.
* [x] Reject live allocation changes without Board approval.
* [x] Reject live execution routing if RiskGovernor is unavailable.
* [x] Reject live execution routing if kill switch is active.
* [x] Reject live execution routing if audit logging is unavailable.
* [x] Escalate critical conflicts to Board workflow.
* [x] Allow only read-only summaries unless a governed workflow is active.

## Allowed Actions

* [x] `coordinate_portfolio_review`.
* [x] `request_lifecycle_review`.
* [x] `request_allocation_review`.
* [x] `request_execution_readiness_check`.
* [x] `request_report_generation`.
* [x] `request_audit_check`.
* [x] `escalate_to_board_workflow`.

## Blocked Actions

* [x] `execute_trade`.
* [x] `approve_risk`.
* [x] `change_live_allocation_directly`.
* [x] `resume_live_trading_after_critical_incident`.
* [x] `modify_risk_thresholds`.

## Output Artifacts

* [x] Portfolio orchestration plan.
* [x] Required evidence list.
* [x] Agent routing plan.
* [x] Board escalation packet.
* [x] Portfolio orchestration audit record.

## Tests Required

* [x] Normal portfolio review request.
* [x] Missing risk evidence rejection.
* [x] Live allocation request without Board approval rejection.
* [x] Kill switch active rejection.
* [x] Audit unavailable rejection.
* [x] LLM cannot override deterministic route blocking.

---

# 3. Portfolio Manager Agent

## Goal

Manage strategy lifecycle, allocation recommendations, and portfolio composition.

## Purpose

The Portfolio Manager Agent determines whether a strategy should remain rejected, enter paper trading, be promoted to micro-live, receive a larger allocation, receive a smaller allocation, be paused, or be retired.

It may recommend actions, but live allocation changes require deterministic checks, RiskGovernor constraints, and Board approval.

## Folder

```text
agents/portfolio/portfolio_manager_agent/
```

## Checklist

* [x] Create `agents/portfolio/portfolio_manager_agent/__init__.py`.
* [x] Create `agents/portfolio/portfolio_manager_agent/agent.py`.
* [x] Create `agents/portfolio/portfolio_manager_agent/contracts.py`.
* [x] Create `agents/portfolio/portfolio_manager_agent/prompts.py`.
* [x] Create `agents/portfolio/portfolio_manager_agent/deterministic_policy.py`.
* [x] Create `agents/portfolio/portfolio_manager_agent/tools.py`.
* [x] Create `agents/portfolio/portfolio_manager_agent/service.py`.
* [x] Create `agents/portfolio/portfolio_manager_agent/evaluator.py`.
* [x] Create `agents/portfolio/portfolio_manager_agent/README.md`.
* [x] Create required tests.
* [x] Read strategy lifecycle table.
* [x] Read strategy specification.
* [x] Read strategy code review result.
* [x] Read backtest result package.
* [x] Read backtest diagnosis report.
* [x] Read optimization comparator report.
* [x] Read robustness result.
* [x] Read statistical validation result.
* [x] Read paper strategy performance.
* [x] Read live strategy performance.
* [x] Read correlation matrix.
* [x] Read allocation limits.
* [x] Read current capital allocation.
* [x] Read RiskGovernor constraints.
* [x] Read risk memo.
* [x] Read execution health.
* [x] Read audit status.
* [x] Read cost status.
* [x] Detect strategy lifecycle state.
* [x] Detect missing lifecycle stages.
* [x] Detect promotion eligibility.
* [x] Detect demotion conditions.
* [x] Detect pause conditions.
* [x] Detect retirement conditions.
* [x] Detect portfolio concentration risk.
* [x] Detect strategy duplication.
* [x] Detect correlated strategy clusters.
* [x] Detect underperforming strategies.
* [x] Detect paper-to-live candidates.
* [x] Detect live allocation increase candidates.
* [x] Detect live allocation decrease candidates.
* [x] Recommend strategy promotions.
* [x] Recommend strategy demotions.
* [x] Recommend strategy retirement.
* [x] Recommend capital allocation changes.
* [x] Require Board approval for live allocation changes.
* [x] Save portfolio decision memo.
* [x] Save portfolio decision audit.

## Portfolio Decision Types

* [x] `admit_to_paper`.
* [x] `reject_strategy`.
* [x] `promote_to_micro_live`.
* [x] `increase_allocation`.
* [x] `decrease_allocation`.
* [x] `pause_strategy`.
* [x] `resume_strategy`.
* [x] `retire_strategy`.
* [x] `hold_current_state`.
* [x] `request_more_evidence`.

## Required Evidence

* [x] Research evidence references.
* [x] Strategy spec version.
* [x] Strategy code hash.
* [x] Backtest run IDs.
* [x] Robustness scorecard.
* [x] Statistical evidence rating.
* [x] RiskGovernor constraints.
* [x] Portfolio exposure snapshot.
* [x] Correlation matrix.
* [x] Paper performance snapshot.
* [x] Live performance snapshot.
* [x] Audit health status.

## LLM Responsibilities

* [x] Explain portfolio trade-offs.
* [x] Summarize strategy lifecycle evidence.
* [x] Compare strategy candidates.
* [x] Draft portfolio decision memo.
* [x] Explain why a strategy was promoted, paused, or retired.

## Deterministic Policy Rules

* [x] Reject `admit_to_paper` if strategy spec is missing.
* [x] Reject `admit_to_paper` if strategy code review failed.
* [x] Reject `admit_to_paper` if minimum simulation evidence is missing.
* [x] Reject `promote_to_micro_live` if paper trading period is incomplete.
* [x] Reject `promote_to_micro_live` if RiskGovernor constraints fail.
* [x] Reject `promote_to_micro_live` if audit logs are incomplete.
* [x] Reject `increase_allocation` if drawdown exceeds policy.
* [x] Reject `increase_allocation` if strategy correlation exceeds limit.
* [x] Reject `increase_allocation` if cost-adjusted performance is weak.
* [x] Require Board approval for all live allocation changes.
* [x] Require signed decision record for lifecycle state changes.
* [x] Fail closed when lifecycle evidence is inconsistent.

## Allowed Actions

* [x] `recommend_admit_to_paper`.
* [x] `recommend_reject_strategy`.
* [x] `recommend_promote_to_micro_live`.
* [x] `recommend_increase_allocation`.
* [x] `recommend_decrease_allocation`.
* [x] `recommend_pause_strategy`.
* [x] `recommend_retire_strategy`.
* [x] `request_more_evidence`.

## Blocked Actions

* [x] `execute_trade`.
* [x] `approve_risk`.
* [x] `directly_change_live_allocation`.
* [x] `bypass_board_approval`.
* [x] `modify_risk_thresholds`.

## Output Artifacts

* [x] Portfolio decision memo.
* [x] Strategy lifecycle decision.
* [x] Allocation recommendation.
* [x] Board approval request.
* [x] Evidence references.
* [x] Audit record.

## Tests Required

* [x] Admit-to-paper normal case.
* [x] Reject missing strategy spec.
* [x] Reject missing backtest evidence.
* [x] Reject live promotion without paper history.
* [x] Reject allocation increase due to correlation.
* [x] Require Board approval for live allocation change.
* [x] LLM cannot override deterministic lifecycle rejection.

## Done Definition

The system manages a portfolio of strategies, not isolated backtests.

---

# 4. Allocation Optimizer Agent

## Goal

Recommend capital allocation changes across strategies while respecting RiskGovernor constraints, drawdown controls, correlation limits, and lifecycle status.

## Folder

```text
agents/portfolio/allocation_optimizer_agent/
```

## Checklist

* [x] Create standard agent files.
* [x] Read current allocation table.
* [x] Read available capital.
* [x] Read strategy lifecycle state.
* [x] Read strategy risk budgets.
* [x] Read strategy volatility.
* [x] Read strategy drawdown.
* [x] Read strategy Sharpe/Sortino/Omega.
* [x] Read strategy expected trade frequency.
* [x] Read strategy live/paper confidence.
* [x] Read strategy correlation matrix.
* [x] Read symbol exposure.
* [x] Read currency-cluster exposure.
* [x] Read RiskGovernor allocation constraints.
* [x] Read max strategy allocation.
* [x] Read max symbol allocation.
* [x] Read max cluster allocation.
* [x] Read max portfolio margin usage.
* [x] Compute equal-capital allocation.
* [x] Compute volatility-adjusted allocation.
* [x] Compute drawdown-adjusted allocation.
* [x] Compute risk-parity-style allocation.
* [x] Compute confidence-weighted allocation.
* [x] Compute constrained allocation proposal.
* [x] Detect overconcentrated strategies.
* [x] Detect underutilized robust strategies.
* [x] Detect allocation cliffs.
* [x] Detect correlated allocation clusters.
* [x] Recommend capital increases.
* [x] Recommend capital decreases.
* [x] Recommend capped allocation.
* [x] Recommend no-change decision.
* [x] Produce allocation proposal.
* [x] Save allocation audit.

## Deterministic Policy Rules

* [x] Reject allocation proposal if total allocation exceeds capital.
* [x] Reject allocation proposal if strategy is not eligible.
* [x] Reject allocation proposal if max strategy allocation exceeded.
* [x] Reject allocation proposal if symbol concentration exceeded.
* [x] Reject allocation proposal if correlation concentration exceeded.
* [x] Reject allocation proposal if RiskGovernor constraints fail.
* [x] Require Board approval for live allocation increases.
* [x] Fail closed if allocation table is stale.

## Output Artifacts

* [x] Allocation proposal.
* [x] Allocation constraint report.
* [x] Strategy-level allocation table.
* [x] Symbol-level exposure table.
* [x] Cluster-level exposure table.
* [x] Board approval request if needed.

## Done Definition

Capital allocation recommendations are robust, risk-aware, and not based only on recent performance.

---

# 5. Strategy Lifecycle Agent

## Goal

Maintain the official lifecycle state of each strategy and ensure strategies cannot skip required evidence gates.

## Folder

```text
agents/portfolio/strategy_lifecycle_agent/
```

## Lifecycle States

* [x] `idea`.
* [x] `spec`.
* [x] `coded`.
* [x] `reviewed`.
* [x] `backtested`.
* [x] `diagnosed`.
* [x] `optimized`.
* [x] `robustness_tested`.
* [x] `statistically_validated`.
* [x] `paper_candidate`.
* [x] `paper_live`.
* [x] `micro_live_candidate`.
* [x] `micro_live`.
* [x] `live_candidate`.
* [x] `live`.
* [x] `paused`.
* [x] `retired`.
* [x] `rejected`.

## Checklist

* [x] Create standard agent files.
* [x] Read current lifecycle table.
* [x] Read requested lifecycle transition.
* [x] Validate allowed transition path.
* [x] Validate required evidence for transition.
* [x] Validate required approvals for transition.
* [x] Validate strategy code hash.
* [x] Validate strategy spec version.
* [x] Validate simulation evidence.
* [x] Validate risk evidence.
* [x] Validate audit evidence.
* [x] Validate Board approval where required.
* [x] Update lifecycle state only through governed service.
* [x] Record transition reason.
* [x] Record transition actor.
* [x] Record transition timestamp.
* [x] Record evidence references.
* [x] Record old state and new state.
* [x] Block invalid transitions.
* [x] Save lifecycle audit.

## Deterministic Policy Rules

* [x] Reject transitions that skip mandatory stages.
* [x] Reject live transition without Board approval.
* [x] Reject live transition without RiskGovernor compatibility.
* [x] Reject paper transition without strategy review.
* [x] Reject micro-live transition without paper trading evidence.
* [x] Reject resume transition after critical incident without approval.
* [x] Fail closed if lifecycle table is stale or inconsistent.

## Done Definition

Every strategy has a controlled lifecycle and cannot silently jump from idea to live trading.

---

# 6. Paper Broker Service

## Goal

Simulate live-like execution without risking real capital.

## Type

Deterministic service, not an LLM agent.

## Path

```text
services/portfolio/paper_broker.py
```

## Checklist

* [x] Create `services/portfolio/paper_broker.py`.
* [x] Define `PaperBrokerConfig`.
* [x] Define `PaperOrderRequest`.
* [x] Define `PaperOrderResult`.
* [x] Define `PaperPosition`.
* [x] Define `PaperAccountState`.
* [x] Simulate market orders.
* [x] Simulate limit orders.
* [x] Simulate stop orders.
* [x] Simulate pending order fills.
* [x] Simulate partial fills if enabled.
* [x] Simulate rejection conditions.
* [x] Simulate spread.
* [x] Simulate slippage.
* [x] Simulate commission.
* [x] Simulate swap.
* [x] Simulate margin usage.
* [x] Simulate margin call behavior if enabled.
* [x] Track open positions.
* [x] Track pending orders.
* [x] Track realized P&L.
* [x] Track unrealized P&L.
* [x] Track balance.
* [x] Track equity.
* [x] Track margin.
* [x] Track free margin.
* [x] Track order history.
* [x] Track deals.
* [x] Save execution logs.
* [x] Save broker state snapshots.
* [x] Support deterministic replay.
* [x] Support reset between paper runs.

## Deterministic Policy Rules

* [x] Reject orders with invalid symbol.
* [x] Reject orders with invalid volume.
* [x] Reject orders with invalid side.
* [x] Reject orders with insufficient margin.
* [x] Reject orders when paper mode disabled.
* [x] Reject orders without RiskGovernor paper approval if required.
* [x] Reject orders if audit logging is unavailable.

## Done Definition

A strategy can run in paper mode with live-like execution assumptions, full risk checks, and full audit logs.

---

# 7. Paper Execution Agent

## Goal

Operate approved paper strategies through the paper broker with the same risk and audit standards used for live trading.

## Folder

```text
agents/portfolio/paper_execution_agent/
```

## Checklist

* [x] Create standard agent files.
* [x] Read approved paper strategies.
* [x] Validate strategy lifecycle state is `paper_live`.
* [x] Read strategy signal.
* [x] Validate signal schema.
* [x] Create trade proposal.
* [x] Call RiskGovernor in paper mode.
* [x] Validate paper approval token.
* [x] Send approved order to paper broker.
* [x] Log paper order request.
* [x] Log paper broker response.
* [x] Log simulated slippage.
* [x] Log simulated spread.
* [x] Log position update.
* [x] Log rejection reason.
* [x] Report anomalies.
* [x] Save paper execution audit.

## Paper Trading Promotion Criteria

* [x] Minimum 30 trading days.
* [x] Minimum trade count.
* [x] Max drawdown within limit.
* [x] Daily loss within limit.
* [x] Weekly loss within limit.
* [x] Slippage within expected range.
* [x] Live-like spread assumptions.
* [x] No execution anomalies.
* [x] No RiskGovernor violations.
* [x] No audit gaps.
* [x] Performance within expected confidence interval.
* [x] Behavior consistent with backtest expectation.

## Deterministic Policy Rules

* [x] Block if paper mode disabled.
* [x] Block if strategy not in approved paper lifecycle state.
* [x] Block if approval token missing.
* [x] Block if approval token expired.
* [x] Block if token does not match symbol.
* [x] Block if token does not match side.
* [x] Block if token does not match approved size.
* [x] Block if paper broker unavailable.
* [x] Block if audit logging unavailable.
* [x] Block if RiskGovernor unavailable.

## Done Definition

Paper execution operates like live trading, except it uses simulated broker execution and does not risk real capital.

---

# 8. Live Execution Agent

## Goal

Create live trade proposals and route only RiskGovernor-approved orders through deterministic execution infrastructure.

## Folder

```text
agents/portfolio/live_execution_agent/
```

## Checklist

* [x] Create standard agent files.
* [x] Read approved live strategies.
* [x] Validate strategy lifecycle state is live-enabled.
* [x] Listen for strategy signals.
* [x] Validate signal schema.
* [x] Validate strategy code hash.
* [x] Validate strategy config hash.
* [x] Validate live mode enabled.
* [x] Validate Board approval for strategy live status.
* [x] Create trade proposal.
* [x] Call RiskGovernor.
* [x] Validate approval token.
* [x] Validate approval token expiration.
* [x] Validate approval token signature.
* [x] Validate approval token symbol.
* [x] Validate approval token side.
* [x] Validate approval token size.
* [x] Validate kill switch status.
* [x] Validate broker heartbeat.
* [x] Validate audit logger health.
* [x] Call order router.
* [x] Log order request.
* [x] Log broker response.
* [x] Log execution latency.
* [x] Log spread at execution.
* [x] Log slippage.
* [x] Log commission.
* [x] Log swap estimate where available.
* [x] Log position update.
* [x] Log rejected order reason.
* [x] Report execution anomalies.
* [x] Save live execution audit.

## Execution Safety

* [x] Block if live mode disabled.
* [x] Block if strategy not live.
* [x] Block if strategy lifecycle state is not live-enabled.
* [x] Block if Board approval missing.
* [x] Block if approval token missing.
* [x] Block if approval token expired.
* [x] Block if approval token signature invalid.
* [x] Block if approval token mismatches order.
* [x] Block if kill switch triggered.
* [x] Block if broker heartbeat failed.
* [x] Block if spread too high.
* [x] Block if slippage too high.
* [x] Block if audit logging unavailable.
* [x] Block if RiskGovernor unavailable.
* [x] Block if broker bridge is degraded.
* [x] Block if repeated order failures exceed limit.

## LLM Responsibilities

* [x] Explain rejected live order reasons.
* [x] Summarize execution anomalies.
* [x] Draft execution incident summaries.
* [x] Explain live execution health status.

## Deterministic Policy Rules

* [x] Never execute without a valid RiskGovernor approval token.
* [x] Never execute if approval token does not match order exactly.
* [x] Never execute if kill switch is active.
* [x] Never execute if audit logging is unavailable.
* [x] Never execute if broker heartbeat is stale.
* [x] Never execute if strategy lifecycle state is not live-enabled.
* [x] Never execute if live mode is disabled.
* [x] Fail closed on any unknown broker or risk state.

## Output Artifacts

* [x] Trade proposal.
* [x] Risk approval token reference.
* [x] Order request record.
* [x] Broker response record.
* [x] Execution anomaly report.
* [x] Live execution audit.

## Tests Required

* [x] Valid live proposal with valid token routes to order router.
* [x] Missing token blocks execution.
* [x] Expired token blocks execution.
* [x] Mismatched size blocks execution.
* [x] Kill switch active blocks execution.
* [x] Broker heartbeat failure blocks execution.
* [x] Audit unavailable blocks execution.
* [x] LLM cannot override execution block.

## Done Definition

Live orders can happen, but only through deterministic guardrails.

---

# 9. Execution Readiness Agent

## Goal

Check whether live execution infrastructure is ready without necessarily enabling live trading.

## Folder

```text
agents/portfolio/execution_readiness_agent/
```

## Checklist

* [x] Create standard agent files.
* [x] Read live mode configuration.
* [x] Read Board live approval state.
* [x] Read RiskGovernor health.
* [x] Read kill switch health.
* [x] Read audit logger health.
* [x] Read MT5 bridge health.
* [x] Read cTrader bridge health.
* [x] Read order router health.
* [x] Read broker heartbeat.
* [x] Read broker account info.
* [x] Read broker symbol metadata.
* [x] Read spread conditions.
* [x] Read slippage conditions.
* [x] Read open positions.
* [x] Read pending orders.
* [x] Read recent order failures.
* [x] Check permission profile.
* [x] Check secrets/config availability without exposing secrets.
* [x] Check environment mode.
* [x] Check execution disabled-by-default policy.
* [x] Output readiness status.
* [x] Output blocking issues.
* [x] Output warning issues.
* [x] Save readiness audit.

## Deterministic Policy Rules

* [x] Mark `not_ready` if RiskGovernor unavailable.
* [x] Mark `not_ready` if audit logger unavailable.
* [x] Mark `not_ready` if kill switch unavailable.
* [x] Mark `not_ready` if broker heartbeat failed.
* [x] Mark `not_ready` if order router unavailable.
* [x] Mark `not_ready` if live mode config is inconsistent.
* [x] Mark `ready_but_disabled` if infrastructure is healthy but live mode is off.
* [x] Never enable live trading directly.

## Done Definition

Live execution infrastructure can be checked safely before it is allowed to trade.

---

# 10. MT5 Execution Bridge

## Goal

Prepare MetaTrader 5 execution infrastructure using a normalized bridge interface while keeping live trading blocked unless approved.

## Type

Deterministic bridge service.

## Path

```text
services/execution/bridges/mt5_bridge.py
```

## Checklist

* [x] Create `services/execution/bridges/base_bridge.py`.
* [x] Create `services/execution/bridges/mt5_bridge.py`.
* [x] Implement `connect`.
* [x] Implement `disconnect`.
* [x] Implement `heartbeat`.
* [x] Implement `get_account_info`.
* [x] Implement `get_symbol_info`.
* [x] Implement `get_latest_tick`.
* [x] Implement `get_open_positions`.
* [x] Implement `get_pending_orders`.
* [x] Implement `place_order`.
* [x] Implement `modify_order`.
* [x] Implement `close_position`.
* [x] Implement `cancel_order`.
* [x] Implement reconnection logic.
* [x] Implement broker timeout handling.
* [x] Implement broker error normalization.
* [x] Implement symbol metadata normalization.
* [x] Implement pip/tick value normalization.
* [x] Implement volume step normalization.
* [x] Implement min/max volume validation.
* [x] Implement execution audit logs.
* [x] Implement idempotency protection.
* [x] Implement duplicate-order prevention.
* [x] Implement dry-run mode.
* [x] Implement paper/simulated mode compatibility.

## Deterministic Policy Rules

* [x] Never place an order unless called by Order Router.
* [x] Reject direct calls from agents.
* [x] Reject live orders when live mode disabled.
* [x] Reject orders without validated RiskGovernor approval token.
* [x] Reject orders with invalid normalized symbol metadata.
* [x] Reject orders with invalid volume step.
* [x] Fail closed on broker uncertainty.

## Done Definition

MT5 bridge can expose broker functions through a normalized, audited, deterministic execution interface.

---

# 11. cTrader Execution Bridge

## Goal

Prepare cTrader execution infrastructure with the same normalized interface as MT5.

## Type

Deterministic bridge service.

## Path

```text
services/execution/bridges/ctrader_bridge.py
```

## Checklist

* [x] Create `services/execution/bridges/ctrader_bridge.py`.
* [x] Match same interface as MT5 bridge.
* [x] Implement `connect`.
* [x] Implement `disconnect`.
* [x] Implement `heartbeat`.
* [x] Implement `get_account_info`.
* [x] Implement `get_symbol_info`.
* [x] Implement `get_latest_tick`.
* [x] Implement `get_open_positions`.
* [x] Implement `get_pending_orders`.
* [x] Implement `place_order`.
* [x] Implement `modify_order`.
* [x] Implement `close_position`.
* [x] Implement `cancel_order`.
* [x] Normalize symbol metadata.
* [x] Normalize pip/tick values.
* [x] Normalize volume units.
* [x] Normalize order status.
* [x] Normalize position status.
* [x] Normalize error codes.
* [x] Add reconnection logic.
* [x] Add heartbeat.
* [x] Add broker error handling.
* [x] Add execution audit logs.
* [x] Add dry-run mode.

## Done Definition

cTrader can be used through the same execution contract as MT5.

---

# 12. Order Router Service

## Goal

Route approved orders to the correct execution bridge only after all deterministic guardrails pass.

## Type

Deterministic service, not an LLM agent.

## Path

```text
services/portfolio/order_router.py
```

## Checklist

* [x] Create `services/portfolio/order_router.py`.
* [x] Define `OrderRouteRequest`.
* [x] Define `OrderRouteResult`.
* [x] Read approved broker bridge.
* [x] Read live mode flag.
* [x] Read strategy live status.
* [x] Read kill switch status.
* [x] Read broker heartbeat status.
* [x] Read audit logger health.
* [x] Validate RiskGovernor approval token.
* [x] Validate token expiration.
* [x] Validate token signature.
* [x] Validate token proposal ID.
* [x] Validate token strategy ID.
* [x] Validate token symbol.
* [x] Validate token side.
* [x] Validate token approved size.
* [x] Validate order type.
* [x] Validate normalized broker metadata.
* [x] Validate max spread.
* [x] Validate max slippage.
* [x] Reject stale approval tokens.
* [x] Reject mismatched order size.
* [x] Reject mismatched symbol.
* [x] Reject mismatched side.
* [x] Reject mismatched order type.
* [x] Reject if broker heartbeat unhealthy.
* [x] Reject if audit logging unavailable.
* [x] Route order to MT5 bridge if broker is MT5.
* [x] Route order to cTrader bridge if broker is cTrader.
* [x] Log all rejected orders.
* [x] Log all routed orders.
* [x] Log broker responses.

## Deterministic Policy Rules

* [x] Order Router is the only service allowed to call live bridge order placement.
* [x] Never route without a valid RiskGovernor token.
* [x] Never route when kill switch is triggered.
* [x] Never route when live mode is disabled.
* [x] Never route when broker heartbeat is unhealthy.
* [x] Never route when audit logging is unavailable.
* [x] Fail closed on any mismatch.

## Done Definition

Live execution code exists but remains blocked by configuration, RiskGovernor approval, kill switch health, audit health, and Board approval.

---

# 13. Kill Switch Service

## Goal

Protect the account when abnormal conditions occur.

## Type

Deterministic service, not an LLM agent.

## Path

```text
services/portfolio/kill_switch.py
```

## Checklist

* [x] Create `services/portfolio/kill_switch.py`.
* [x] Define kill switch states.
* [x] Define trigger severity.
* [x] Define trigger policy config.
* [x] Monitor daily loss.
* [x] Monitor weekly loss.
* [x] Monitor account drawdown.
* [x] Monitor strategy drawdown.
* [x] Monitor symbol drawdown.
* [x] Monitor portfolio exposure.
* [x] Monitor broker connection.
* [x] Monitor broker heartbeat.
* [x] Monitor spread spikes.
* [x] Monitor slippage spikes.
* [x] Monitor repeated order failures.
* [x] Monitor execution latency spikes.
* [x] Monitor audit logger health.
* [x] Monitor RiskGovernor health.
* [x] Monitor data feed health.
* [x] Monitor price staleness.
* [x] Monitor abnormal fills.
* [x] Disable new orders if triggered.
* [x] Optionally close positions based on policy.
* [x] Block strategy resumes after critical incident.
* [x] Write incident report.
* [x] Emit alert.
* [x] Save kill switch audit.

## Kill Switch States

* [x] `healthy`.
* [x] `warning`.
* [x] `new_orders_blocked`.
* [x] `position_reduction_only`.
* [x] `close_all_required`.
* [x] `manual_review_required`.
* [x] `critical_shutdown`.

## Deterministic Policy Rules

* [x] Trigger if daily loss exceeds configured limit.
* [x] Trigger if weekly loss exceeds configured limit.
* [x] Trigger if account drawdown exceeds configured limit.
* [x] Trigger if broker heartbeat fails beyond allowed window.
* [x] Trigger if repeated order failures exceed threshold.
* [x] Trigger if audit logging is unavailable.
* [x] Trigger if RiskGovernor unavailable.
* [x] Critical trigger disables live trading.
* [x] Resume after critical trigger requires human approval.
* [x] Fail closed if kill switch state cannot be determined.

## Done Definition

The system can stop itself before a small failure becomes a major loss.

---

# 14. Incident Agent

## Goal

Explain portfolio, execution, broker, risk, or audit incidents and recommend controlled response actions.

## Folder

```text
agents/portfolio/incident_agent/
```

## Checklist

* [x] Create standard agent files.
* [x] Read incident trigger.
* [x] Read kill switch state.
* [x] Read affected strategies.
* [x] Read affected symbols.
* [x] Read open positions.
* [x] Read pending orders.
* [x] Read recent broker responses.
* [x] Read recent rejected orders.
* [x] Read RiskGovernor state.
* [x] Read audit logger state.
* [x] Read execution bridge state.
* [x] Summarize incident.
* [x] Identify trigger.
* [x] Identify severity.
* [x] Identify affected strategies.
* [x] Identify affected open positions.
* [x] Identify immediate required action.
* [x] Recommend pause/resume/close/reduce/hold.
* [x] Require human approval to resume live trading after critical incidents.
* [x] Produce incident memo.
* [x] Save incident audit.

## Deterministic Policy Rules

* [x] Block resume recommendation if critical incident unresolved.
* [x] Block resume recommendation without human approval after critical incident.
* [x] Mark incident as critical if audit logging failed during live execution.
* [x] Mark incident as critical if RiskGovernor failed during live execution.
* [x] Mark incident as critical if unauthorized order detected.
* [x] Fail closed on unknown broker state.

## Done Definition

Incidents are explained, classified, audited, and safely routed to a recovery workflow.

---

# 15. Performance Reporter Agent

## Goal

Create automated daily, weekly, monthly, and Board-level reports.

## Folder

```text
agents/portfolio/performance_reporter_agent/
```

## Checklist

* [x] Create standard agent files.
* [x] Read portfolio P&L.
* [x] Read open exposure.
* [x] Read realized P&L.
* [x] Read unrealized P&L.
* [x] Read drawdown.
* [x] Read trade count.
* [x] Read active strategies.
* [x] Read paper strategies.
* [x] Read live strategies.
* [x] Read rejected trades.
* [x] Read RiskGovernor blocks.
* [x] Read execution anomalies.
* [x] Read cost usage.
* [x] Read audit findings.
* [x] Generate daily report.
* [x] Generate weekly Board report.
* [x] Generate monthly strategy review.
* [x] Generate strategy-level health report.
* [x] Generate portfolio-level health report.
* [x] Generate allocation change summary.
* [x] Generate decision-required summary.
* [x] Save report artifacts.
* [x] Save report audit.

## Daily Report Checklist

* [x] Report daily P&L.
* [x] Report open exposure.
* [x] Report drawdown.
* [x] Report trade count.
* [x] Report strategy health.
* [x] Report rejected trades.
* [x] Report RiskGovernor blocks.
* [x] Report execution anomalies.
* [x] Report cost usage.
* [x] Report audit warnings.
* [x] Report next actions.

## Weekly Board Report Checklist

* [x] Summarize portfolio performance.
* [x] Summarize paper strategies.
* [x] Summarize live strategies.
* [x] Summarize new research.
* [x] Summarize backtests.
* [x] Summarize robustness tests.
* [x] Summarize risk events.
* [x] Summarize execution events.
* [x] Summarize audit events.
* [x] Summarize cost usage.
* [x] List decisions required from Board/user.

## Monthly Strategy Review Checklist

* [x] Rank active strategies.
* [x] Rank paper strategies.
* [x] Identify underperformers.
* [x] Identify promotion candidates.
* [x] Identify retirement candidates.
* [x] Identify correlated strategy clusters.
* [x] Identify cost-heavy strategies.
* [x] Identify overtrading strategies.
* [x] Recommend allocation changes.
* [x] Recommend lifecycle changes.

## Deterministic Policy Rules

* [x] Reject report generation if required data is missing.
* [x] Mark report incomplete if audit gaps exist.
* [x] Mark report incomplete if execution logs are missing.
* [x] Never change allocation from a report.
* [x] Never approve strategy promotion from a report.
* [x] Escalate critical audit/risk findings.

## Done Definition

The user can review HaruQuant like a hedge-fund operator, not as a code debugger.

---

# 16. Audit Agent

## Goal

Continuously verify that the system is obeying its own rules.

## Folder

```text
agents/audit/audit_agent/
```

## Checklist

* [x] Create `agents/audit/audit_agent/__init__.py`.
* [x] Create `agents/audit/audit_agent/agent.py`.
* [x] Create `agents/audit/audit_agent/contracts.py`.
* [x] Create `agents/audit/audit_agent/prompts.py`.
* [x] Create `agents/audit/audit_agent/deterministic_policy.py`.
* [x] Create `agents/audit/audit_agent/tools.py`.
* [x] Create `agents/audit/audit_agent/service.py`.
* [x] Create `agents/audit/audit_agent/evaluator.py`.
* [x] Create `agents/audit/audit_agent/README.md`.
* [x] Create required tests.
* [x] Check every live order has RiskGovernor approval.
* [x] Check every approval token matches executed order.
* [x] Check approval token was not expired at execution time.
* [x] Check approval token signature/hash.
* [x] Check no agent changed risk thresholds.
* [x] Check no strategy skipped lifecycle stages.
* [x] Check no live strategy lacks Board approval.
* [x] Check no missing evidence refs.
* [x] Check no missing execution logs.
* [x] Check no missing broker responses.
* [x] Check no missing order-router logs.
* [x] Check no missing RiskGovernor audit records.
* [x] Check no hidden failed tool calls.
* [x] Check no direct bridge calls bypassed Order Router.
* [x] Check no direct execution call came from specialist agents.
* [x] Check no live trading occurred while kill switch was active.
* [x] Check no live trading occurred while audit logger was unhealthy.
* [x] Check no live trading occurred while RiskGovernor was unavailable.
* [x] Generate daily audit report.
* [x] Generate critical audit alert.
* [x] Save audit evidence.

## Audit Severity

* [x] `info`.
* [x] `warning`.
* [x] `major`.
* [x] `critical`.

## Deterministic Policy Rules

* [x] Critical audit failure disables live trading.
* [x] Major audit failure blocks new live orders until reviewed.
* [x] Missing RiskGovernor token on live order is critical.
* [x] Token/order mismatch is critical.
* [x] Direct bridge call bypassing router is critical.
* [x] Missing broker response on live order is major or critical.
* [x] Missing audit record is major or critical.
* [x] Unknown execution state is critical.

## Allowed Actions

* [x] `generate_audit_report`.
* [x] `flag_audit_issue`.
* [x] `escalate_critical_audit_failure`.
* [x] `request_live_trading_disable`.

## Blocked Actions

* [x] `execute_trade`.
* [x] `approve_risk`.
* [x] `modify_risk_thresholds`.
* [x] `resume_live_trading`.

## Done Definition

The system has internal compliance, not just performance tracking.

---

# 17. Cost Optimizer Agent

## Goal

Control LLM usage, infrastructure cost, backtest cost, and research cost without weakening risk controls.

## Folder

```text
agents/portfolio/cost_optimizer_agent/
```

## Checklist

* [x] Create standard agent files.
* [x] Track model provider.
* [x] Track model name.
* [x] Track prompt tokens.
* [x] Track completion tokens.
* [x] Track total tokens.
* [x] Track cost per task.
* [x] Track cost per agent.
* [x] Track cost per workflow.
* [x] Track cost per department.
* [x] Track cost per strategy.
* [x] Track failed-call cost.
* [x] Track retry cost.
* [x] Track backtest compute cost.
* [x] Track optimization compute cost.
* [x] Track Monte Carlo compute cost.
* [x] Track data storage cost.
* [x] Track report generation cost.
* [x] Track cost per accepted strategy.
* [x] Track cost per rejected strategy.
* [x] Track cost per live candidate.
* [x] Track budget usage.
* [x] Detect cost anomalies.
* [x] Recommend cheaper model routing.
* [x] Recommend cache usage.
* [x] Recommend batch processing.
* [x] Recommend local model usage.
* [x] Produce daily cost report.
* [x] Produce weekly cost report.
* [x] Produce monthly cost report.
* [x] Save cost audit.

## Model Routing Rules

* [x] Use strong model for CEO decisions.
* [x] Use strong model for risk memos.
* [x] Use strong coding model for strategy code generation.
* [x] Use cheaper model for formatting reports.
* [x] Use cheaper model for simple summaries.
* [x] Use local model for low-risk summarization if quality is acceptable.
* [x] Use deterministic code for risk approvals.
* [x] Use deterministic code for order placement.
* [x] Use no LLM for RiskGovernor decisions.
* [x] Use no LLM for Order Router decisions.
* [x] Use no LLM for Kill Switch decisions.

## Deterministic Policy Rules

* [x] Never weaken risk controls to reduce cost.
* [x] Never route RiskGovernor decisions to an LLM.
* [x] Never route execution decisions to an LLM.
* [x] Reject model routing if permission profile disallows it.
* [x] Alert if cost exceeds budget.
* [x] Alert if failed-call cost exceeds threshold.
* [x] Alert if one strategy consumes abnormal cost.
* [x] Alert if one workflow consumes abnormal cost.

## Cost Reports

* [x] Daily cost report.
* [x] Weekly cost report.
* [x] Monthly cost report.
* [x] Cost per accepted strategy.
* [x] Cost per rejected strategy.
* [x] Cost per live candidate.
* [x] Cost per department.
* [x] Cost per model provider.
* [x] Cost anomaly alerts.

## Done Definition

Agents become economically manageable without compromising safety.

---

# 18. Shared Portfolio Contracts

## Goal

Define the machine-readable contracts used across the Portfolio Department.

## Checklist

* [x] Create `agents/portfolio/shared/contracts.py`.
* [x] Add `PortfolioRequest`.
* [x] Add `PortfolioDecision`.
* [x] Add `StrategyLifecycleState`.
* [x] Add `LifecycleTransitionRequest`.
* [x] Add `LifecycleTransitionResult`.
* [x] Add `AllocationProposal`.
* [x] Add `AllocationDecision`.
* [x] Add `ExecutionProposal`.
* [x] Add `ExecutionDecision`.
* [x] Add `PaperOrderRequest`.
* [x] Add `PaperOrderResult`.
* [x] Add `LiveOrderRequest`.
* [x] Add `LiveOrderResult`.
* [x] Add `OrderRouteRequest`.
* [x] Add `OrderRouteResult`.
* [x] Add `BrokerHealthSnapshot`.
* [x] Add `ExecutionHealthSnapshot`.
* [x] Add `KillSwitchState`.
* [x] Add `IncidentReport`.
* [x] Add `PerformanceReport`.
* [x] Add `AuditFinding`.
* [x] Add `CostReport`.

## Done Definition

All Portfolio Department agents and services exchange typed contracts instead of loose dictionaries.

---

# 19. Portfolio Decision Schema

## Checklist

* [x] Add `decision_id`.
* [x] Add `decision_type`.
* [x] Add `strategy_id`.
* [x] Add `strategy_name`.
* [x] Add `current_lifecycle_state`.
* [x] Add `proposed_lifecycle_state`.
* [x] Add `current_allocation`.
* [x] Add `proposed_allocation`.
* [x] Add `symbol_exposure_change`.
* [x] Add `currency_cluster_exposure_change`.
* [x] Add `correlation_impact`.
* [x] Add `risk_governor_constraints`.
* [x] Add `evidence_refs`.
* [x] Add `required_approval_level`.
* [x] Add `board_approval_required`.
* [x] Add `board_approval_id`.
* [x] Add `decision_status`.
* [x] Add `allowed_actions`.
* [x] Add `blocked_actions`.
* [x] Add `reasons`.
* [x] Add `confidence`.
* [x] Add `risk_level`.
* [x] Add `created_at`.
* [x] Add `expires_at` if applicable.
* [x] Add `audit_ref`.

---

# 20. Execution Proposal Schema

## Checklist

* [x] Add `proposal_id`.
* [x] Add `strategy_id`.
* [x] Add `strategy_name`.
* [x] Add `strategy_code_hash`.
* [x] Add `strategy_config_hash`.
* [x] Add `symbol`.
* [x] Add `side`.
* [x] Add `order_type`.
* [x] Add `requested_volume`.
* [x] Add `requested_price`.
* [x] Add `stop_loss`.
* [x] Add `take_profit`.
* [x] Add `signal_time`.
* [x] Add `proposal_time`.
* [x] Add `signal_reason`.
* [x] Add `setup_id`.
* [x] Add `group_id`.
* [x] Add `metadata`.
* [x] Add `risk_mode`.
* [x] Add `execution_mode`.
* [x] Add `evidence_refs`.

---

# 21. Execution Result Schema

## Checklist

* [x] Add `execution_id`.
* [x] Add `proposal_id`.
* [x] Add `approval_id`.
* [x] Add `broker`.
* [x] Add `bridge_name`.
* [x] Add `symbol`.
* [x] Add `side`.
* [x] Add `order_type`.
* [x] Add `requested_volume`.
* [x] Add `executed_volume`.
* [x] Add `requested_price`.
* [x] Add `executed_price`.
* [x] Add `spread_at_execution`.
* [x] Add `slippage`.
* [x] Add `commission`.
* [x] Add `swap_estimate`.
* [x] Add `broker_order_id`.
* [x] Add `broker_position_id`.
* [x] Add `broker_response_code`.
* [x] Add `broker_response_message`.
* [x] Add `status`.
* [x] Add `rejection_reason`.
* [x] Add `created_at`.
* [x] Add `audit_ref`.

---

# 22. Incident Report Schema

## Checklist

* [x] Add `incident_id`.
* [x] Add `incident_type`.
* [x] Add `severity`.
* [x] Add `trigger`.
* [x] Add `trigger_time`.
* [x] Add `detected_by`.
* [x] Add `affected_strategies`.
* [x] Add `affected_symbols`.
* [x] Add `affected_orders`.
* [x] Add `affected_positions`.
* [x] Add `kill_switch_state_before`.
* [x] Add `kill_switch_state_after`.
* [x] Add `risk_governor_state`.
* [x] Add `broker_state`.
* [x] Add `audit_state`.
* [x] Add `immediate_action_taken`.
* [x] Add `recommended_next_action`.
* [x] Add `resume_allowed`.
* [x] Add `human_approval_required`.
* [x] Add `evidence_refs`.
* [x] Add `audit_ref`.

---

# 23. Portfolio Permissions Model

## Checklist

* [x] Create `portfolio_read_only_v1` permission profile.
* [x] Create `portfolio_lifecycle_recommendation_v1` permission profile.
* [x] Create `portfolio_allocation_recommendation_v1` permission profile.
* [x] Create `paper_execution_v1` permission profile.
* [x] Create `live_execution_guarded_v1` permission profile.
* [x] Create `execution_bridge_internal_v1` permission profile.
* [x] Create `audit_read_only_v1` permission profile.
* [x] Create `cost_read_only_v1` permission profile.
* [x] Block all direct execution permissions from research agents.
* [x] Block all direct execution permissions from strategy creation agents.
* [x] Block all direct execution permissions from simulation agents.
* [x] Block all direct execution permissions from reporting agents.

## Permission Law

```text
Only Order Router can call broker bridges for live orders.
Only broker bridges can talk to MT5/cTrader.
Only RiskGovernor can approve risk.
Only Kill Switch can block execution globally.
Only Board workflow can approve live allocation changes.
Only Audit Agent can escalate critical compliance failure to live-trading disablement.
```

---

# 24. Portfolio Audit Requirements

## Checklist

* [x] Every portfolio decision must include `decision_id`.
* [x] Every lifecycle transition must include old state and new state.
* [x] Every allocation recommendation must include evidence refs.
* [x] Every live allocation change must include Board approval ref.
* [x] Every paper order must include paper approval/risk ref if required.
* [x] Every live order must include RiskGovernor approval token.
* [x] Every order router rejection must be logged.
* [x] Every broker response must be logged.
* [x] Every execution anomaly must be logged.
* [x] Every kill switch trigger must be logged.
* [x] Every resume action must be logged.
* [x] Every incident must have an incident report.
* [x] Every cost report must include provider/model/task metadata.
* [x] Every audit report must include severity.

Minimum audit fields:

```text
request_id
agent_name
service_name
workflow_id
strategy_id
proposal_id
decision_id
approval_id
evidence_refs
tools_called
permission_profile
policy_version
prompt_version
model_provider
model_name
fallback_used
created_at
status
blocked_actions
allowed_actions
reasons
```

---

# 25. Portfolio Output Package

## Goal

Create immutable output packages for important portfolio workflows.

## Portfolio Decision Package

```text
portfolio/decisions/<decision_id>/
  request.json
  evidence_refs.json
  lifecycle_snapshot.json
  risk_snapshot.json
  allocation_snapshot.json
  decision.json
  memo.md
  audit.json
```

## Execution Package

```text
portfolio/executions/<execution_id>/
  proposal.json
  risk_approval_token.json
  route_request.json
  broker_response.json
  position_update.json
  execution_summary.json
  audit.json
```

## Incident Package

```text
portfolio/incidents/<incident_id>/
  trigger.json
  affected_strategies.json
  affected_positions.json
  broker_state.json
  risk_state.json
  audit_state.json
  incident_report.md
  audit.json
```

## Reporting Package

```text
portfolio/reports/<report_id>/
  data_snapshot.json
  report.md
  charts/
  evidence_refs.json
  audit.json
```

---

# 26. Department Handoff Contracts

## Research to Portfolio

* [x] Receive market context affecting portfolio allocation.
* [x] Receive strategy idea lineage.
* [x] Receive evidence references.
* [x] Receive macro/sentiment warnings.
* [x] Receive correlation regime warnings.

## Strategy Creation to Portfolio

* [x] Receive strategy spec.
* [x] Receive strategy code hash.
* [x] Receive strategy review result.
* [x] Receive strategy README.
* [x] Receive strategy tests result.

## Simulation to Portfolio

* [x] Receive backtest run package.
* [x] Receive diagnosis report.
* [x] Receive optimization comparison.
* [x] Receive robustness scorecard.
* [x] Receive statistical validation result.
* [x] Receive evidence quality rating.

## Risk to Portfolio

* [x] Receive RiskGovernor constraints.
* [x] Receive risk memo.
* [x] Receive portfolio exposure limits.
* [x] Receive approved/rejected proposal result.
* [x] Receive risk approval tokens.

## Portfolio to Execution

* [x] Send only approved live strategy status.
* [x] Send strategy allocation limits.
* [x] Send execution proposals.
* [x] Send Board approval refs.
* [x] Send RiskGovernor approval token to Order Router.

## Portfolio to CEO/Board

* [x] Send portfolio decision memo.
* [x] Send Board approval request.
* [x] Send weekly Board report.
* [x] Send incident escalation memo.
* [x] Send cost anomaly report.

---

# 27. Standard Tests for Portfolio Department

## Checklist

* [x] Test all contracts serialize to JSON.
* [x] Test invalid lifecycle transition rejection.
* [x] Test strategy cannot skip required lifecycle stages.
* [x] Test paper order blocked without approved paper state.
* [x] Test live order blocked without RiskGovernor token.
* [x] Test live order blocked with expired token.
* [x] Test live order blocked with mismatched token.
* [x] Test live order blocked when kill switch active.
* [x] Test live order blocked when broker heartbeat fails.
* [x] Test live order blocked when audit unavailable.
* [x] Test Order Router is the only bridge caller.
* [x] Test direct bridge call rejection.
* [x] Test Audit Agent flags missing RiskGovernor approval.
* [x] Test critical audit finding disables live trading.
* [x] Test Cost Optimizer never routes risk/execution to LLM.
* [x] Test LLM cannot override deterministic portfolio decisions.
* [x] Test performance report marks missing data as incomplete.
* [x] Test incident resume requires approval after critical incident.

---

# 28. Recommended Build Order

## Checklist

* [x] Build shared portfolio contracts.
* [x] Build Strategy Lifecycle Agent.
* [x] Build Portfolio Manager Agent.
* [x] Build Allocation Optimizer Agent.
* [x] Build Paper Broker Service.
* [x] Build Paper Execution Agent.
* [x] Build Execution Readiness Agent.
* [x] Build MT5 bridge in dry-run mode.
* [x] Build cTrader bridge in dry-run mode.
* [x] Build Order Router Service.
* [x] Build Kill Switch Service.
* [x] Build Incident Agent.
* [x] Build Live Execution Agent with live mode disabled by default.
* [x] Build Performance Reporter Agent.
* [x] Build Audit Agent.
* [x] Build Cost Optimizer Agent.
* [x] Build Portfolio Orchestrator Agent.
* [x] Register portfolio agents with Planner.
* [x] Surface portfolio summaries through CEOChatGateway.
* [x] Keep live execution blocked until Board approval workflow is implemented.

---

# 29. Department Definition of Done

The Portfolio Department is complete only when:

```text
1. Every portfolio agent follows the HaruQuant agent template.
2. Every agent has contracts.py, prompts.py, deterministic_policy.py, tools.py, service.py, evaluator.py, README.md, and tests.
3. Every deterministic service has typed contracts, audit logs, and fail-closed behavior.
4. Strategy lifecycle states cannot be skipped.
5. Paper execution works with full risk checks and audit logs.
6. Live execution is disabled by default.
7. No live order can execute without RiskGovernor approval.
8. No live order can bypass Order Router.
9. No broker bridge can be called directly by specialist agents.
10. Kill Switch can block live execution.
11. Audit Agent can detect rule violations.
12. Critical audit failure disables live trading.
13. Performance Reporter generates daily, weekly, and monthly reports.
14. Cost Optimizer tracks model and compute cost without weakening safety.
15. Portfolio Manager can recommend lifecycle and allocation decisions.
16. Board approval is required for live allocation changes.
17. Planner and CEOChatGateway consume portfolio outputs through stable AgentResponse envelopes.
```

---

# 30. Final Portfolio Department Rule

```text
Research finds ideas.
Strategy Creation formalizes and codes strategies.
Simulation tests them.
RiskGovernor gates them.
Portfolio decides lifecycle and allocation.
Execution only acts on approved proposals.
Audit verifies every rule was followed.
Kill Switch stops everything when safety fails.
```

The Portfolio Department is where HaruQuant becomes a managed trading firm instead of a collection of individual strategies.
