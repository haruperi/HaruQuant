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

* [ ] Create `agents/portfolio/`.
* [ ] Create `agents/portfolio/portfolio_orchestrator_agent/`.
* [ ] Create `agents/portfolio/portfolio_manager_agent/`.
* [ ] Create `agents/portfolio/allocation_optimizer_agent/`.
* [ ] Create `agents/portfolio/strategy_lifecycle_agent/`.
* [ ] Create `agents/portfolio/paper_execution_agent/`.
* [ ] Create `agents/portfolio/live_execution_agent/`.
* [ ] Create `agents/portfolio/execution_readiness_agent/`.
* [ ] Create `agents/portfolio/performance_reporter_agent/`.
* [ ] Create `agents/portfolio/cost_optimizer_agent/`.
* [ ] Create `agents/portfolio/shared/`.
* [ ] Create `services/portfolio/`.
* [ ] Create `services/portfolio/paper_broker.py`.
* [ ] Create `services/portfolio/order_router.py`.
* [ ] Create `services/portfolio/kill_switch.py`.
* [ ] Create `services/portfolio/incident_service.py`.
* [ ] Create `services/portfolio/lifecycle_service.py`.
* [ ] Create `services/portfolio/allocation_service.py`.
* [ ] Create `services/portfolio/reporting_service.py`.
* [ ] Create `services/portfolio/cost_service.py`.
* [ ] Create `services/execution/`.
* [ ] Create `services/execution/bridges/`.
* [ ] Create `services/execution/bridges/mt5_bridge.py`.
* [ ] Create `services/execution/bridges/ctrader_bridge.py`.
* [ ] Create `services/execution/bridges/base_bridge.py`.
* [ ] Create `agents/audit/audit_agent/`.
* [ ] Create `agents/audit/shared/`.

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

* [ ] Create `agents/portfolio/portfolio_orchestrator_agent/__init__.py`.
* [ ] Create `agents/portfolio/portfolio_orchestrator_agent/agent.py`.
* [ ] Create `agents/portfolio/portfolio_orchestrator_agent/contracts.py`.
* [ ] Create `agents/portfolio/portfolio_orchestrator_agent/prompts.py`.
* [ ] Create `agents/portfolio/portfolio_orchestrator_agent/deterministic_policy.py`.
* [ ] Create `agents/portfolio/portfolio_orchestrator_agent/tools.py`.
* [ ] Create `agents/portfolio/portfolio_orchestrator_agent/service.py`.
* [ ] Create `agents/portfolio/portfolio_orchestrator_agent/evaluator.py`.
* [ ] Create `agents/portfolio/portfolio_orchestrator_agent/README.md`.
* [ ] Create required tests.
* [ ] Validate portfolio request type.
* [ ] Validate caller permission.
* [ ] Validate request context.
* [ ] Determine required evidence.
* [ ] Determine required agents/services.
* [ ] Route lifecycle requests to Portfolio Manager Agent.
* [ ] Route allocation requests to Allocation Optimizer Agent.
* [ ] Route paper execution requests to Paper Execution Agent.
* [ ] Route live execution requests to Live Execution Agent.
* [ ] Route readiness checks to Execution Readiness Agent.
* [ ] Route reporting requests to Performance Reporter Agent.
* [ ] Route cost requests to Cost Optimizer Agent.
* [ ] Route audit checks to Audit Agent.
* [ ] Route incidents to Incident Agent/Service.
* [ ] Merge portfolio evidence.
* [ ] Detect missing upstream evidence.
* [ ] Detect conflicting recommendations.
* [ ] Escalate Board-required decisions.
* [ ] Produce portfolio orchestration result.
* [ ] Save orchestration audit record.

## Required Evidence

* [ ] Strategy lifecycle state.
* [ ] RiskGovernor constraints.
* [ ] Latest risk memo.
* [ ] Backtest evidence package.
* [ ] Robustness report.
* [ ] Statistical validation report.
* [ ] Paper trading report.
* [ ] Live performance report.
* [ ] Execution health status.
* [ ] Audit health status.
* [ ] Cost budget status.

## LLM Responsibilities

* [ ] Summarize portfolio request.
* [ ] Explain evidence conflicts.
* [ ] Draft CEO-facing portfolio memo.
* [ ] Draft Board decision summary.
* [ ] Summarize recommended next actions.

## Deterministic Policy Rules

* [ ] Reject request if required evidence is missing.
* [ ] Reject live allocation changes without Board approval.
* [ ] Reject live execution routing if RiskGovernor is unavailable.
* [ ] Reject live execution routing if kill switch is active.
* [ ] Reject live execution routing if audit logging is unavailable.
* [ ] Escalate critical conflicts to Board workflow.
* [ ] Allow only read-only summaries unless a governed workflow is active.

## Allowed Actions

* [ ] `coordinate_portfolio_review`.
* [ ] `request_lifecycle_review`.
* [ ] `request_allocation_review`.
* [ ] `request_execution_readiness_check`.
* [ ] `request_report_generation`.
* [ ] `request_audit_check`.
* [ ] `escalate_to_board_workflow`.

## Blocked Actions

* [ ] `execute_trade`.
* [ ] `approve_risk`.
* [ ] `change_live_allocation_directly`.
* [ ] `resume_live_trading_after_critical_incident`.
* [ ] `modify_risk_thresholds`.

## Output Artifacts

* [ ] Portfolio orchestration plan.
* [ ] Required evidence list.
* [ ] Agent routing plan.
* [ ] Board escalation packet.
* [ ] Portfolio orchestration audit record.

## Tests Required

* [ ] Normal portfolio review request.
* [ ] Missing risk evidence rejection.
* [ ] Live allocation request without Board approval rejection.
* [ ] Kill switch active rejection.
* [ ] Audit unavailable rejection.
* [ ] LLM cannot override deterministic route blocking.

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

* [ ] Create `agents/portfolio/portfolio_manager_agent/__init__.py`.
* [ ] Create `agents/portfolio/portfolio_manager_agent/agent.py`.
* [ ] Create `agents/portfolio/portfolio_manager_agent/contracts.py`.
* [ ] Create `agents/portfolio/portfolio_manager_agent/prompts.py`.
* [ ] Create `agents/portfolio/portfolio_manager_agent/deterministic_policy.py`.
* [ ] Create `agents/portfolio/portfolio_manager_agent/tools.py`.
* [ ] Create `agents/portfolio/portfolio_manager_agent/service.py`.
* [ ] Create `agents/portfolio/portfolio_manager_agent/evaluator.py`.
* [ ] Create `agents/portfolio/portfolio_manager_agent/README.md`.
* [ ] Create required tests.
* [ ] Read strategy lifecycle table.
* [ ] Read strategy specification.
* [ ] Read strategy code review result.
* [ ] Read backtest result package.
* [ ] Read backtest diagnosis report.
* [ ] Read optimization comparator report.
* [ ] Read robustness result.
* [ ] Read statistical validation result.
* [ ] Read paper strategy performance.
* [ ] Read live strategy performance.
* [ ] Read correlation matrix.
* [ ] Read allocation limits.
* [ ] Read current capital allocation.
* [ ] Read RiskGovernor constraints.
* [ ] Read risk memo.
* [ ] Read execution health.
* [ ] Read audit status.
* [ ] Read cost status.
* [ ] Detect strategy lifecycle state.
* [ ] Detect missing lifecycle stages.
* [ ] Detect promotion eligibility.
* [ ] Detect demotion conditions.
* [ ] Detect pause conditions.
* [ ] Detect retirement conditions.
* [ ] Detect portfolio concentration risk.
* [ ] Detect strategy duplication.
* [ ] Detect correlated strategy clusters.
* [ ] Detect underperforming strategies.
* [ ] Detect paper-to-live candidates.
* [ ] Detect live allocation increase candidates.
* [ ] Detect live allocation decrease candidates.
* [ ] Recommend strategy promotions.
* [ ] Recommend strategy demotions.
* [ ] Recommend strategy retirement.
* [ ] Recommend capital allocation changes.
* [ ] Require Board approval for live allocation changes.
* [ ] Save portfolio decision memo.
* [ ] Save portfolio decision audit.

## Portfolio Decision Types

* [ ] `admit_to_paper`.
* [ ] `reject_strategy`.
* [ ] `promote_to_micro_live`.
* [ ] `increase_allocation`.
* [ ] `decrease_allocation`.
* [ ] `pause_strategy`.
* [ ] `resume_strategy`.
* [ ] `retire_strategy`.
* [ ] `hold_current_state`.
* [ ] `request_more_evidence`.

## Required Evidence

* [ ] Research evidence references.
* [ ] Strategy spec version.
* [ ] Strategy code hash.
* [ ] Backtest run IDs.
* [ ] Robustness scorecard.
* [ ] Statistical evidence rating.
* [ ] RiskGovernor constraints.
* [ ] Portfolio exposure snapshot.
* [ ] Correlation matrix.
* [ ] Paper performance snapshot.
* [ ] Live performance snapshot.
* [ ] Audit health status.

## LLM Responsibilities

* [ ] Explain portfolio trade-offs.
* [ ] Summarize strategy lifecycle evidence.
* [ ] Compare strategy candidates.
* [ ] Draft portfolio decision memo.
* [ ] Explain why a strategy was promoted, paused, or retired.

## Deterministic Policy Rules

* [ ] Reject `admit_to_paper` if strategy spec is missing.
* [ ] Reject `admit_to_paper` if strategy code review failed.
* [ ] Reject `admit_to_paper` if minimum simulation evidence is missing.
* [ ] Reject `promote_to_micro_live` if paper trading period is incomplete.
* [ ] Reject `promote_to_micro_live` if RiskGovernor constraints fail.
* [ ] Reject `promote_to_micro_live` if audit logs are incomplete.
* [ ] Reject `increase_allocation` if drawdown exceeds policy.
* [ ] Reject `increase_allocation` if strategy correlation exceeds limit.
* [ ] Reject `increase_allocation` if cost-adjusted performance is weak.
* [ ] Require Board approval for all live allocation changes.
* [ ] Require signed decision record for lifecycle state changes.
* [ ] Fail closed when lifecycle evidence is inconsistent.

## Allowed Actions

* [ ] `recommend_admit_to_paper`.
* [ ] `recommend_reject_strategy`.
* [ ] `recommend_promote_to_micro_live`.
* [ ] `recommend_increase_allocation`.
* [ ] `recommend_decrease_allocation`.
* [ ] `recommend_pause_strategy`.
* [ ] `recommend_retire_strategy`.
* [ ] `request_more_evidence`.

## Blocked Actions

* [ ] `execute_trade`.
* [ ] `approve_risk`.
* [ ] `directly_change_live_allocation`.
* [ ] `bypass_board_approval`.
* [ ] `modify_risk_thresholds`.

## Output Artifacts

* [ ] Portfolio decision memo.
* [ ] Strategy lifecycle decision.
* [ ] Allocation recommendation.
* [ ] Board approval request.
* [ ] Evidence references.
* [ ] Audit record.

## Tests Required

* [ ] Admit-to-paper normal case.
* [ ] Reject missing strategy spec.
* [ ] Reject missing backtest evidence.
* [ ] Reject live promotion without paper history.
* [ ] Reject allocation increase due to correlation.
* [ ] Require Board approval for live allocation change.
* [ ] LLM cannot override deterministic lifecycle rejection.

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

* [ ] Create standard agent files.
* [ ] Read current allocation table.
* [ ] Read available capital.
* [ ] Read strategy lifecycle state.
* [ ] Read strategy risk budgets.
* [ ] Read strategy volatility.
* [ ] Read strategy drawdown.
* [ ] Read strategy Sharpe/Sortino/Omega.
* [ ] Read strategy expected trade frequency.
* [ ] Read strategy live/paper confidence.
* [ ] Read strategy correlation matrix.
* [ ] Read symbol exposure.
* [ ] Read currency-cluster exposure.
* [ ] Read RiskGovernor allocation constraints.
* [ ] Read max strategy allocation.
* [ ] Read max symbol allocation.
* [ ] Read max cluster allocation.
* [ ] Read max portfolio margin usage.
* [ ] Compute equal-capital allocation.
* [ ] Compute volatility-adjusted allocation.
* [ ] Compute drawdown-adjusted allocation.
* [ ] Compute risk-parity-style allocation.
* [ ] Compute confidence-weighted allocation.
* [ ] Compute constrained allocation proposal.
* [ ] Detect overconcentrated strategies.
* [ ] Detect underutilized robust strategies.
* [ ] Detect allocation cliffs.
* [ ] Detect correlated allocation clusters.
* [ ] Recommend capital increases.
* [ ] Recommend capital decreases.
* [ ] Recommend capped allocation.
* [ ] Recommend no-change decision.
* [ ] Produce allocation proposal.
* [ ] Save allocation audit.

## Deterministic Policy Rules

* [ ] Reject allocation proposal if total allocation exceeds capital.
* [ ] Reject allocation proposal if strategy is not eligible.
* [ ] Reject allocation proposal if max strategy allocation exceeded.
* [ ] Reject allocation proposal if symbol concentration exceeded.
* [ ] Reject allocation proposal if correlation concentration exceeded.
* [ ] Reject allocation proposal if RiskGovernor constraints fail.
* [ ] Require Board approval for live allocation increases.
* [ ] Fail closed if allocation table is stale.

## Output Artifacts

* [ ] Allocation proposal.
* [ ] Allocation constraint report.
* [ ] Strategy-level allocation table.
* [ ] Symbol-level exposure table.
* [ ] Cluster-level exposure table.
* [ ] Board approval request if needed.

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

* [ ] `idea`.
* [ ] `spec`.
* [ ] `coded`.
* [ ] `reviewed`.
* [ ] `backtested`.
* [ ] `diagnosed`.
* [ ] `optimized`.
* [ ] `robustness_tested`.
* [ ] `statistically_validated`.
* [ ] `paper_candidate`.
* [ ] `paper_live`.
* [ ] `micro_live_candidate`.
* [ ] `micro_live`.
* [ ] `live_candidate`.
* [ ] `live`.
* [ ] `paused`.
* [ ] `retired`.
* [ ] `rejected`.

## Checklist

* [ ] Create standard agent files.
* [ ] Read current lifecycle table.
* [ ] Read requested lifecycle transition.
* [ ] Validate allowed transition path.
* [ ] Validate required evidence for transition.
* [ ] Validate required approvals for transition.
* [ ] Validate strategy code hash.
* [ ] Validate strategy spec version.
* [ ] Validate simulation evidence.
* [ ] Validate risk evidence.
* [ ] Validate audit evidence.
* [ ] Validate Board approval where required.
* [ ] Update lifecycle state only through governed service.
* [ ] Record transition reason.
* [ ] Record transition actor.
* [ ] Record transition timestamp.
* [ ] Record evidence references.
* [ ] Record old state and new state.
* [ ] Block invalid transitions.
* [ ] Save lifecycle audit.

## Deterministic Policy Rules

* [ ] Reject transitions that skip mandatory stages.
* [ ] Reject live transition without Board approval.
* [ ] Reject live transition without RiskGovernor compatibility.
* [ ] Reject paper transition without strategy review.
* [ ] Reject micro-live transition without paper trading evidence.
* [ ] Reject resume transition after critical incident without approval.
* [ ] Fail closed if lifecycle table is stale or inconsistent.

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

* [ ] Create `services/portfolio/paper_broker.py`.
* [ ] Define `PaperBrokerConfig`.
* [ ] Define `PaperOrderRequest`.
* [ ] Define `PaperOrderResult`.
* [ ] Define `PaperPosition`.
* [ ] Define `PaperAccountState`.
* [ ] Simulate market orders.
* [ ] Simulate limit orders.
* [ ] Simulate stop orders.
* [ ] Simulate pending order fills.
* [ ] Simulate partial fills if enabled.
* [ ] Simulate rejection conditions.
* [ ] Simulate spread.
* [ ] Simulate slippage.
* [ ] Simulate commission.
* [ ] Simulate swap.
* [ ] Simulate margin usage.
* [ ] Simulate margin call behavior if enabled.
* [ ] Track open positions.
* [ ] Track pending orders.
* [ ] Track realized P&L.
* [ ] Track unrealized P&L.
* [ ] Track balance.
* [ ] Track equity.
* [ ] Track margin.
* [ ] Track free margin.
* [ ] Track order history.
* [ ] Track deals.
* [ ] Save execution logs.
* [ ] Save broker state snapshots.
* [ ] Support deterministic replay.
* [ ] Support reset between paper runs.

## Deterministic Policy Rules

* [ ] Reject orders with invalid symbol.
* [ ] Reject orders with invalid volume.
* [ ] Reject orders with invalid side.
* [ ] Reject orders with insufficient margin.
* [ ] Reject orders when paper mode disabled.
* [ ] Reject orders without RiskGovernor paper approval if required.
* [ ] Reject orders if audit logging is unavailable.

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

* [ ] Create standard agent files.
* [ ] Read approved paper strategies.
* [ ] Validate strategy lifecycle state is `paper_live`.
* [ ] Read strategy signal.
* [ ] Validate signal schema.
* [ ] Create trade proposal.
* [ ] Call RiskGovernor in paper mode.
* [ ] Validate paper approval token.
* [ ] Send approved order to paper broker.
* [ ] Log paper order request.
* [ ] Log paper broker response.
* [ ] Log simulated slippage.
* [ ] Log simulated spread.
* [ ] Log position update.
* [ ] Log rejection reason.
* [ ] Report anomalies.
* [ ] Save paper execution audit.

## Paper Trading Promotion Criteria

* [ ] Minimum 30 trading days.
* [ ] Minimum trade count.
* [ ] Max drawdown within limit.
* [ ] Daily loss within limit.
* [ ] Weekly loss within limit.
* [ ] Slippage within expected range.
* [ ] Live-like spread assumptions.
* [ ] No execution anomalies.
* [ ] No RiskGovernor violations.
* [ ] No audit gaps.
* [ ] Performance within expected confidence interval.
* [ ] Behavior consistent with backtest expectation.

## Deterministic Policy Rules

* [ ] Block if paper mode disabled.
* [ ] Block if strategy not in approved paper lifecycle state.
* [ ] Block if approval token missing.
* [ ] Block if approval token expired.
* [ ] Block if token does not match symbol.
* [ ] Block if token does not match side.
* [ ] Block if token does not match approved size.
* [ ] Block if paper broker unavailable.
* [ ] Block if audit logging unavailable.
* [ ] Block if RiskGovernor unavailable.

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

* [ ] Create standard agent files.
* [ ] Read approved live strategies.
* [ ] Validate strategy lifecycle state is live-enabled.
* [ ] Listen for strategy signals.
* [ ] Validate signal schema.
* [ ] Validate strategy code hash.
* [ ] Validate strategy config hash.
* [ ] Validate live mode enabled.
* [ ] Validate Board approval for strategy live status.
* [ ] Create trade proposal.
* [ ] Call RiskGovernor.
* [ ] Validate approval token.
* [ ] Validate approval token expiration.
* [ ] Validate approval token signature.
* [ ] Validate approval token symbol.
* [ ] Validate approval token side.
* [ ] Validate approval token size.
* [ ] Validate kill switch status.
* [ ] Validate broker heartbeat.
* [ ] Validate audit logger health.
* [ ] Call order router.
* [ ] Log order request.
* [ ] Log broker response.
* [ ] Log execution latency.
* [ ] Log spread at execution.
* [ ] Log slippage.
* [ ] Log commission.
* [ ] Log swap estimate where available.
* [ ] Log position update.
* [ ] Log rejected order reason.
* [ ] Report execution anomalies.
* [ ] Save live execution audit.

## Execution Safety

* [ ] Block if live mode disabled.
* [ ] Block if strategy not live.
* [ ] Block if strategy lifecycle state is not live-enabled.
* [ ] Block if Board approval missing.
* [ ] Block if approval token missing.
* [ ] Block if approval token expired.
* [ ] Block if approval token signature invalid.
* [ ] Block if approval token mismatches order.
* [ ] Block if kill switch triggered.
* [ ] Block if broker heartbeat failed.
* [ ] Block if spread too high.
* [ ] Block if slippage too high.
* [ ] Block if audit logging unavailable.
* [ ] Block if RiskGovernor unavailable.
* [ ] Block if broker bridge is degraded.
* [ ] Block if repeated order failures exceed limit.

## LLM Responsibilities

* [ ] Explain rejected live order reasons.
* [ ] Summarize execution anomalies.
* [ ] Draft execution incident summaries.
* [ ] Explain live execution health status.

## Deterministic Policy Rules

* [ ] Never execute without a valid RiskGovernor approval token.
* [ ] Never execute if approval token does not match order exactly.
* [ ] Never execute if kill switch is active.
* [ ] Never execute if audit logging is unavailable.
* [ ] Never execute if broker heartbeat is stale.
* [ ] Never execute if strategy lifecycle state is not live-enabled.
* [ ] Never execute if live mode is disabled.
* [ ] Fail closed on any unknown broker or risk state.

## Output Artifacts

* [ ] Trade proposal.
* [ ] Risk approval token reference.
* [ ] Order request record.
* [ ] Broker response record.
* [ ] Execution anomaly report.
* [ ] Live execution audit.

## Tests Required

* [ ] Valid live proposal with valid token routes to order router.
* [ ] Missing token blocks execution.
* [ ] Expired token blocks execution.
* [ ] Mismatched size blocks execution.
* [ ] Kill switch active blocks execution.
* [ ] Broker heartbeat failure blocks execution.
* [ ] Audit unavailable blocks execution.
* [ ] LLM cannot override execution block.

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

* [ ] Create standard agent files.
* [ ] Read live mode configuration.
* [ ] Read Board live approval state.
* [ ] Read RiskGovernor health.
* [ ] Read kill switch health.
* [ ] Read audit logger health.
* [ ] Read MT5 bridge health.
* [ ] Read cTrader bridge health.
* [ ] Read order router health.
* [ ] Read broker heartbeat.
* [ ] Read broker account info.
* [ ] Read broker symbol metadata.
* [ ] Read spread conditions.
* [ ] Read slippage conditions.
* [ ] Read open positions.
* [ ] Read pending orders.
* [ ] Read recent order failures.
* [ ] Check permission profile.
* [ ] Check secrets/config availability without exposing secrets.
* [ ] Check environment mode.
* [ ] Check execution disabled-by-default policy.
* [ ] Output readiness status.
* [ ] Output blocking issues.
* [ ] Output warning issues.
* [ ] Save readiness audit.

## Deterministic Policy Rules

* [ ] Mark `not_ready` if RiskGovernor unavailable.
* [ ] Mark `not_ready` if audit logger unavailable.
* [ ] Mark `not_ready` if kill switch unavailable.
* [ ] Mark `not_ready` if broker heartbeat failed.
* [ ] Mark `not_ready` if order router unavailable.
* [ ] Mark `not_ready` if live mode config is inconsistent.
* [ ] Mark `ready_but_disabled` if infrastructure is healthy but live mode is off.
* [ ] Never enable live trading directly.

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

* [ ] Create `services/execution/bridges/base_bridge.py`.
* [ ] Create `services/execution/bridges/mt5_bridge.py`.
* [ ] Implement `connect`.
* [ ] Implement `disconnect`.
* [ ] Implement `heartbeat`.
* [ ] Implement `get_account_info`.
* [ ] Implement `get_symbol_info`.
* [ ] Implement `get_latest_tick`.
* [ ] Implement `get_open_positions`.
* [ ] Implement `get_pending_orders`.
* [ ] Implement `place_order`.
* [ ] Implement `modify_order`.
* [ ] Implement `close_position`.
* [ ] Implement `cancel_order`.
* [ ] Implement reconnection logic.
* [ ] Implement broker timeout handling.
* [ ] Implement broker error normalization.
* [ ] Implement symbol metadata normalization.
* [ ] Implement pip/tick value normalization.
* [ ] Implement volume step normalization.
* [ ] Implement min/max volume validation.
* [ ] Implement execution audit logs.
* [ ] Implement idempotency protection.
* [ ] Implement duplicate-order prevention.
* [ ] Implement dry-run mode.
* [ ] Implement paper/simulated mode compatibility.

## Deterministic Policy Rules

* [ ] Never place an order unless called by Order Router.
* [ ] Reject direct calls from agents.
* [ ] Reject live orders when live mode disabled.
* [ ] Reject orders without validated RiskGovernor approval token.
* [ ] Reject orders with invalid normalized symbol metadata.
* [ ] Reject orders with invalid volume step.
* [ ] Fail closed on broker uncertainty.

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

* [ ] Create `services/execution/bridges/ctrader_bridge.py`.
* [ ] Match same interface as MT5 bridge.
* [ ] Implement `connect`.
* [ ] Implement `disconnect`.
* [ ] Implement `heartbeat`.
* [ ] Implement `get_account_info`.
* [ ] Implement `get_symbol_info`.
* [ ] Implement `get_latest_tick`.
* [ ] Implement `get_open_positions`.
* [ ] Implement `get_pending_orders`.
* [ ] Implement `place_order`.
* [ ] Implement `modify_order`.
* [ ] Implement `close_position`.
* [ ] Implement `cancel_order`.
* [ ] Normalize symbol metadata.
* [ ] Normalize pip/tick values.
* [ ] Normalize volume units.
* [ ] Normalize order status.
* [ ] Normalize position status.
* [ ] Normalize error codes.
* [ ] Add reconnection logic.
* [ ] Add heartbeat.
* [ ] Add broker error handling.
* [ ] Add execution audit logs.
* [ ] Add dry-run mode.

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

* [ ] Create `services/portfolio/order_router.py`.
* [ ] Define `OrderRouteRequest`.
* [ ] Define `OrderRouteResult`.
* [ ] Read approved broker bridge.
* [ ] Read live mode flag.
* [ ] Read strategy live status.
* [ ] Read kill switch status.
* [ ] Read broker heartbeat status.
* [ ] Read audit logger health.
* [ ] Validate RiskGovernor approval token.
* [ ] Validate token expiration.
* [ ] Validate token signature.
* [ ] Validate token proposal ID.
* [ ] Validate token strategy ID.
* [ ] Validate token symbol.
* [ ] Validate token side.
* [ ] Validate token approved size.
* [ ] Validate order type.
* [ ] Validate normalized broker metadata.
* [ ] Validate max spread.
* [ ] Validate max slippage.
* [ ] Reject stale approval tokens.
* [ ] Reject mismatched order size.
* [ ] Reject mismatched symbol.
* [ ] Reject mismatched side.
* [ ] Reject mismatched order type.
* [ ] Reject if broker heartbeat unhealthy.
* [ ] Reject if audit logging unavailable.
* [ ] Route order to MT5 bridge if broker is MT5.
* [ ] Route order to cTrader bridge if broker is cTrader.
* [ ] Log all rejected orders.
* [ ] Log all routed orders.
* [ ] Log broker responses.

## Deterministic Policy Rules

* [ ] Order Router is the only service allowed to call live bridge order placement.
* [ ] Never route without a valid RiskGovernor token.
* [ ] Never route when kill switch is triggered.
* [ ] Never route when live mode is disabled.
* [ ] Never route when broker heartbeat is unhealthy.
* [ ] Never route when audit logging is unavailable.
* [ ] Fail closed on any mismatch.

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

* [ ] Create `services/portfolio/kill_switch.py`.
* [ ] Define kill switch states.
* [ ] Define trigger severity.
* [ ] Define trigger policy config.
* [ ] Monitor daily loss.
* [ ] Monitor weekly loss.
* [ ] Monitor account drawdown.
* [ ] Monitor strategy drawdown.
* [ ] Monitor symbol drawdown.
* [ ] Monitor portfolio exposure.
* [ ] Monitor broker connection.
* [ ] Monitor broker heartbeat.
* [ ] Monitor spread spikes.
* [ ] Monitor slippage spikes.
* [ ] Monitor repeated order failures.
* [ ] Monitor execution latency spikes.
* [ ] Monitor audit logger health.
* [ ] Monitor RiskGovernor health.
* [ ] Monitor data feed health.
* [ ] Monitor price staleness.
* [ ] Monitor abnormal fills.
* [ ] Disable new orders if triggered.
* [ ] Optionally close positions based on policy.
* [ ] Block strategy resumes after critical incident.
* [ ] Write incident report.
* [ ] Emit alert.
* [ ] Save kill switch audit.

## Kill Switch States

* [ ] `healthy`.
* [ ] `warning`.
* [ ] `new_orders_blocked`.
* [ ] `position_reduction_only`.
* [ ] `close_all_required`.
* [ ] `manual_review_required`.
* [ ] `critical_shutdown`.

## Deterministic Policy Rules

* [ ] Trigger if daily loss exceeds configured limit.
* [ ] Trigger if weekly loss exceeds configured limit.
* [ ] Trigger if account drawdown exceeds configured limit.
* [ ] Trigger if broker heartbeat fails beyond allowed window.
* [ ] Trigger if repeated order failures exceed threshold.
* [ ] Trigger if audit logging is unavailable.
* [ ] Trigger if RiskGovernor unavailable.
* [ ] Critical trigger disables live trading.
* [ ] Resume after critical trigger requires human approval.
* [ ] Fail closed if kill switch state cannot be determined.

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

* [ ] Create standard agent files.
* [ ] Read incident trigger.
* [ ] Read kill switch state.
* [ ] Read affected strategies.
* [ ] Read affected symbols.
* [ ] Read open positions.
* [ ] Read pending orders.
* [ ] Read recent broker responses.
* [ ] Read recent rejected orders.
* [ ] Read RiskGovernor state.
* [ ] Read audit logger state.
* [ ] Read execution bridge state.
* [ ] Summarize incident.
* [ ] Identify trigger.
* [ ] Identify severity.
* [ ] Identify affected strategies.
* [ ] Identify affected open positions.
* [ ] Identify immediate required action.
* [ ] Recommend pause/resume/close/reduce/hold.
* [ ] Require human approval to resume live trading after critical incidents.
* [ ] Produce incident memo.
* [ ] Save incident audit.

## Deterministic Policy Rules

* [ ] Block resume recommendation if critical incident unresolved.
* [ ] Block resume recommendation without human approval after critical incident.
* [ ] Mark incident as critical if audit logging failed during live execution.
* [ ] Mark incident as critical if RiskGovernor failed during live execution.
* [ ] Mark incident as critical if unauthorized order detected.
* [ ] Fail closed on unknown broker state.

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

* [ ] Create standard agent files.
* [ ] Read portfolio P&L.
* [ ] Read open exposure.
* [ ] Read realized P&L.
* [ ] Read unrealized P&L.
* [ ] Read drawdown.
* [ ] Read trade count.
* [ ] Read active strategies.
* [ ] Read paper strategies.
* [ ] Read live strategies.
* [ ] Read rejected trades.
* [ ] Read RiskGovernor blocks.
* [ ] Read execution anomalies.
* [ ] Read cost usage.
* [ ] Read audit findings.
* [ ] Generate daily report.
* [ ] Generate weekly Board report.
* [ ] Generate monthly strategy review.
* [ ] Generate strategy-level health report.
* [ ] Generate portfolio-level health report.
* [ ] Generate allocation change summary.
* [ ] Generate decision-required summary.
* [ ] Save report artifacts.
* [ ] Save report audit.

## Daily Report Checklist

* [ ] Report daily P&L.
* [ ] Report open exposure.
* [ ] Report drawdown.
* [ ] Report trade count.
* [ ] Report strategy health.
* [ ] Report rejected trades.
* [ ] Report RiskGovernor blocks.
* [ ] Report execution anomalies.
* [ ] Report cost usage.
* [ ] Report audit warnings.
* [ ] Report next actions.

## Weekly Board Report Checklist

* [ ] Summarize portfolio performance.
* [ ] Summarize paper strategies.
* [ ] Summarize live strategies.
* [ ] Summarize new research.
* [ ] Summarize backtests.
* [ ] Summarize robustness tests.
* [ ] Summarize risk events.
* [ ] Summarize execution events.
* [ ] Summarize audit events.
* [ ] Summarize cost usage.
* [ ] List decisions required from Board/user.

## Monthly Strategy Review Checklist

* [ ] Rank active strategies.
* [ ] Rank paper strategies.
* [ ] Identify underperformers.
* [ ] Identify promotion candidates.
* [ ] Identify retirement candidates.
* [ ] Identify correlated strategy clusters.
* [ ] Identify cost-heavy strategies.
* [ ] Identify overtrading strategies.
* [ ] Recommend allocation changes.
* [ ] Recommend lifecycle changes.

## Deterministic Policy Rules

* [ ] Reject report generation if required data is missing.
* [ ] Mark report incomplete if audit gaps exist.
* [ ] Mark report incomplete if execution logs are missing.
* [ ] Never change allocation from a report.
* [ ] Never approve strategy promotion from a report.
* [ ] Escalate critical audit/risk findings.

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

* [ ] Create `agents/audit/audit_agent/__init__.py`.
* [ ] Create `agents/audit/audit_agent/agent.py`.
* [ ] Create `agents/audit/audit_agent/contracts.py`.
* [ ] Create `agents/audit/audit_agent/prompts.py`.
* [ ] Create `agents/audit/audit_agent/deterministic_policy.py`.
* [ ] Create `agents/audit/audit_agent/tools.py`.
* [ ] Create `agents/audit/audit_agent/service.py`.
* [ ] Create `agents/audit/audit_agent/evaluator.py`.
* [ ] Create `agents/audit/audit_agent/README.md`.
* [ ] Create required tests.
* [ ] Check every live order has RiskGovernor approval.
* [ ] Check every approval token matches executed order.
* [ ] Check approval token was not expired at execution time.
* [ ] Check approval token signature/hash.
* [ ] Check no agent changed risk thresholds.
* [ ] Check no strategy skipped lifecycle stages.
* [ ] Check no live strategy lacks Board approval.
* [ ] Check no missing evidence refs.
* [ ] Check no missing execution logs.
* [ ] Check no missing broker responses.
* [ ] Check no missing order-router logs.
* [ ] Check no missing RiskGovernor audit records.
* [ ] Check no hidden failed tool calls.
* [ ] Check no direct bridge calls bypassed Order Router.
* [ ] Check no direct execution call came from specialist agents.
* [ ] Check no live trading occurred while kill switch was active.
* [ ] Check no live trading occurred while audit logger was unhealthy.
* [ ] Check no live trading occurred while RiskGovernor was unavailable.
* [ ] Generate daily audit report.
* [ ] Generate critical audit alert.
* [ ] Save audit evidence.

## Audit Severity

* [ ] `info`.
* [ ] `warning`.
* [ ] `major`.
* [ ] `critical`.

## Deterministic Policy Rules

* [ ] Critical audit failure disables live trading.
* [ ] Major audit failure blocks new live orders until reviewed.
* [ ] Missing RiskGovernor token on live order is critical.
* [ ] Token/order mismatch is critical.
* [ ] Direct bridge call bypassing router is critical.
* [ ] Missing broker response on live order is major or critical.
* [ ] Missing audit record is major or critical.
* [ ] Unknown execution state is critical.

## Allowed Actions

* [ ] `generate_audit_report`.
* [ ] `flag_audit_issue`.
* [ ] `escalate_critical_audit_failure`.
* [ ] `request_live_trading_disable`.

## Blocked Actions

* [ ] `execute_trade`.
* [ ] `approve_risk`.
* [ ] `modify_risk_thresholds`.
* [ ] `resume_live_trading`.

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

* [ ] Create standard agent files.
* [ ] Track model provider.
* [ ] Track model name.
* [ ] Track prompt tokens.
* [ ] Track completion tokens.
* [ ] Track total tokens.
* [ ] Track cost per task.
* [ ] Track cost per agent.
* [ ] Track cost per workflow.
* [ ] Track cost per department.
* [ ] Track cost per strategy.
* [ ] Track failed-call cost.
* [ ] Track retry cost.
* [ ] Track backtest compute cost.
* [ ] Track optimization compute cost.
* [ ] Track Monte Carlo compute cost.
* [ ] Track data storage cost.
* [ ] Track report generation cost.
* [ ] Track cost per accepted strategy.
* [ ] Track cost per rejected strategy.
* [ ] Track cost per live candidate.
* [ ] Track budget usage.
* [ ] Detect cost anomalies.
* [ ] Recommend cheaper model routing.
* [ ] Recommend cache usage.
* [ ] Recommend batch processing.
* [ ] Recommend local model usage.
* [ ] Produce daily cost report.
* [ ] Produce weekly cost report.
* [ ] Produce monthly cost report.
* [ ] Save cost audit.

## Model Routing Rules

* [ ] Use strong model for CEO decisions.
* [ ] Use strong model for risk memos.
* [ ] Use strong coding model for strategy code generation.
* [ ] Use cheaper model for formatting reports.
* [ ] Use cheaper model for simple summaries.
* [ ] Use local model for low-risk summarization if quality is acceptable.
* [ ] Use deterministic code for risk approvals.
* [ ] Use deterministic code for order placement.
* [ ] Use no LLM for RiskGovernor decisions.
* [ ] Use no LLM for Order Router decisions.
* [ ] Use no LLM for Kill Switch decisions.

## Deterministic Policy Rules

* [ ] Never weaken risk controls to reduce cost.
* [ ] Never route RiskGovernor decisions to an LLM.
* [ ] Never route execution decisions to an LLM.
* [ ] Reject model routing if permission profile disallows it.
* [ ] Alert if cost exceeds budget.
* [ ] Alert if failed-call cost exceeds threshold.
* [ ] Alert if one strategy consumes abnormal cost.
* [ ] Alert if one workflow consumes abnormal cost.

## Cost Reports

* [ ] Daily cost report.
* [ ] Weekly cost report.
* [ ] Monthly cost report.
* [ ] Cost per accepted strategy.
* [ ] Cost per rejected strategy.
* [ ] Cost per live candidate.
* [ ] Cost per department.
* [ ] Cost per model provider.
* [ ] Cost anomaly alerts.

## Done Definition

Agents become economically manageable without compromising safety.

---

# 18. Shared Portfolio Contracts

## Goal

Define the machine-readable contracts used across the Portfolio Department.

## Checklist

* [ ] Create `agents/portfolio/shared/contracts.py`.
* [ ] Add `PortfolioRequest`.
* [ ] Add `PortfolioDecision`.
* [ ] Add `StrategyLifecycleState`.
* [ ] Add `LifecycleTransitionRequest`.
* [ ] Add `LifecycleTransitionResult`.
* [ ] Add `AllocationProposal`.
* [ ] Add `AllocationDecision`.
* [ ] Add `ExecutionProposal`.
* [ ] Add `ExecutionDecision`.
* [ ] Add `PaperOrderRequest`.
* [ ] Add `PaperOrderResult`.
* [ ] Add `LiveOrderRequest`.
* [ ] Add `LiveOrderResult`.
* [ ] Add `OrderRouteRequest`.
* [ ] Add `OrderRouteResult`.
* [ ] Add `BrokerHealthSnapshot`.
* [ ] Add `ExecutionHealthSnapshot`.
* [ ] Add `KillSwitchState`.
* [ ] Add `IncidentReport`.
* [ ] Add `PerformanceReport`.
* [ ] Add `AuditFinding`.
* [ ] Add `CostReport`.

## Done Definition

All Portfolio Department agents and services exchange typed contracts instead of loose dictionaries.

---

# 19. Portfolio Decision Schema

## Checklist

* [ ] Add `decision_id`.
* [ ] Add `decision_type`.
* [ ] Add `strategy_id`.
* [ ] Add `strategy_name`.
* [ ] Add `current_lifecycle_state`.
* [ ] Add `proposed_lifecycle_state`.
* [ ] Add `current_allocation`.
* [ ] Add `proposed_allocation`.
* [ ] Add `symbol_exposure_change`.
* [ ] Add `currency_cluster_exposure_change`.
* [ ] Add `correlation_impact`.
* [ ] Add `risk_governor_constraints`.
* [ ] Add `evidence_refs`.
* [ ] Add `required_approval_level`.
* [ ] Add `board_approval_required`.
* [ ] Add `board_approval_id`.
* [ ] Add `decision_status`.
* [ ] Add `allowed_actions`.
* [ ] Add `blocked_actions`.
* [ ] Add `reasons`.
* [ ] Add `confidence`.
* [ ] Add `risk_level`.
* [ ] Add `created_at`.
* [ ] Add `expires_at` if applicable.
* [ ] Add `audit_ref`.

---

# 20. Execution Proposal Schema

## Checklist

* [ ] Add `proposal_id`.
* [ ] Add `strategy_id`.
* [ ] Add `strategy_name`.
* [ ] Add `strategy_code_hash`.
* [ ] Add `strategy_config_hash`.
* [ ] Add `symbol`.
* [ ] Add `side`.
* [ ] Add `order_type`.
* [ ] Add `requested_volume`.
* [ ] Add `requested_price`.
* [ ] Add `stop_loss`.
* [ ] Add `take_profit`.
* [ ] Add `signal_time`.
* [ ] Add `proposal_time`.
* [ ] Add `signal_reason`.
* [ ] Add `setup_id`.
* [ ] Add `group_id`.
* [ ] Add `metadata`.
* [ ] Add `risk_mode`.
* [ ] Add `execution_mode`.
* [ ] Add `evidence_refs`.

---

# 21. Execution Result Schema

## Checklist

* [ ] Add `execution_id`.
* [ ] Add `proposal_id`.
* [ ] Add `approval_id`.
* [ ] Add `broker`.
* [ ] Add `bridge_name`.
* [ ] Add `symbol`.
* [ ] Add `side`.
* [ ] Add `order_type`.
* [ ] Add `requested_volume`.
* [ ] Add `executed_volume`.
* [ ] Add `requested_price`.
* [ ] Add `executed_price`.
* [ ] Add `spread_at_execution`.
* [ ] Add `slippage`.
* [ ] Add `commission`.
* [ ] Add `swap_estimate`.
* [ ] Add `broker_order_id`.
* [ ] Add `broker_position_id`.
* [ ] Add `broker_response_code`.
* [ ] Add `broker_response_message`.
* [ ] Add `status`.
* [ ] Add `rejection_reason`.
* [ ] Add `created_at`.
* [ ] Add `audit_ref`.

---

# 22. Incident Report Schema

## Checklist

* [ ] Add `incident_id`.
* [ ] Add `incident_type`.
* [ ] Add `severity`.
* [ ] Add `trigger`.
* [ ] Add `trigger_time`.
* [ ] Add `detected_by`.
* [ ] Add `affected_strategies`.
* [ ] Add `affected_symbols`.
* [ ] Add `affected_orders`.
* [ ] Add `affected_positions`.
* [ ] Add `kill_switch_state_before`.
* [ ] Add `kill_switch_state_after`.
* [ ] Add `risk_governor_state`.
* [ ] Add `broker_state`.
* [ ] Add `audit_state`.
* [ ] Add `immediate_action_taken`.
* [ ] Add `recommended_next_action`.
* [ ] Add `resume_allowed`.
* [ ] Add `human_approval_required`.
* [ ] Add `evidence_refs`.
* [ ] Add `audit_ref`.

---

# 23. Portfolio Permissions Model

## Checklist

* [ ] Create `portfolio_read_only_v1` permission profile.
* [ ] Create `portfolio_lifecycle_recommendation_v1` permission profile.
* [ ] Create `portfolio_allocation_recommendation_v1` permission profile.
* [ ] Create `paper_execution_v1` permission profile.
* [ ] Create `live_execution_guarded_v1` permission profile.
* [ ] Create `execution_bridge_internal_v1` permission profile.
* [ ] Create `audit_read_only_v1` permission profile.
* [ ] Create `cost_read_only_v1` permission profile.
* [ ] Block all direct execution permissions from research agents.
* [ ] Block all direct execution permissions from strategy creation agents.
* [ ] Block all direct execution permissions from simulation agents.
* [ ] Block all direct execution permissions from reporting agents.

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

* [ ] Every portfolio decision must include `decision_id`.
* [ ] Every lifecycle transition must include old state and new state.
* [ ] Every allocation recommendation must include evidence refs.
* [ ] Every live allocation change must include Board approval ref.
* [ ] Every paper order must include paper approval/risk ref if required.
* [ ] Every live order must include RiskGovernor approval token.
* [ ] Every order router rejection must be logged.
* [ ] Every broker response must be logged.
* [ ] Every execution anomaly must be logged.
* [ ] Every kill switch trigger must be logged.
* [ ] Every resume action must be logged.
* [ ] Every incident must have an incident report.
* [ ] Every cost report must include provider/model/task metadata.
* [ ] Every audit report must include severity.

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

* [ ] Receive market context affecting portfolio allocation.
* [ ] Receive strategy idea lineage.
* [ ] Receive evidence references.
* [ ] Receive macro/sentiment warnings.
* [ ] Receive correlation regime warnings.

## Strategy Creation to Portfolio

* [ ] Receive strategy spec.
* [ ] Receive strategy code hash.
* [ ] Receive strategy review result.
* [ ] Receive strategy README.
* [ ] Receive strategy tests result.

## Simulation to Portfolio

* [ ] Receive backtest run package.
* [ ] Receive diagnosis report.
* [ ] Receive optimization comparison.
* [ ] Receive robustness scorecard.
* [ ] Receive statistical validation result.
* [ ] Receive evidence quality rating.

## Risk to Portfolio

* [ ] Receive RiskGovernor constraints.
* [ ] Receive risk memo.
* [ ] Receive portfolio exposure limits.
* [ ] Receive approved/rejected proposal result.
* [ ] Receive risk approval tokens.

## Portfolio to Execution

* [ ] Send only approved live strategy status.
* [ ] Send strategy allocation limits.
* [ ] Send execution proposals.
* [ ] Send Board approval refs.
* [ ] Send RiskGovernor approval token to Order Router.

## Portfolio to CEO/Board

* [ ] Send portfolio decision memo.
* [ ] Send Board approval request.
* [ ] Send weekly Board report.
* [ ] Send incident escalation memo.
* [ ] Send cost anomaly report.

---

# 27. Standard Tests for Portfolio Department

## Checklist

* [ ] Test all contracts serialize to JSON.
* [ ] Test invalid lifecycle transition rejection.
* [ ] Test strategy cannot skip required lifecycle stages.
* [ ] Test paper order blocked without approved paper state.
* [ ] Test live order blocked without RiskGovernor token.
* [ ] Test live order blocked with expired token.
* [ ] Test live order blocked with mismatched token.
* [ ] Test live order blocked when kill switch active.
* [ ] Test live order blocked when broker heartbeat fails.
* [ ] Test live order blocked when audit unavailable.
* [ ] Test Order Router is the only bridge caller.
* [ ] Test direct bridge call rejection.
* [ ] Test Audit Agent flags missing RiskGovernor approval.
* [ ] Test critical audit finding disables live trading.
* [ ] Test Cost Optimizer never routes risk/execution to LLM.
* [ ] Test LLM cannot override deterministic portfolio decisions.
* [ ] Test performance report marks missing data as incomplete.
* [ ] Test incident resume requires approval after critical incident.

---

# 28. Recommended Build Order

## Checklist

* [ ] Build shared portfolio contracts.
* [ ] Build Strategy Lifecycle Agent.
* [ ] Build Portfolio Manager Agent.
* [ ] Build Allocation Optimizer Agent.
* [ ] Build Paper Broker Service.
* [ ] Build Paper Execution Agent.
* [ ] Build Execution Readiness Agent.
* [ ] Build MT5 bridge in dry-run mode.
* [ ] Build cTrader bridge in dry-run mode.
* [ ] Build Order Router Service.
* [ ] Build Kill Switch Service.
* [ ] Build Incident Agent.
* [ ] Build Live Execution Agent with live mode disabled by default.
* [ ] Build Performance Reporter Agent.
* [ ] Build Audit Agent.
* [ ] Build Cost Optimizer Agent.
* [ ] Build Portfolio Orchestrator Agent.
* [ ] Register portfolio agents with Planner.
* [ ] Surface portfolio summaries through CEOChatGateway.
* [ ] Keep live execution blocked until Board approval workflow is implemented.

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
