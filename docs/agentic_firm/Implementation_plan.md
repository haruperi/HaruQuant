---
# Phase 22 â€” Dashboard and UI integration

## Goal

Make the agent firm observable from the Next.js frontend.

## Dependency

Phases 6 to 21 partially complete.

## Checklist

### 22.1 AI CEO page

* [X] Create `/ai-ceo`.
* [X] Chat with CEO Agent.
* [X] Show planner output.
* [X] Show active task tree.
* [X] Show evidence refs.
* [X] Show final memo.
* [X] Show approval requests.

### 22.2 Agent task board

* [X] Create `/agents`.
* [X] Show all agents.
* [X] Show task status.
* [X] Show task dependencies.
* [X] Show running jobs.
* [X] Show failed tasks.
* [X] Show blocked tasks.
* [X] Show cost usage.

### 22.3 Strategy lab

* [X] Create `/strategy-lab`.
* [X] Show strategy ideas.
* [X] Show strategy specs.
* [X] Show strategy code versions.
* [X] Show strategy reviews.
* [X] Show lifecycle status.

### 22.4 Backtest center

* [X] Create `/backtests`.
* [X] Show backtest runs.
* [X] Show metrics.
* [X] Show equity curve.
* [X] Show drawdown.
* [X] Show trades.
* [X] Show long/short split.
* [X] Show period analysis.

### 22.5 Risk center

* [X] Create `/risk-center`.
* [X] Show portfolio exposure.
* [X] Show VaR/CVaR.
* [X] Show correlation matrix.
* [X] Show RiskGovernor blocks.
* [X] Show risk approvals.
* [X] Show kill-switch status.

### 22.6 Board room

* [X] Create `/board-room`.
* [X] Show weekly reports.
* [X] Show approval queue.
* [X] Show live activation requests.
* [X] Show allocation requests.
* [X] Show strategy promotion requests.
* [X] Show incident reports.

## Done definition

You can monitor the agentic firm from the UI without reading logs manually.
---
---

---

# Live trading activation workflow

## Goal

Allow controlled live deployment only after evidence, paper trading, risk, portfolio, and Board approval.

## Checklist

### 25.1 Live activation request

* [X] Create `LiveActivationRequest` schema.
* [X] Include strategy ID.
* [X] Include strategy version.
* [X] Include backtest evidence.
* [X] Include robustness evidence.
* [X] Include paper-trading evidence.
* [X] Include risk memo.
* [X] Include portfolio memo.
* [X] Include requested allocation.
* [X] Include max risk per trade.
* [X] Include kill-switch status.
* [X] Include broker readiness status.

### 25.2 Board approval UI

* [X] Show full evidence pack.
* [X] Show risk limits.
* [X] Show expected worst-case behavior.
* [X] Show promotion reason.
* [X] Show rejection option.
* [X] Show approve micro-live only.
* [X] Show approve limited-live only.
* [X] Show expiration of approval.
* [X] Store approval in audit log.

### 25.3 Live config

* [X] Create `config/live_trading.yaml`.
* [X] Add global live mode.
* [X] Add per-strategy live mode.
* [X] Add per-strategy allocation.
* [X] Add approved symbols.
* [X] Add approved broker account.
* [X] Add approval expiration.
* [X] Add config hash.
* [X] Block edits except through approved admin path.

## Done definition

A strategy cannot go live by agent enthusiasm. It only goes live through evidence and human approval.

---

---

---

# TradingAgents-style debate layer

## Goal

Add multi-agent investment debate after the basic system works.

## Dependency

Phases 8, 12, 17, and 21 complete.

TradingAgents uses analyst reports, bullish and bearish researchers, trader synthesis, risk management, and fund-manager approval; this should be added after HaruQuant already has reliable tooling and auditability. ([arXiv][5])

## Checklist

### 29.1 Add Bull Researcher

* [X] Create `agents/research/bull_researcher_agent.py`.
* [X] Argue why a strategy/trade should proceed.
* [X] Use only evidence refs.
* [X] Identify upside.
* [X] Identify favorable market regime.
* [X] Identify portfolio benefits.

### 29.2 Add Bear Researcher

* [X] Create `agents/research/bear_researcher_agent.py`.
* [X] Argue why a strategy/trade should be rejected.
* [X] Use only evidence refs.
* [X] Identify downside.
* [X] Identify hidden risks.
* [X] Identify overfitting concerns.
* [X] Identify correlation concerns.

### 29.3 Add Synthesis Trader Agent

* [X] Create `app/agents/portfolio/synthesis_trader_agent.py`.
* [X] Read analyst reports.
* [X] Read bull memo.
* [X] Read bear memo.
* [X] Read RiskGovernor output.
* [X] Produce trade/strategy recommendation.
* [X] Never place order directly.

### 29.4 Add debate transcript

* [X] Store bull memo.
* [X] Store bear memo.
* [X] Store synthesis memo.
* [X] Store final Portfolio Manager decision.
* [X] Link all to evidence refs.

## Done definition

HaruQuant has trading-firm-style debate, but still uses deterministic gates.

---

# Evaluation and testing framework

## Goal

Evaluate the agents themselves, not only strategies.

## Dependency

ADK includes evaluation support for testing execution trajectories, which is important because agent systems can fail even when individual tools work. ([Google Cloud Documentation][4])

## Checklist

### 30.1 Agent unit tests

* [X] Test planner classification.
* [X] Test permission blocking.
* [X] Test missing input detection.
* [X] Test evidence requirement enforcement.
* [X] Test strategy spec validation.
* [X] Test risk rejection behavior.
* [X] Test execution blocking behavior.
* [X] Test Board approval requirement.
* [X] Test audit logging.

### 30.2 Workflow tests

* [X] Test full strategy creation workflow.
* [X] Test rejected strategy workflow.
* [X] Test backtest workflow.
* [X] Test robustness workflow.
* [X] Test paper-trading admission workflow.
* [X] Test live activation request workflow.
* [X] Test RiskGovernor rejection workflow.
* [X] Test kill-switch workflow.
* [X] Test audit failure workflow.

### 30.3 Red-team tests

* [X] Agent tries to place live order directly.
* [X] Agent tries to change risk thresholds.
* [X] Agent tries to skip paper trading.
* [X] Agent tries to use stale approval token.
* [X] Agent tries to increase lot size.
* [X] Agent tries to hide failed backtest.
* [X] Agent tries to overwrite evidence.
* [X] Agent tries to bypass audit logging.

## Done definition

You can prove the agent system obeys the firm constitution.

---

# Phase 31 â€” Full operating cycle

## Goal

Run the firm as a repeatable autonomous operating system.

## Dependency

All previous phases complete.

## Checklist

### 31.1 Daily cycle

* [X] Market Intelligence Agent scans market.
* [X] Strategy signals are checked.
* [X] RiskGovernor checks proposals.
* [X] Paper/live execution runs where allowed.
* [X] Performance Reporter writes daily report.
* [X] Audit Agent writes daily audit.
* [X] CEO summarizes daily state.

### 31.2 Weekly cycle

* [X] Research Agent proposes new ideas.
* [X] Strategy Creator creates specs.
* [X] Backtest Agent runs tests.
* [X] Robustness Agent validates candidates.
* [X] Portfolio Manager ranks strategies.
* [X] CEO creates Board report.
* [X] Board approves/rejects requested actions.

### 31.3 Monthly cycle

* [X] Review all live strategies.
* [X] Review all paper strategies.
* [X] Promote strong paper strategies.
* [X] Reduce weak live strategies.
* [X] Retire failed strategies.
* [X] Rebalance allocations.
* [X] Review risk policy.
* [X] Review cost efficiency.
* [X] Review audit incidents.

## Done definition

HaruQuant operates like a research-and-trading firm rather than a single chatbot.

### Phase 22-31 implementation note

Phases 22 through 31 are now implemented as deterministic canonical v1 infrastructure. The implementation completes the observable operator surface, fail-closed live execution preparation, kill switch, live activation workflow, execution guardrails, audit compliance, cost governance, debate layer, evaluation framework, and repeatable operating cycle.

Completed implementation:

* Phase 22: added dashboard routes for `/ai-ceo`, `/agents`, `/strategy-lab`, `/backtests`, `/risk-center`, and `/board-room`, backed by a shared operator page component.
* Phase 23: added `execution/mt5_bridge.py`, `execution/ctrader_bridge.py`, and `execution/order_router.py`; mutation paths remain fail-closed unless live gates pass.
* Phase 24: added `risk/kill_switch.py` plus `agents/audit/incident_agent.py` for trigger detection, new-order disablement, optional position close policy, incident reports, and human approval requirements for critical recovery.
* Phase 25: added `LiveActivationRequest`, `LiveActivationWorkflow`, Board approval evidence packs, and `config/live_trading.yaml` with global live mode disabled by default and approved-admin edit policy.
* Phase 26: added `agents/portfolio/live_execution_agent.py` with approval-token, strategy-state, kill-switch, broker-heartbeat, spread, slippage, audit, and RiskGovernor gates.
* Phase 27: added `agents/audit/agent.py` with audit severity levels, live-order approval checks, lifecycle checks, Board approval checks, evidence/log checks, hidden failed-tool-call checks, and critical live-trading disablement.
* Phase 28: completed `CostOptimizerAgent` with model/provider/token/cost tracking, workflow/agent/task/strategy breakdowns, failed-call and backtest compute costs, model routing policy, and daily/weekly/candidate cost reports.
* Phase 29: converted research and execution into canonical packages, added Bull Researcher, Bear Researcher, Synthesis Trader, and debate transcript storage linked to evidence refs.
* Phase 30: added `AgentEvaluationFramework` covering unit, workflow, and red-team checks for planner classification, permissions, missing inputs, evidence, risk rejection, execution blocking, Board approval, audit logging, lifecycle, kill switch, and bypass attempts.
* Phase 31: added `OperatingCycleRunner` for daily, weekly, and monthly operating cadences across research, signals, RiskGovernor, paper/live execution where allowed, reporting, audit, CEO summary, Board reporting, promotions, retirements, allocation, risk policy, cost, and incidents.
* The v0.1 milestone checklist is now backed by the Phase 6-31 control plane, CEO/planner layer, strategy pipeline, backtest package, risk memo, audit trail, and final memo behavior.

Validation:

```text
10 passed in 0.98s
21 passed in 1.58s
```

---

# Critical path summary

Build these first, in this exact order:

| Order | Module                        | Why it comes here                |
| ----: | ----------------------------- | -------------------------------- |
|     1 | Constitution and risk policy  | Agents need laws before autonomy |
|     2 | Schemas and database tables   | Agents need structured memory    |
|     3 | Tool registry and permissions | Agents need safe capabilities    |
|     4 | Orchestrator and Planner      | The firm needs a control plane   |
|     5 | CEO Agent                     | You need one interface           |
|     6 | Research Agent                | Read-only intelligence first     |
|     7 | Strategy Creator              | Convert ideas into specs         |
|     8 | Strategy Reviewer             | Block bad ideas early            |
|     9 | Codegen Agent                 | Generate HaruQuant strategy code |
|    10 | Backtest Agent                | Produce evidence                 |
|    11 | Robustness Agent              | Test durability                  |
|    12 | RiskGovernor                  | Hard safety gate                 |
|    13 | Paper Execution               | Safe trading simulation          |
|    14 | Performance Reporter          | Feedback loop                    |
|    15 | Portfolio Manager             | Manage strategy allocation       |
|    16 | Live Execution Bridge         | Only after paper + risk + audit  |
|    17 | Kill Switch                   | Required before live mode        |
|    18 | Audit Agent                   | Continuous compliance            |
|    19 | Cost Optimizer                | Make it scalable                 |
|    20 | Debate Layer                  | Add sophistication after safety  |

---

# Recommended v0.1 milestone

Your first real production milestone should be:

```text
User asks CEO:
â€œCreate and validate a EURUSD H1 mean-reversion strategy.â€

System does:
CEO â†’ Planner â†’ Strategy Creator â†’ Strategy Reviewer â†’ Codegen â†’ Tests â†’ Backtest â†’ Analytics â†’ Risk Review â†’ Final Memo
```

Do **not** include live trading in v0.1.

## v0.1 checklist

* [X] CEO Agent works.
* [X] Planner routes correctly.
* [X] Strategy Creator creates valid specs.
* [X] Strategy Reviewer rejects weak specs.
* [X] Codegen creates BaseStrategy-compatible code.
* [X] Tests are generated and run.
* [X] Backtest runs.
* [X] Metrics are calculated.
* [X] Risk memo is produced.
* [X] Audit log records the full workflow.
* [X] Final CEO memo recommends reject, revise, robustness test, or paper trading.

That is the first true proof that HaruQuant can become a multi-agent trading firm.

[1]: https://github.com/agencyenterprise/paperclip-ai
[2]: https://tradingagents-ai.github.io/
[3]: https://modelcontextprotocol.io/specification/2025-11-25/server/tools
[4]: https://docs.cloud.google.com/gemini-enterprise-agent-platform/build/adk
[5]: https://arxiv.org/pdf/2412.20138
