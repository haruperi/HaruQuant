Below is the **dependency-ordered implementation checklist** for turning HaruQuant into a real multi-agent LLM trading firm. I’m structuring it so each layer unlocks the next layer. Do **not** start with live execution or too many agents. Start with governance, tool contracts, auditability, and paper-trading automation.

The source patterns I’m applying are: Paperclip-style org charts, budgets, governance, task tracking, and cost monitoring; TradingAgents-style analyst/research/trader/risk/fund-manager workflow; ADK-style multi-agent orchestration with tools and evaluation; and MCP-style tool/resource boundaries with human-in-the-loop safety for sensitive operations. ([GitHub][1])

---

# HaruQuant Zero-Human Trading Firm Implementation Checklist

## 0. Guiding dependency rule

Build in this order:

```text
Governance
→ Data contracts
→ Tool contracts
→ Agent control plane
→ Read-only agents
→ Strategy creation agents
→ Backtest agents
→ Risk agents
→ Paper execution
→ Portfolio management
→ Live execution gates
→ Full autonomous operating cycle
```

The reason is simple: TradingAgents separates analysts, researchers, trader, risk management, and fund manager approval; HaruQuant should follow the same separation so that no single agent can research, decide, size, approve, and execute alone. ([tradingagents-ai.github.io][2])

---

# Phase 1 — Governance, constitution, and safety foundation

## Goal

Create the “laws of the firm” before creating agents.

## Dependency

None. This is the root phase.

## Checklist

### 1.1 Create the HaruQuant firm constitution

* [X] Create `docs/agentic_firm/constitution.md`.
* [X] Define the mission of the HaruQuant agentic firm.
* [X] Define allowed markets: Forex, metals, indices, crypto, equities, or only the ones you want now.
* [X] Define forbidden actions.
* [X] Define paper-trading-first policy.
* [X] Define live-trading approval process.
* [X] Define who can change risk thresholds.
* [X] Define what agents are never allowed to do.
* [X] Define what requires human Board approval.
* [X] Define audit-log requirements.
* [X] Define incident escalation process.
* [X] Define strategy retirement rules.

### 1.2 Create risk policy document

* [X] Create `docs/agentic_firm/risk_policy.md`.
* [X] Define max risk per trade.
* [X] Define max daily loss.
* [X] Define max weekly loss.
* [X] Define max monthly drawdown.
* [X] Define max portfolio drawdown.
* [X] Define max symbol exposure.
* [X] Define max correlated exposure.
* [X] Define max USD-cluster exposure.
* [X] Define max number of simultaneous positions.
* [X] Define max strategy allocation.
* [X] Define max live strategies.
* [X] Define max paper strategies.
* [X] Define spread filters.
* [X] Define slippage filters.
* [X] Define news-event blocks.
* [X] Define broker-disconnect behavior.
* [X] Define kill-switch rules.

### 1.3 Create agent permissions policy

* [X] Create `docs/agentic_firm/agent_permissions.md`.
* [X] Define each agent role.
* [X] Define allowed tools per agent.
* [X] Define forbidden tools per agent.
* [X] Define read-only tools.
* [X] Define write tools.
* [X] Define critical tools.
* [X] Define which tools require approval.
* [X] Define which tools require RiskGovernor approval.
* [X] Define which tools require human approval.
* [X] Define emergency-disable rules for agents.

### 1.4 Create strategy lifecycle policy

* [X] Create `docs/agentic_firm/strategy_lifecycle.md`.
* [X] Define lifecycle states:

  * `idea`
  * `spec`
  * `code_review`
  * `backtest`
  * `robustness`
  * `paper_trading`
  * `micro_live`
  * `limited_live`
  * `normal_live`
  * `paused`
  * `retired`
  * `rejected`
* [X] Define promotion requirements for each state.
* [X] Define demotion rules.
* [X] Define retirement rules.
* [X] Define what evidence is required before paper trading.
* [X] Define what evidence is required before live trading.
* [X] Define what evidence is required before increasing allocation.

## Done definition

This phase is complete only when HaruQuant has written policies that agents must obey and cannot modify.

---

# Phase 2 — Repository and folder structure

## Goal

Create the physical structure where agents, tools, memory, reports, risk gates, and audit logs will live.

## Dependency

Phase 1 complete.

## Checklist

### 2.1 Create backend agent folders

* [X] Create `agents/`.
* [X] Create `agents/ceo.py`.
* [X] Create `agents/planner.py`.
* [X] Create `agents/research.py`.
* [X] Create `agents/strategy_creator.py`.
* [X] Create `agents/strategy_reviewer.py`.
* [X] Create `agents/codegen.py`.
* [X] Create `agents/backtest.py`.
* [X] Create `agents/optimization.py`.
* [X] Create `agents/robustness.py`.
* [X] Create `agents/statistical_validation.py`.
* [X] Create `agents/risk_reviewer.py`.
* [X] Create `agents/portfolio_manager.py`.
* [X] Create `agents/execution.py`.
* [X] Create `agents/performance_reporter.py`.
* [X] Create `agents/audit.py`.
* [X] Create `agents/cost_optimizer.py`.

### 2.2 Create tool folders

* [X] Create `tools/`.
* [X] Create `tools/data_tools.py`.
* [X] Create `tools/strategy_tools.py`.
* [X] Create `tools/backtest_tools.py`.
* [X] Create `tools/analytics_tools.py`.
* [X] Create `tools/risk_tools.py`.
* [X] Create `tools/portfolio_tools.py`.
* [X] Create `tools/execution_tools.py`.
* [X] Create `tools/reporting_tools.py`.
* [X] Create `tools/audit_tools.py`.

### 2.3 Create risk and execution folders

* [X] Create `risk/governor.py`.
* [X] Create `risk/approvals.py`.
* [X] Create `risk/kill_switch.py`.
* [X] Create `risk/correlation.py`.
* [X] Create `risk/var_engine.py`.
* [X] Create `execution/paper_broker.py`.
* [X] Create `execution/mt5_bridge.py`.
* [X] Create `execution/ctrader_bridge.py`.
* [X] Create `execution/order_router.py`.

### 2.4 Create memory folders

* [X] Create `memory/institutional/`.
* [X] Create `memory/performance/`.
* [X] Create `memory/evidence/`.
* [X] Create `memory/lessons/`.
* [X] Create `memory/strategies/active/`.
* [X] Create `memory/strategies/paper/`.
* [X] Create `memory/strategies/live/`.
* [X] Create `memory/strategies/rejected/`.
* [X] Create `memory/strategies/retired/`.

### 2.5 Create report folders

* [X] Create `reports/daily/`.
* [X] Create `reports/weekly/`.
* [X] Create `reports/monthly/`.
* [X] Create `reports/board/`.
* [X] Create `reports/risk/`.
* [X] Create `reports/backtests/`.
* [X] Create `reports/robustness/`.
* [X] Create `reports/strategy_reviews/`.

### Phase 2 implementation note

Phase 2 was implemented as an additive facade migration to avoid losing existing functionality. New firm-facing packages wrap current deterministic services and governed MCP boundaries instead of duplicating risk, execution, strategy, audit, and optimization logic. `execution/ctrader_bridge.py` exists as an explicit fail-closed placeholder until a governed cTrader bridge is implemented.

## Done definition

The repo structure exists, and every future phase has a correct place to write files.

---

# Phase 3 — Core schemas and contracts

## Goal

Define the objects agents will exchange.

## Dependency

Phase 2 complete.

## Checklist

### 3.1 Create shared schemas

* [ ] Create `agents/schemas.py`.
* [ ] Add `AgentTask`.
* [ ] Add `AgentPlan`.
* [ ] Add `AgentObservation`.
* [ ] Add `AgentDecision`.
* [ ] Add `EvidenceRef`.
* [ ] Add `ToolCallRequest`.
* [ ] Add `ToolCallResult`.
* [ ] Add `StrategySpec`.
* [ ] Add `StrategyReview`.
* [ ] Add `BacktestRequest`.
* [ ] Add `BacktestResultSummary`.
* [ ] Add `RiskReview`.
* [ ] Add `TradeProposal`.
* [ ] Add `RiskApproval`.
* [ ] Add `ExecutionRequest`.
* [ ] Add `ExecutionResult`.

### 3.2 Define planner output schema

Your planner already has a good base. Expand it.

* [ ] Keep `intent`.
* [ ] Keep `missing_inputs`.
* [ ] Keep `context_needed`.
* [ ] Keep `backend_tools_to_run`.
* [ ] Keep `attached_tools`.
* [ ] Keep `page_actions_to_plan`.
* [ ] Keep `artifact_expected`.
* [ ] Keep `risk_level`.
* [ ] Add `requires_board_approval`.
* [ ] Add `requires_risk_governor`.
* [ ] Add `requires_audit_log`.
* [ ] Add `allowed_agents`.
* [ ] Add `blocked_agents`.
* [ ] Add `expected_outputs`.
* [ ] Add `evidence_requirements`.
* [ ] Add `failure_policy`.

### 3.3 Define strategy spec schema

* [ ] Add `strategy_name`.
* [ ] Add `version`.
* [ ] Add `market`.
* [ ] Add `symbol`.
* [ ] Add `timeframe`.
* [ ] Add `data_requirements`.
* [ ] Add `entry_logic`.
* [ ] Add `exit_logic`.
* [ ] Add `position_sizing`.
* [ ] Add `risk_assumptions`.
* [ ] Add `cost_assumptions`.
* [ ] Add `invalid_conditions`.
* [ ] Add `test_plan`.
* [ ] Add `deployment_recommendation`.

### 3.4 Define trade proposal schema

* [ ] Add `strategy_id`.
* [ ] Add `symbol`.
* [ ] Add `side`.
* [ ] Add `entry_type`.
* [ ] Add `requested_size`.
* [ ] Add `stop_loss`.
* [ ] Add `take_profit`.
* [ ] Add `max_spread`.
* [ ] Add `max_slippage`.
* [ ] Add `expected_risk`.
* [ ] Add `portfolio_impact`.
* [ ] Add `evidence_refs`.
* [ ] Add `requires_risk_approval`.

### Phase 3 implementation note

Phase 3 was implemented by extending existing schemas instead of creating competing contracts. `AgentPlan` aliases the existing `ConversationPlan`, which now includes Board approval, RiskGovernor, audit, allowed/blocked agent, output, evidence, and failure-policy fields. `agents/schemas.py` provides firm-facing agent exchange models and bridge helpers to existing canonical contracts such as `StrategyBlueprint`, `TradeProposal`, `RiskAssessmentDecision`, `ExecutionIntent`, and `ExecutionReceipt`.

## Done definition

Every agent speaks in structured objects, not vague prose.

---

# Phase 4 — Database tables and audit persistence

## Goal

Make every action traceable.

## Dependency

Phase 3 complete.

## Checklist

### 4.1 Add agent task tables

* [] Create `agent_tasks`.
* [] Create `agent_task_events`.
* [] Create `agent_tool_calls`.
* [] Create `agent_observations`.
* [] Create `agent_decisions`.

### 4.2 Add evidence tables

* [] Create `evidence_refs`.
* [ ] Create `research_reports`.
* [ ] Create `strategy_specs`.
* [ ] Create `strategy_reviews`.
* [ ] Create `backtest_run_refs`.
* [ ] Create `robustness_run_refs`.
* [ ] Create `risk_review_refs`.
* [ ] Create `paper_trade_refs`.
* [ ] Create `live_trade_refs`.

### 4.3 Add lifecycle tables

* [ ] Create `strategy_lifecycle`.
* [ ] Create `strategy_versions`.
* [ ] Create `strategy_status_history`.
* [ ] Create `strategy_promotion_requests`.
* [ ] Create `strategy_retirement_records`.

### 4.4 Add risk and execution tables

* [ ] Create `risk_approvals`.
* [ ] Create `risk_rejections`.
* [ ] Create `trade_proposals`.
* [ ] Create `execution_requests`.
* [ ] Create `execution_results`.
* [ ] Create `execution_audit`.

### 4.5 Add immutable audit log

* [ ] Create append-only audit table.
* [ ] Add actor name.
* [ ] Add agent name.
* [ ] Add tool name.
* [ ] Add input hash.
* [ ] Add output hash.
* [ ] Add evidence refs.
* [ ] Add timestamp.
* [ ] Add request ID.
* [ ] Add parent task ID.
* [ ] Block delete operations from normal app logic.

### Phase 4 implementation note

Phase 4 was implemented through migration `0028_agentic_firm_phase4_persistence.sql` and `AgenticFirmRepository`. New tables were added for agent tasks, task events, tool calls, observations, decisions, evidence refs, reports, lifecycle records, and append-only audit logging. Where canonical tables already existed, Phase 4 names are compatibility views over existing sources of truth: `core_trade_proposals`, `risk_risk_decisions`, `core_execution_intents`, `core_execution_receipts`, and `core_execution_send_attempts`.

## Done definition

A strategy, decision, tool call, risk approval, or trade can always be traced back to its evidence.

---

# Phase 5 — Tool registry and permission layer

## Goal

Before agents can act, define what tools exist and who can use them.

## Dependency

Phases 3 and 4 complete.

MCP’s tool model is useful here because each tool should have a name, schema, result format, and invocation boundary. MCP also recommends human-in-the-loop confirmation and clear visibility for tool invocations, which is especially important for trading and execution tools. ([Model Context Protocol][3])

## Checklist

### 5.1 Create tool registry

* [ ] Create `tools/registry.py`.
* [ ] Define `ToolDefinition`.
* [ ] Define `name`.
* [ ] Define `description`.
* [ ] Define `input_schema`.
* [ ] Define `output_schema`.
* [ ] Define `risk_level`.
* [ ] Define `permission_required`.
* [ ] Define `requires_human_approval`.
* [ ] Define `requires_risk_governor`.
* [ ] Define `audit_required`.

### 5.2 Register read-only tools first

* [ ] `get_symbol_data`.
* [ ] `get_latest_ohlcv`.
* [ ] `get_strategy`.
* [ ] `list_strategies`.
* [ ] `get_backtest_result`.
* [ ] `get_analytics_summary`.
* [ ] `get_open_positions`.
* [ ] `get_account_snapshot`.
* [ ] `get_risk_snapshot`.

### 5.3 Register write tools second

* [ ] `create_strategy_spec`.
* [ ] `save_strategy_code`.
* [ ] `run_backtest`.
* [ ] `run_optimization`.
* [ ] `run_robustness_test`.
* [ ] `create_risk_review`.
* [ ] `create_report`.
* [ ] `start_paper_trading`.

### 5.4 Register critical tools last

* [ ] `request_live_activation`.
* [ ] `create_trade_proposal`.
* [ ] `request_risk_approval`.
* [ ] `place_paper_order`.
* [ ] `place_live_order`.
* [ ] `close_live_position`.
* [ ] `pause_strategy`.
* [ ] `disable_live_trading`.
* [ ] `trigger_kill_switch`.

### 5.5 Enforce permission checks

* [ ] Create `agents/permissions.py`.
* [ ] Map agents to allowed tools.
* [ ] Block tool calls not explicitly allowed.
* [ ] Block critical tools without approval.
* [ ] Block execution tools without RiskGovernor approval.
* [ ] Log every blocked attempt.

### Phase 5 implementation note

Phase 5 was implemented through `tools/registry.py` and `agents/permissions.py`. The existing runtime `ToolAllowlistMiddleware` keeps its original allowlist behavior and now also exposes registry-backed agent permission enforcement. The registry is metadata-only: actual execution remains inside existing service, MCP, risk, execution, and audit boundaries.

## Done definition

Agents cannot call arbitrary code. Every capability is permissioned, typed, logged, and risk-rated.

---

# Phase 6 — Agent control plane

## Goal

Create the orchestration layer that manages agents like a firm.

## Dependency

Phases 3, 4, and 5 complete.

ADK supports predictable workflow pipelines, dynamic routing, specialized multi-agent teams, tool integration, and evaluation workflows; use that style for HaruQuant’s agent control plane. ([Google Cloud Documentation][4])

## Checklist

### 6.1 Create agent registry

* [ ] Create `agents/agent_registry.py`.
* [ ] Register CEO Agent.
* [ ] Register Planner Agent.
* [ ] Register Research Agent.
* [ ] Register Strategy Creator Agent.
* [ ] Register Strategy Reviewer Agent.
* [ ] Register Backtest Agent.
* [ ] Register Risk Reviewer Agent.
* [ ] Register Performance Reporter Agent.
* [ ] Register Audit Agent.

### 6.2 Create task manager

* [ ] Create `agents/task_manager.py`.
* [ ] Add `create_task`.
* [ ] Add `assign_task`.
* [ ] Add `start_task`.
* [ ] Add `complete_task`.
* [ ] Add `fail_task`.
* [ ] Add `block_task`.
* [ ] Add `create_child_task`.
* [ ] Add `get_task_tree`.
* [ ] Add task status transitions.

### 6.3 Create orchestration service

* [ ] Create `agents/orchestrator.py`.
* [ ] Accept user request.
* [ ] Call Planner.
* [ ] Create parent task.
* [ ] Create child tasks.
* [ ] Dispatch to agents.
* [ ] Collect outputs.
* [ ] Validate evidence.
* [ ] Produce final response.
* [ ] Write audit record.

### 6.4 Create agent base class

* [ ] Create `agents/base.py`.
* [ ] Add `agent_name`.
* [ ] Add `role`.
* [ ] Add `allowed_tools`.
* [ ] Add `run`.
* [ ] Add `plan`.
* [ ] Add `act`.
* [ ] Add `observe`.
* [ ] Add `evaluate`.
* [ ] Add `finalize`.
* [ ] Add standard error handling.

### 6.5 Add execution trace

* [ ] Store planner result.
* [ ] Store agent instructions.
* [ ] Store tool calls.
* [ ] Store observations.
* [ ] Store final decisions.
* [ ] Store evidence refs.
* [ ] Store failure reasons.

### Phase 6 implementation note

Phase 6 was implemented on the canonical `agents/` path, not under `app/`. `AgentRegistry` registers the first firm departments and draws each agent's tool envelope from the Phase 5 permission layer. `AgentTaskManager` manages persisted or in-memory task trees with explicit status transitions. `AgentControlPlaneOrchestrator` creates a top-down workflow record, parent CEO task, planner task, delegated child tasks, standard agent run results, final response, and audit record. The base agent class provides a common `plan -> act -> observe -> evaluate -> finalize` envelope for Phase 7+ specialized agents.

Usage example: `docs/agentic_firm/phase6_agent_control_plane_usage_example.md`.

## Done definition

A user request can enter the CEO Agent, get planned, delegated, executed, audited, and returned as a structured answer.

---

# Phase 7 — CEO Agent and Planner Agent

## Goal

Make one main interface for you: the CEO Agent.

## Dependency

Phase 6 complete.

## Checklist

### 7.1 CEO Agent

* [ ] Create `agents/ceo/agent.py`.
* [ ] Add CEO system instructions.
* [ ] Add firm constitution reference.
* [ ] Add risk policy reference.
* [ ] Add task delegation ability.
* [ ] Add final investment memo format.
* [ ] Add Board escalation rules.
* [ ] Add refusal rules for unsafe requests.
* [ ] Add evidence requirement.

### 7.2 Planner Agent

* [ ] Create `agents/planner/agent.py`.
* [ ] Implement structured planner output.
* [ ] Support `strategy_creation`.
* [ ] Support `backtest_diagnosis`.
* [ ] Support `optimization_comparison`.
* [ ] Support `risk_review`.
* [ ] Support `execution_proposal`.
* [ ] Support `research`.
* [ ] Support `reporting`.
* [ ] Support `page_action`.
* [ ] Support `clarification`.
* [ ] Support `governed_action_draft`.

### 7.3 CEO response templates

* [ ] Create `agents/ceo/templates.py`.
* [ ] Add research memo template.
* [ ] Add strategy proposal template.
* [ ] Add backtest report template.
* [ ] Add risk memo template.
* [ ] Add Board approval request template.
* [ ] Add rejection template.
* [ ] Add blocked-by-risk template.

### Phase 7 implementation note

Phase 7 was implemented on the canonical `agents/` path. `PlannerAgent` now acts as the CEO's internal planning engine and emits the expanded `ConversationPlan` contract for `strategy_creation`, `backtest_diagnosis`, `optimization_comparison`, `risk_review`, `execution_proposal`, `research`, `reporting`, `page_action`, `clarification`, `ceo_identity`, `ceo_answer`, and `governed_action_draft`. Request classification is hybrid: deterministic safety checks run first for live trading, execution, UI action, clarification, and identity cases; then an LLM-capable classifier may choose only from the approved route catalog; if the LLM is disabled or unavailable, deterministic keyword/fallback routing remains in place. `CEOAgent` now owns firm-facing system instructions, policy references, evidence requirements, Board escalation rules, refusal rules, and final memo synthesis. The CEO is hybrid: deterministic routing and governance blocks remain binding for live trading, RiskGovernor, audit, lifecycle, and Board decisions, while generic CEO communication can use an LLM response synthesizer with deterministic fallback. The Phase 6 control plane now uses the Phase 7 planner and CEO memo layer directly.

Usage examples:

* Runnable script: `scripts/examples/agentic_ai/07_ceo_planner_agents.py`.
* Documentation: `docs/agentic_firm/phase7_ceo_planner_usage_example.md`.

### Phase 7.5 chatbot merge note

The AI chatbot is now bridged into the Agentic Firm architecture by default. Set `HARUQUANT_AGENTIC_FIRM_CHAT=false` or instantiate `AIGatewayService(agentic_firm_chat_enabled=False)` only when the legacy route is needed for comparison. `CEOChatOrchestrator` makes the chatbot speak through `CEOAgent`, the CEO planning engine, and `AgentControlPlaneOrchestrator`; legacy attached chat tools are treated as operator hints rather than authority grants; chat metadata now stores `firm_workflow_id`, parent task ID, child task IDs, audit ID, planner source, and CEO memo. Runnable script: `scripts/examples/agentic_ai/09_ceo_chat_bridge.py`.

## Done definition

You can ask the CEO Agent for work, and it routes the task correctly without relying on keyword routing.

---

# Phase 8 — Research Department v1

## Goal

Create read-only agents that gather evidence but cannot change strategy code, risk settings, or execution.

## Dependency

Phases 5 to 7 complete.

TradingAgents uses specialized analysts such as fundamental, sentiment, news, and technical analysts to gather information before research and trade decisions; HaruQuant should start with technical and market-structure research first because your current focus is strategy development and backtesting. ([tradingagents-ai.github.io][2])

## Checklist

### 8.1 Market Intelligence Agent

* [ ] Create `agents/research/market_intelligence_agent.py`.
* [ ] Read symbol data.
* [ ] Read volatility regimes.
* [ ] Read spreads.
* [ ] Read session behavior.
* [ ] Detect trending/ranging/transition regimes.
* [ ] Output market intelligence report.
* [ ] Save report to evidence memory.

### 8.2 Technical Analyst Agent

* [ ] Create `agents/research/technical_analyst_agent.py`.
* [ ] Compute indicator context.
* [ ] Analyze trend.
* [ ] Analyze volatility.
* [ ] Analyze support/resistance.
* [ ] Analyze mean-reversion suitability.
* [ ] Analyze breakout suitability.
* [ ] Analyze trend-following suitability.
* [ ] Output technical analysis report.

### 8.3 Strategy Scout Agent

* [X] Create `agents/research/strategy_scout_agent.py`.
* [X] Search internal strategy memory.
* [X] Search past backtests.
* [X] Search rejected strategies.
* [X] Search external research only through approved tools.
* [X] Score ideas by novelty.
* [X] Score ideas by feasibility.
* [X] Score ideas by edge plausibility.
* [X] Score ideas by testability.
* [X] Score ideas by risk compatibility.
* [X] Output top strategy ideas.

### 8.4 Research report schema

* [X] Add `research_question`.
* [X] Add `sources_used`.
* [X] Add `market_context`.
* [X] Add `candidate_ideas`.
* [X] Add `risks`.
* [X] Add `recommended_next_steps`.
* [X] Add `confidence`.
* [X] Add `evidence_refs`.

### Phase 8 implementation note

Phase 8 was implemented on the canonical `agents/research/` path with read-only deterministic agents: `MarketIntelligenceAgent`, `TechnicalAnalystAgent`, and `StrategyScoutAgent`. The shared `ResearchReport` schema was added to `agents/schemas.py`, and reports are saved as evidence JSON under `memory/evidence/`. The Phase 7 Planner research route now delegates to these Research Department v1 agents. Runnable script: `scripts/examples/agentic_ai/08_research_department.py`.

## Done definition

The CEO can ask for strategy ideas, and the Research Department returns structured evidence without touching execution.

---

# Phase 9 — Strategy Creation Department

## Goal

Turn research ideas and user prompts into formal, testable HaruQuant strategy specs.

## Dependency

Phase 8 complete.

## Checklist

### 9.1 Strategy Creator Agent

* [ ] Create `agents/strategy_creator/agent.py`.
* [ ] Convert natural language requests into `StrategySpec`.
* [ ] Support symbol.
* [ ] Support timeframe.
* [ ] Support entry logic.
* [ ] Support exit logic.
* [ ] Support position sizing.
* [ ] Support risk assumptions.
* [ ] Support data requirements.
* [ ] Support cost assumptions.
* [ ] Support invalidation rules.
* [ ] Support test plan.

### 9.2 Strategy Spec Validator

* [ ] Create `agents/strategy_creator/validator.py`.
* [ ] Reject missing symbol.
* [ ] Reject missing timeframe.
* [ ] Reject untestable strategy.
* [ ] Reject vague entry rules.
* [ ] Reject vague exit rules.
* [ ] Reject missing cost assumptions.
* [ ] Reject missing data requirements.
* [ ] Reject impossible live conditions.
* [ ] Reject future-looking rules.

### 9.3 Strategy Spec Storage

* [ ] Save spec to database.
* [ ] Save spec to `memory/strategies/`.
* [ ] Version each spec.
* [ ] Link spec to research evidence.
* [ ] Assign lifecycle state `spec`.

## Done definition

A request like “create a EURUSD H1 mean-reversion strategy” becomes a structured YAML/JSON strategy spec that can be reviewed and coded.

---

# Phase 10 — Strategy Review Department

## Goal

Catch bad strategy designs before code generation and backtesting.

## Dependency

Phase 9 complete.

## Checklist

### 10.1 Strategy Reviewer Agent

* [ ] Create `agents/strategy_reviewer/agent.py`.
* [ ] Check lookahead bias.
* [ ] Check repainting risk.
* [ ] Check indicator warmup.
* [ ] Check data leakage.
* [ ] Check parameter count.
* [ ] Check curve-fit risk.
* [ ] Check live feasibility.
* [ ] Check spread/slippage realism.
* [ ] Check session/timezone logic.
* [ ] Check order execution assumptions.
* [ ] Check compatibility with RiskGovernor.
* [ ] Output `approved`, `rejected`, or `needs_revision`.

### 10.2 Review report storage

* [ ] Save review to database.
* [ ] Save review to `reports/strategy_reviews/`.
* [ ] Link review to strategy spec.
* [ ] Update lifecycle status.
* [ ] Block code generation if rejected.

## Done definition

No strategy reaches code generation without a formal review.

---

# Phase 11 — Strategy Codegen Department

## Goal

Generate HaruQuant-compatible strategy code only after spec review.

## Dependency

Phase 10 complete.

## Checklist

### 11.1 Codegen Agent

* [ ] Create `agents/codegen/agent.py`.
* [ ] Generate strategy class from `BaseStrategy`.
* [ ] Implement `on_init`.
* [ ] Implement `on_bar`.
* [ ] Implement `on_tick` only if needed.
* [ ] Implement static signal columns if needed.
* [ ] Add indicator warmup handling.
* [ ] Add no-lookahead safeguards.
* [ ] Add config parameters.
* [ ] Add docstring.
* [ ] Add logging.
* [ ] Add type hints.

### 11.2 Strategy tests

* [ ] Generate unit tests.
* [ ] Test signal generation.
* [ ] Test no signal before warmup.
* [ ] Test long entry.
* [ ] Test short entry.
* [ ] Test exit.
* [ ] Test no future data access.
* [ ] Test invalid parameters.
* [ ] Test empty data.
* [ ] Test missing columns.

### 11.3 Code review gate

* [ ] Run formatter.
* [ ] Run linter.
* [ ] Run tests.
* [ ] Run static safety checks.
* [ ] Require passing tests before backtest.
* [ ] Store code version hash.
* [ ] Link code hash to strategy spec.

## Done definition

Every generated strategy is testable, versioned, and linked to a reviewed spec.

---

# Phase 12 — Backtest Department v1

## Goal

Run reproducible historical tests using HaruQuant’s engine.

## Dependency

Phase 11 complete.

## Checklist

### 12.1 Backtest Agent

* [ ] Create `agents/backtest/agent.py`.
* [ ] Accept `BacktestRequest`.
* [ ] Validate data availability.
* [ ] Validate strategy code hash.
* [ ] Validate backtest period.
* [ ] Validate initial balance.
* [ ] Validate commission.
* [ ] Validate spread.
* [ ] Validate slippage.
* [ ] Validate execution mode.
* [ ] Run backtest.
* [ ] Save trades.
* [ ] Save orders.
* [ ] Save deals.
* [ ] Save equity curve.
* [ ] Save metrics.
* [ ] Save config.
* [ ] Save logs.

### 12.2 Analytics integration

* [ ] Call `metrics.py`.
* [ ] Call `returns.py`.
* [ ] Call `drawdowns.py`.
* [ ] Call `ratios.py`.
* [ ] Call `risks.py`.
* [ ] Call `efficiency.py`.
* [ ] Call `distributions.py`.
* [ ] Call `benchmark.py`.
* [ ] Call `statistical_tests.py`.

### 12.3 Backtest result package

* [ ] Create `backtests/runs/<run_id>/config.yaml`.
* [ ] Create `backtests/runs/<run_id>/trades.parquet`.
* [ ] Create `backtests/runs/<run_id>/orders.parquet`.
* [ ] Create `backtests/runs/<run_id>/deals.parquet`.
* [ ] Create `backtests/runs/<run_id>/equity_curve.parquet`.
* [ ] Create `backtests/runs/<run_id>/metrics.json`.
* [ ] Create `backtests/runs/<run_id>/report.md`.
* [ ] Create `backtests/runs/<run_id>/audit.json`.

### 12.4 Backtest acceptance rules

* [ ] Reject if too few trades.
* [ ] Reject if profit comes from one trade.
* [ ] Reject if long/short split is unstable.
* [ ] Reject if OOS is much worse than IS.
* [ ] Reject if drawdown exceeds policy.
* [ ] Reject if costs destroy edge.
* [ ] Reject if results cannot be reproduced.

## Done definition

A strategy can be tested and produce a full, immutable evidence package.

---

# Phase 13 — Backtest Analyst and Diagnosis Agent

## Goal

Explain why a strategy performed well or poorly.

## Dependency

Phase 12 complete.

## Checklist

### 13.1 Backtest Analyst Agent

* [ ] Create `agents/backtest/backtest_analyst_agent.py`.
* [ ] Analyze equity curve.
* [ ] Analyze drawdowns.
* [ ] Analyze monthly performance.
* [ ] Analyze trade distribution.
* [ ] Analyze long vs short.
* [ ] Analyze session performance.
* [ ] Analyze symbol/timeframe suitability.
* [ ] Analyze cost sensitivity.
* [ ] Analyze regime dependency.
* [ ] Output improvement recommendations.

### 13.2 Diagnosis outputs

* [ ] `edge_quality`.
* [ ] `failure_modes`.
* [ ] `risk_concerns`.
* [ ] `parameter_concerns`.
* [ ] `market_regime_dependency`.
* [ ] `recommended_changes`.
* [ ] `deployment_recommendation`.

## Done definition

HaruQuant does not just produce metrics; it explains strategy behavior.

---

# Phase 14 — Optimization Comparator

## Goal

Compare parameter sets without selecting overfit results.

## Dependency

Phase 12 complete.

## Checklist

### 14.1 Optimization Agent

* [ ] Create `app/agents/optimization/agent.py`.
* [ ] Run parameter sweeps.
* [ ] Run walk-forward optimization if enabled.
* [ ] Save optimization grid.
* [ ] Save each run result.
* [ ] Save parameter set metadata.

### 14.2 Comparator Agent

* [ ] Create `agents/optimization/comparator_agent.py`.
* [ ] Compare best result.
* [ ] Compare stable regions.
* [ ] Compare IS vs OOS.
* [ ] Detect parameter cliffs.
* [ ] Detect fragile settings.
* [ ] Prefer robust clusters.
* [ ] Reject isolated best settings.
* [ ] Output recommended candidate parameters.

## Done definition

The system recommends robust parameter regions, not the prettiest overfit result.

---

# Phase 15 — Robustness Department

## Goal

Test whether a strategy survives stress.

## Dependency

Phases 12 and 14 complete.

## Checklist

### 15.1 Robustness Agent

* [ ] Create `agents/robustness/agent.py`.
* [ ] Run second OOS test.
* [ ] Run spread stress test.
* [ ] Run slippage stress test.
* [ ] Run commission stress test.
* [ ] Run swap stress test.
* [ ] Run cross-market test.
* [ ] Run cross-timeframe test.
* [ ] Run Monte Carlo trade-order randomization.
* [ ] Run Monte Carlo trade resampling.
* [ ] Run Monte Carlo skipped trades.
* [ ] Run Monte Carlo parameter randomization.
* [ ] Run randomized history test.
* [ ] Run combined Monte Carlo.
* [ ] Run final full-period confirmation.

### 15.2 Robustness scorecard

* [ ] Create `app/agents/robustness/scorecard.py`.
* [ ] Score profitability durability.
* [ ] Score drawdown durability.
* [ ] Score parameter stability.
* [ ] Score OOS stability.
* [ ] Score cost tolerance.
* [ ] Score trade-count quality.
* [ ] Score regime stability.
* [ ] Score Monte Carlo survival.
* [ ] Produce pass/fail/needs-review.

## Done definition

No strategy reaches paper trading from a single backtest.

---

# Phase 16 — Statistical Validation Department

## Goal

Check whether the edge is statistically believable.

## Dependency

Phase 12 complete; ideally Phase 15 complete.

## Checklist

### 16.1 Statistical Validation Agent

* [ ] Create `agents/statistical_validation/agent.py`.
* [ ] Check minimum sample size.
* [ ] Run bootstrap confidence intervals.
* [ ] Run permutation/randomization tests.
* [ ] Check monthly stability.
* [ ] Check regime stability.
* [ ] Check return distribution.
* [ ] Check skew/kurtosis.
* [ ] Check tail risk.
* [ ] Check benchmark alpha.
* [ ] Check probability of ruin.
* [ ] Output evidence quality rating.

### 16.2 Evidence rating

* [ ] `weak`
* [ ] `moderate`
* [ ] `strong`
* [ ] `institutional_grade`

## Done definition

The system can say, “profitable but not statistically convincing,” which is critical.

---

# Phase 17 — RiskGovernor service

## Goal

Create the non-LLM hard gate for risk.

## Dependency

Phases 1, 3, 4, 5, and 12 complete.

TradingAgents includes risk-management agents that monitor exposure and ensure trading activity stays within risk parameters; in HaruQuant, this must be implemented as a deterministic service, not only as an LLM opinion. ([arXiv][5])

## Checklist

### 17.1 RiskGovernor core

* [ ] Create `risk/governor.py`.
* [ ] Load `configs/risk_thresholds.yaml`.
* [ ] Validate risk config hash.
* [ ] Calculate proposed trade risk.
* [ ] Calculate open portfolio exposure.
* [ ] Calculate symbol exposure.
* [ ] Calculate currency-cluster exposure.
* [ ] Calculate margin impact.
* [ ] Calculate VaR impact.
* [ ] Calculate CVaR impact.
* [ ] Calculate correlation impact.
* [ ] Calculate drawdown state.
* [ ] Calculate daily loss state.
* [ ] Approve or reject proposal.
* [ ] Return signed approval token.

### 17.2 Risk rules

* [ ] Max risk per trade.
* [ ] Max daily loss.
* [ ] Max weekly loss.
* [ ] Max portfolio drawdown.
* [ ] Max strategy drawdown.
* [ ] Max symbol concentration.
* [ ] Max correlated exposure.
* [ ] Max total margin usage.
* [ ] Max open positions.
* [ ] Max live strategies.
* [ ] Spread limit.
* [ ] Slippage limit.
* [ ] News block.
* [ ] Broker anomaly block.

### 17.3 Risk approval token

* [ ] Add `approval_id`.
* [ ] Add `proposal_id`.
* [ ] Add approved size.
* [ ] Add expiration time.
* [ ] Add risk metrics snapshot.
* [ ] Add config version hash.
* [ ] Add signature/hash.
* [ ] Add audit record.

## Done definition

No order can execute without RiskGovernor approval.

---

# Phase 18 — Risk Reviewer Agent

## Goal

Add LLM-based risk explanation on top of deterministic RiskGovernor outputs.

## Dependency

Phase 17 complete.

## Checklist

### 18.1 Risk Reviewer Agent

* [ ] Create `agents/risk_reviewer/agent.py`.
* [ ] Read strategy evidence.
* [ ] Read backtest result.
* [ ] Read robustness result.
* [ ] Read portfolio exposure.
* [ ] Read RiskGovernor output.
* [ ] Explain key risks.
* [ ] Explain rejection reasons.
* [ ] Recommend reduce/hold/pause/promote.
* [ ] Produce risk memo.

### 18.2 Risk memo format

* [ ] Strategy summary.
* [ ] Evidence reviewed.
* [ ] Key risk metrics.
* [ ] Portfolio impact.
* [ ] Correlation concerns.
* [ ] Drawdown concerns.
* [ ] Cost concerns.
* [ ] Failure modes.
* [ ] Recommendation.
* [ ] Required Board action, if any.

## Done definition

Risk decisions become understandable, auditable, and explainable.

---

# Phase 19 — Paper trading engine

## Goal

Allow agents to operate safely without live capital.

## Dependency

Phases 12, 15, 17, and 18 complete.

## Checklist

### 19.1 Paper broker

* [ ] Create `execution/paper_broker.py`.
* [ ] Simulate market orders.
* [ ] Simulate limit orders.
* [ ] Simulate stop orders.
* [ ] Simulate spread.
* [ ] Simulate slippage.
* [ ] Simulate commission.
* [ ] Simulate swap.
* [ ] Track open positions.
* [ ] Track realized P&L.
* [ ] Track unrealized P&L.
* [ ] Track equity.
* [ ] Track margin.
* [ ] Save execution logs.

### 19.2 Paper Execution Agent

* [ ] Create `agents/execution/paper_execution_agent.py`.
* [ ] Accept approved paper strategy.
* [ ] Run signal checks.
* [ ] Create trade proposal.
* [ ] Call RiskGovernor in paper mode.
* [ ] Place paper order.
* [ ] Log result.
* [ ] Report anomalies.

### 19.3 Paper trading promotion criteria

* [ ] Minimum 30 trading days.
* [ ] Minimum trade count.
* [ ] Max drawdown within limit.
* [ ] Slippage within expected range.
* [ ] Live-like spread assumptions.
* [ ] No execution anomalies.
* [ ] No RiskGovernor violations.
* [ ] Performance within expected confidence interval.

## Done definition

A strategy can run in paper mode with full risk checks and full audit logs.

---

# Phase 20 — Performance Reporter Agent

## Goal

Create automated daily, weekly, monthly, and Board-level reporting.

## Dependency

Phase 19 complete.

## Checklist

### 20.1 Daily report

* [ ] Create `agents/performance_reporter/daily_agent.py`.
* [ ] Report daily P&L.
* [ ] Report open exposure.
* [ ] Report drawdown.
* [ ] Report trade count.
* [ ] Report strategy health.
* [ ] Report rejected trades.
* [ ] Report RiskGovernor blocks.
* [ ] Report execution anomalies.
* [ ] Report next actions.

### 20.2 Weekly Board report

* [ ] Create `app/agents/performance_reporter/weekly_board_agent.py`.
* [ ] Summarize portfolio performance.
* [ ] Summarize paper strategies.
* [ ] Summarize live strategies.
* [ ] Summarize new research.
* [ ] Summarize backtests.
* [ ] Summarize robustness tests.
* [ ] Summarize risk events.
* [ ] Summarize cost usage.
* [ ] List decisions required from you.

### 20.3 Monthly strategy review

* [ ] Rank active strategies.
* [ ] Rank paper strategies.
* [ ] Identify underperformers.
* [ ] Identify promotion candidates.
* [ ] Identify retirement candidates.
* [ ] Identify correlated strategy clusters.
* [ ] Recommend allocation changes.

## Done definition

You can review the firm like a hedge-fund operator, not as a code debugger.

---

# Phase 21 — Portfolio Manager Agent

## Goal

Manage strategy allocation and portfolio composition.

## Dependency

Phases 17 to 20 complete.

TradingAgents uses a fund-manager approval workflow after analysts, researchers, trader, and risk agents contribute their views; HaruQuant’s Portfolio Manager should similarly approve allocation changes only after evidence and risk review are complete. ([tradingagents-ai.github.io][2])

## Checklist

### 21.1 Portfolio Manager Agent

* [ ] Create `agents/portfolio_manager/agent.py`.
* [ ] Read strategy lifecycle table.
* [ ] Read live strategy performance.
* [ ] Read paper strategy performance.
* [ ] Read correlation matrix.
* [ ] Read allocation limits.
* [ ] Read RiskGovernor constraints.
* [ ] Recommend strategy promotions.
* [ ] Recommend strategy demotions.
* [ ] Recommend capital allocation changes.
* [ ] Recommend strategy retirement.
* [ ] Require Board approval for live allocation changes.

### 21.2 Portfolio decision types

* [ ] `admit_to_paper`.
* [ ] `reject_strategy`.
* [ ] `promote_to_micro_live`.
* [ ] `increase_allocation`.
* [ ] `decrease_allocation`.
* [ ] `pause_strategy`.
* [ ] `retire_strategy`.

## Done definition

The system manages a portfolio of strategies, not isolated backtests.

---

# Phase 22 — Dashboard and UI integration

## Goal

Make the agent firm observable from the Next.js frontend.

## Dependency

Phases 6 to 21 partially complete.

## Checklist

### 22.1 AI CEO page

* [ ] Create `/ai-ceo`.
* [ ] Chat with CEO Agent.
* [ ] Show planner output.
* [ ] Show active task tree.
* [ ] Show evidence refs.
* [ ] Show final memo.
* [ ] Show approval requests.

### 22.2 Agent task board

* [ ] Create `/agents`.
* [ ] Show all agents.
* [ ] Show task status.
* [ ] Show task dependencies.
* [ ] Show running jobs.
* [ ] Show failed tasks.
* [ ] Show blocked tasks.
* [ ] Show cost usage.

### 22.3 Strategy lab

* [ ] Create `/strategy-lab`.
* [ ] Show strategy ideas.
* [ ] Show strategy specs.
* [ ] Show strategy code versions.
* [ ] Show strategy reviews.
* [ ] Show lifecycle status.

### 22.4 Backtest center

* [ ] Create `/backtests`.
* [ ] Show backtest runs.
* [ ] Show metrics.
* [ ] Show equity curve.
* [ ] Show drawdown.
* [ ] Show trades.
* [ ] Show long/short split.
* [ ] Show period analysis.

### 22.5 Risk center

* [ ] Create `/risk-center`.
* [ ] Show portfolio exposure.
* [ ] Show VaR/CVaR.
* [ ] Show correlation matrix.
* [ ] Show RiskGovernor blocks.
* [ ] Show risk approvals.
* [ ] Show kill-switch status.

### 22.6 Board room

* [ ] Create `/board-room`.
* [ ] Show weekly reports.
* [ ] Show approval queue.
* [ ] Show live activation requests.
* [ ] Show allocation requests.
* [ ] Show strategy promotion requests.
* [ ] Show incident reports.

## Done definition

You can monitor the agentic firm from the UI without reading logs manually.

---

# Phase 23 — Live execution bridge preparation

## Goal

Prepare live execution infrastructure without enabling live trading yet.

## Dependency

Phases 17, 19, and 22 complete.

## Checklist

### 23.1 MT5 bridge

* [ ] Create or finalize `execution/mt5_bridge.py`.
* [ ] Add `get_account_info`.
* [ ] Add `get_symbol_info`.
* [ ] Add `get_latest_tick`.
* [ ] Add `get_open_positions`.
* [ ] Add `get_pending_orders`.
* [ ] Add `place_order`.
* [ ] Add `close_position`.
* [ ] Add `cancel_order`.
* [ ] Add reconnection logic.
* [ ] Add heartbeat.
* [ ] Add broker error handling.
* [ ] Add execution audit logs.

### 23.2 cTrader bridge

* [ ] Create or finalize `execution/ctrader_bridge.py`.
* [ ] Match same interface as MT5 bridge.
* [ ] Normalize symbol metadata.
* [ ] Normalize pip/tick values.
* [ ] Normalize order status.
* [ ] Normalize position status.

### 23.3 Order router

* [ ] Create `execution/order_router.py`.
* [ ] Require RiskGovernor approval token.
* [ ] Require live mode enabled.
* [ ] Require strategy live status.
* [ ] Require kill switch healthy.
* [ ] Require broker heartbeat healthy.
* [ ] Reject stale approval tokens.
* [ ] Reject mismatched order size.
* [ ] Reject mismatched symbol.
* [ ] Reject mismatched side.
* [ ] Log all rejected orders.

## Done definition

Live execution code exists but is still blocked by configuration and Board approval.

---

# Phase 24 — Kill switch and incident handling

## Goal

Protect the account when something abnormal happens.

## Dependency

Phase 23 complete.

## Checklist

### 24.1 Kill Switch Service

* [ ] Create `risk/kill_switch.py`.
* [ ] Monitor daily loss.
* [ ] Monitor weekly loss.
* [ ] Monitor account drawdown.
* [ ] Monitor strategy drawdown.
* [ ] Monitor broker connection.
* [ ] Monitor spread spikes.
* [ ] Monitor slippage spikes.
* [ ] Monitor repeated order failures.
* [ ] Monitor audit logger health.
* [ ] Monitor RiskGovernor health.
* [ ] Disable new orders if triggered.
* [ ] Optionally close positions based on policy.
* [ ] Write incident report.

### 24.2 Incident Agent

* [ ] Create `agents/audit/incident_agent.py`.
* [ ] Summarize incident.
* [ ] Identify trigger.
* [ ] Identify affected strategies.
* [ ] Identify open positions.
* [ ] Identify required action.
* [ ] Recommend pause/resume.
* [ ] Require human approval to resume live trading after critical incidents.

## Done definition

The system can stop itself before a small failure becomes a major loss.

---

# Phase 25 — Live trading activation workflow

## Goal

Allow controlled live deployment only after evidence, paper trading, risk, portfolio, and Board approval.

## Dependency

Phases 17 to 24 complete.

## Checklist

### 25.1 Live activation request

* [ ] Create `LiveActivationRequest` schema.
* [ ] Include strategy ID.
* [ ] Include strategy version.
* [ ] Include backtest evidence.
* [ ] Include robustness evidence.
* [ ] Include paper-trading evidence.
* [ ] Include risk memo.
* [ ] Include portfolio memo.
* [ ] Include requested allocation.
* [ ] Include max risk per trade.
* [ ] Include kill-switch status.
* [ ] Include broker readiness status.

### 25.2 Board approval UI

* [ ] Show full evidence pack.
* [ ] Show risk limits.
* [ ] Show expected worst-case behavior.
* [ ] Show promotion reason.
* [ ] Show rejection option.
* [ ] Show approve micro-live only.
* [ ] Show approve limited-live only.
* [ ] Show expiration of approval.
* [ ] Store approval in audit log.

### 25.3 Live config

* [ ] Create `configs/live_trading.yaml`.
* [ ] Add global live mode.
* [ ] Add per-strategy live mode.
* [ ] Add per-strategy allocation.
* [ ] Add approved symbols.
* [ ] Add approved broker account.
* [ ] Add approval expiration.
* [ ] Add config hash.
* [ ] Block edits except through approved admin path.

## Done definition

A strategy cannot go live by agent enthusiasm. It only goes live through evidence and human approval.

---

# Phase 26 — Execution Agent v1

## Goal

Let the system execute approved strategies live, but only inside hard gates.

## Dependency

Phase 25 complete.

## Checklist

### 26.1 Execution Agent

* [ ] Create `agents/execution/live_execution_agent.py`.
* [ ] Read approved live strategies.
* [ ] Listen for strategy signals.
* [ ] Create trade proposals.
* [ ] Call RiskGovernor.
* [ ] Validate approval token.
* [ ] Call order router.
* [ ] Log order request.
* [ ] Log broker response.
* [ ] Log slippage.
* [ ] Log position update.
* [ ] Report execution anomalies.

### 26.2 Execution safety

* [ ] Block if live mode disabled.
* [ ] Block if strategy not live.
* [ ] Block if approval token missing.
* [ ] Block if approval token expired.
* [ ] Block if kill switch triggered.
* [ ] Block if broker heartbeat failed.
* [ ] Block if spread too high.
* [ ] Block if slippage too high.
* [ ] Block if audit logging unavailable.
* [ ] Block if RiskGovernor unavailable.

## Done definition

Live orders can happen, but only through deterministic guardrails.

---

# Phase 27 — Audit Agent

## Goal

Continuously verify that the system is obeying its own rules.

## Dependency

Phases 4, 5, 17, 23, and 26 complete.

## Checklist

### 27.1 Audit Agent

* [ ] Create `agents/audit/agent.py`.
* [ ] Check every live order has RiskGovernor approval.
* [ ] Check every approval token matches the executed order.
* [ ] Check no agent changed risk thresholds.
* [ ] Check no strategy skipped lifecycle stages.
* [ ] Check no live strategy lacks Board approval.
* [ ] Check no missing evidence refs.
* [ ] Check no missing execution logs.
* [ ] Check no missing broker responses.
* [ ] Check no hidden failed tool calls.
* [ ] Generate daily audit report.

### 27.2 Audit severity

* [ ] `info`.
* [ ] `warning`.
* [ ] `major`.
* [ ] `critical`.
* [ ] Critical audit failure disables live trading.

## Done definition

The system has internal compliance, not just performance tracking.

---

# Phase 28 — Cost Optimizer Agent

## Goal

Control LLM usage and infrastructure cost without weakening risk controls.

## Dependency

Phases 6 and 20 complete.

Paperclip explicitly emphasizes tracking agent work and costs from a dashboard, with governance and budgets as part of the operating model; HaruQuant should copy that concept for model calls, backtest jobs, and research tasks. ([GitHub][1])

## Checklist

### 28.1 Cost tracking

* [ ] Track model provider.
* [ ] Track model name.
* [ ] Track prompt tokens.
* [ ] Track completion tokens.
* [ ] Track cost per task.
* [ ] Track cost per agent.
* [ ] Track cost per workflow.
* [ ] Track cost per strategy.
* [ ] Track failed-call cost.
* [ ] Track backtest compute cost.

### 28.2 Model routing

* [ ] Use strong model for CEO decisions.
* [ ] Use strong model for risk memos.
* [ ] Use strong coding model for code generation.
* [ ] Use cheaper model for formatting reports.
* [ ] Use local model for simple summaries.
* [ ] Use deterministic code for risk approvals.
* [ ] Use no LLM for order placement.

### 28.3 Cost reports

* [ ] Daily cost report.
* [ ] Weekly cost report.
* [ ] Cost per accepted strategy.
* [ ] Cost per rejected strategy.
* [ ] Cost per live candidate.
* [ ] Cost anomaly alerts.

## Done definition

Agents become economically manageable.

---

# Phase 29 — TradingAgents-style debate layer

## Goal

Add multi-agent investment debate after the basic system works.

## Dependency

Phases 8, 12, 17, and 21 complete.

TradingAgents uses analyst reports, bullish and bearish researchers, trader synthesis, risk management, and fund-manager approval; this should be added after HaruQuant already has reliable tooling and auditability. ([arXiv][5])

## Checklist

### 29.1 Add Bull Researcher

* [ ] Create `agents/research/bull_researcher_agent.py`.
* [ ] Argue why a strategy/trade should proceed.
* [ ] Use only evidence refs.
* [ ] Identify upside.
* [ ] Identify favorable market regime.
* [ ] Identify portfolio benefits.

### 29.2 Add Bear Researcher

* [ ] Create `agents/research/bear_researcher_agent.py`.
* [ ] Argue why a strategy/trade should be rejected.
* [ ] Use only evidence refs.
* [ ] Identify downside.
* [ ] Identify hidden risks.
* [ ] Identify overfitting concerns.
* [ ] Identify correlation concerns.

### 29.3 Add Synthesis Trader Agent

* [ ] Create `app/agents/execution/synthesis_trader_agent.py`.
* [ ] Read analyst reports.
* [ ] Read bull memo.
* [ ] Read bear memo.
* [ ] Read RiskGovernor output.
* [ ] Produce trade/strategy recommendation.
* [ ] Never place order directly.

### 29.4 Add debate transcript

* [ ] Store bull memo.
* [ ] Store bear memo.
* [ ] Store synthesis memo.
* [ ] Store final Portfolio Manager decision.
* [ ] Link all to evidence refs.

## Done definition

HaruQuant has trading-firm-style debate, but still uses deterministic gates.

---

# Phase 30 — Evaluation and testing framework

## Goal

Evaluate the agents themselves, not only strategies.

## Dependency

Phases 6 to 29 progressively complete.

ADK includes evaluation support for testing execution trajectories, which is important because agent systems can fail even when individual tools work. ([Google Cloud Documentation][4])

## Checklist

### 30.1 Agent unit tests

* [ ] Test planner classification.
* [ ] Test permission blocking.
* [ ] Test missing input detection.
* [ ] Test evidence requirement enforcement.
* [ ] Test strategy spec validation.
* [ ] Test risk rejection behavior.
* [ ] Test execution blocking behavior.
* [ ] Test Board approval requirement.
* [ ] Test audit logging.

### 30.2 Workflow tests

* [ ] Test full strategy creation workflow.
* [ ] Test rejected strategy workflow.
* [ ] Test backtest workflow.
* [ ] Test robustness workflow.
* [ ] Test paper-trading admission workflow.
* [ ] Test live activation request workflow.
* [ ] Test RiskGovernor rejection workflow.
* [ ] Test kill-switch workflow.
* [ ] Test audit failure workflow.

### 30.3 Red-team tests

* [ ] Agent tries to place live order directly.
* [ ] Agent tries to change risk thresholds.
* [ ] Agent tries to skip paper trading.
* [ ] Agent tries to use stale approval token.
* [ ] Agent tries to increase lot size.
* [ ] Agent tries to hide failed backtest.
* [ ] Agent tries to overwrite evidence.
* [ ] Agent tries to bypass audit logging.

## Done definition

You can prove the agent system obeys the firm constitution.

---

# Phase 31 — Full operating cycle

## Goal

Run the firm as a repeatable autonomous operating system.

## Dependency

All previous phases complete.

## Checklist

### 31.1 Daily cycle

* [ ] Market Intelligence Agent scans market.
* [ ] Strategy signals are checked.
* [ ] RiskGovernor checks proposals.
* [ ] Paper/live execution runs where allowed.
* [ ] Performance Reporter writes daily report.
* [ ] Audit Agent writes daily audit.
* [ ] CEO summarizes daily state.

### 31.2 Weekly cycle

* [ ] Research Agent proposes new ideas.
* [ ] Strategy Creator creates specs.
* [ ] Backtest Agent runs tests.
* [ ] Robustness Agent validates candidates.
* [ ] Portfolio Manager ranks strategies.
* [ ] CEO creates Board report.
* [ ] Board approves/rejects requested actions.

### 31.3 Monthly cycle

* [ ] Review all live strategies.
* [ ] Review all paper strategies.
* [ ] Promote strong paper strategies.
* [ ] Reduce weak live strategies.
* [ ] Retire failed strategies.
* [ ] Rebalance allocations.
* [ ] Review risk policy.
* [ ] Review cost efficiency.
* [ ] Review audit incidents.

## Done definition

HaruQuant operates like a research-and-trading firm rather than a single chatbot.

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
“Create and validate a EURUSD H1 mean-reversion strategy.”

System does:
CEO → Planner → Strategy Creator → Strategy Reviewer → Codegen → Tests → Backtest → Analytics → Risk Review → Final Memo
```

Do **not** include live trading in v0.1.

## v0.1 checklist

* [ ] CEO Agent works.
* [ ] Planner routes correctly.
* [ ] Strategy Creator creates valid specs.
* [ ] Strategy Reviewer rejects weak specs.
* [ ] Codegen creates BaseStrategy-compatible code.
* [ ] Tests are generated and run.
* [ ] Backtest runs.
* [ ] Metrics are calculated.
* [ ] Risk memo is produced.
* [ ] Audit log records the full workflow.
* [ ] Final CEO memo recommends reject, revise, robustness test, or paper trading.

That is the first true proof that HaruQuant can become a multi-agent trading firm.

[1]: https://github.com/agencyenterprise/paperclip-ai
[2]: https://tradingagents-ai.github.io/
[3]: https://modelcontextprotocol.io/specification/2025-11-25/server/tools
[4]: https://docs.cloud.google.com/gemini-enterprise-agent-platform/build/adk
[5]: https://arxiv.org/pdf/2412.20138
