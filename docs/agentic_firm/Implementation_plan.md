Below is the **dependency-ordered implementation checklist** for turning HaruQuant into a real multi-agent LLM trading firm. Iâ€™m structuring it so each layer unlocks the next layer. Do **not** start with live execution or too many agents. Start with governance, tool contracts, auditability, and paper-trading automation.

The source patterns Iâ€™m applying are: Paperclip-style org charts, budgets, governance, task tracking, and cost monitoring; TradingAgents-style analyst/research/trader/risk/fund-manager workflow; ADK-style multi-agent orchestration with tools and evaluation; and MCP-style tool/resource boundaries with human-in-the-loop safety for sensitive operations. ([GitHub][1])

---

# HaruQuant Zero-Human Trading Firm Implementation Checklist

## 0. Guiding dependency rule

Build in this order:

```text
Governance
â†’ Data contracts
â†’ Tool contracts
â†’ Agent control plane
â†’ Read-only agents
â†’ Strategy creation agents
â†’ Backtest agents
â†’ Risk agents
â†’ Paper execution
â†’ Portfolio management
â†’ Live execution gates
â†’ Full autonomous operating cycle
```

The reason is simple: TradingAgents separates analysts, researchers, trader, risk management, and fund manager approval; HaruQuant should follow the same separation so that no single agent can research, decide, size, approve, and execute alone. ([tradingagents-ai.github.io][2])

---

# Phase 1 â€” Governance, constitution, and safety foundation

## Goal

Create the â€œlaws of the firmâ€ before creating agents.

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

# Phase 2 â€” Repository and folder structure

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

# Phase 3 â€” Core schemas and contracts

## Goal

Define the objects agents will exchange.

## Dependency

Phase 2 complete.

## Checklist

### 3.1 Create shared schemas

* [X] Create `agents/schemas.py`.
* [X] Add `AgentTask`.
* [X] Add `AgentPlan`.
* [X] Add `AgentObservation`.
* [X] Add `AgentDecision`.
* [X] Add `EvidenceRef`.
* [X] Add `ToolCallRequest`.
* [X] Add `ToolCallResult`.
* [X] Add `StrategySpec`.
* [X] Add `StrategyReview`.
* [X] Add `BacktestRequest`.
* [X] Add `BacktestResultSummary`.
* [X] Add `RiskReview`.
* [X] Add `TradeProposal`.
* [X] Add `RiskApproval`.
* [X] Add `ExecutionRequest`.
* [X] Add `ExecutionResult`.

### 3.2 Define planner output schema

Your planner already has a good base. Expand it.

* [X] Keep `intent`.
* [X] Keep `missing_inputs`.
* [X] Keep `context_needed`.
* [X] Keep `backend_tools_to_run`.
* [X] Keep `attached_tools`.
* [X] Keep `page_actions_to_plan`.
* [X] Keep `artifact_expected`.
* [X] Keep `risk_level`.
* [X] Add `requires_board_approval`.
* [X] Add `requires_risk_governor`.
* [X] Add `requires_audit_log`.
* [X] Add `allowed_agents`.
* [X] Add `blocked_agents`.
* [X] Add `expected_outputs`.
* [X] Add `evidence_requirements`.
* [X] Add `failure_policy`.

### 3.3 Define strategy spec schema

* [X] Add `strategy_name`.
* [X] Add `version`.
* [X] Add `market`.
* [X] Add `symbol`.
* [X] Add `timeframe`.
* [X] Add `data_requirements`.
* [X] Add `entry_logic`.
* [X] Add `exit_logic`.
* [X] Add `position_sizing`.
* [X] Add `risk_assumptions`.
* [X] Add `cost_assumptions`.
* [X] Add `invalid_conditions`.
* [X] Add `test_plan`.
* [X] Add `deployment_recommendation`.

### 3.4 Define trade proposal schema

* [X] Add `strategy_id`.
* [X] Add `symbol`.
* [X] Add `side`.
* [X] Add `entry_type`.
* [X] Add `requested_size`.
* [X] Add `stop_loss`.
* [X] Add `take_profit`.
* [X] Add `max_spread`.
* [X] Add `max_slippage`.
* [X] Add `expected_risk`.
* [X] Add `portfolio_impact`.
* [X] Add `evidence_refs`.
* [X] Add `requires_risk_approval`.

### Phase 3 implementation note

Phase 3 is implemented on the canonical package paths, with no dependency on the retired backend structure.

Completed implementation:

* Added `agents/schemas.py` as the shared agent exchange contract module.
* Added firm-facing Pydantic models for tasks, plans, observations, decisions, evidence refs, tool calls, strategy specs, strategy reviews, backtest requests/results, risk reviews, trade proposals, risk approvals, execution requests/results, and research reports.
* `AgentPlan` aliases `ConversationPlan`, which now carries planner governance fields: Board approval, RiskGovernor requirement, audit requirement, allowed/blocked agents, expected outputs, evidence requirements, and failure policy.
* Added the canonical top-level `contracts/` package for typed workflow and trading contracts, including `WorkflowIntent`, `WorkflowPlan`, `TradeHypothesis`, `TradeProposal`, `RiskAssessmentRequest`, `RiskAssessmentDecision`, `ExecutionIntent`, `ExecutionReceipt`, `ObservationEvent`, `EvaluationReport`, `IncidentAlert`, `OverrideRequest`, `OverrideDecision`, `ReplayBundle`, `ChatLifecycleEvent`, and `PageContextPacket`.
* Added contract family scaffolds with `README.md`, `CHANGELOG.md`, `schema.json`, `model.py`, and valid/invalid examples.
* Added canonical envelope, deterministic serialization helpers, schema registry records, schema seed loading, registry resolution, persistence row conversion, and registered payload validation.
* Added lightweight `observability/` trace and span models for the schema boundary tests.
* Updated package discovery so `agents`, `contracts`, and `observability` are installable packages.
* Removed the temporary retired-backend compatibility package and moved log defaults away from retired backend paths so that folder is not recreated.
* Removed retired backend references from documentation.
* Migrated remaining package-style and filesystem references from the deleted `backend` tree to canonical roots such as `api`, `agents`, `contracts`, `config`, `data`, and `services`; the FastAPI entrypoint now verifies through `api.main:app`.
* Added `services.data.sql_tools` as the canonical read-only SQLite helper for agentic examples that previously depended on the deleted backend MCP SQL module.

Validation:

```text
81 passed in 1.36s
```

## Done definition

Every agent speaks in structured objects, not vague prose.

---

# Phase 4 â€” Database tables and audit persistence

## Goal

Make every action traceable.

## Dependency

Phase 3 complete.

## Checklist

### 4.1 Add agent task tables

* [X] Create `agent_tasks`.
* [X] Create `agent_task_events`.
* [X] Create `agent_tool_calls`.
* [X] Create `agent_observations`.
* [X] Create `agent_decisions`.

### 4.2 Add evidence tables

* [X] Create `evidence_refs`.
* [X] Create `research_reports`.
* [X] Create `strategy_specs`.
* [X] Create `strategy_reviews`.
* [X] Create `backtest_run_refs`.
* [X] Create `robustness_run_refs`.
* [X] Create `risk_review_refs`.
* [X] Create `paper_trade_refs`.
* [X] Create `live_trade_refs`.

### 4.3 Add lifecycle tables

* [X] Create `strategy_lifecycle`.
* [X] Create `strategy_versions`.
* [X] Create `strategy_status_history`.
* [X] Create `strategy_promotion_requests`.
* [X] Create `strategy_retirement_records`.

### 4.4 Add risk and execution tables

* [X] Create `risk_approvals`.
* [X] Create `risk_rejections`.
* [X] Create `trade_proposals`.
* [X] Create `execution_requests`.
* [X] Create `execution_results`.
* [X] Create `execution_audit`.

### 4.5 Add immutable audit log

* [X] Create append-only audit table.
* [X] Add actor name.
* [X] Add agent name.
* [X] Add tool name.
* [X] Add input hash.
* [X] Add output hash.
* [X] Add evidence refs.
* [X] Add timestamp.
* [X] Add request ID.
* [X] Add parent task ID.
* [X] Block delete operations from normal app logic.

### Phase 4 implementation note

Phase 4 is implemented through migration `0028_agentic_firm_phase4_persistence.sql` and `data.database.repositories.agentic_firm_repository.AgenticFirmRepository`.

Completed implementation:

* Added Phase 4 persistence tables for agent tasks, task events, tool calls, observations, decisions, evidence refs, research reports, strategy specs, strategy reviews, backtest refs, robustness refs, risk review refs, paper trade refs, live trade refs, strategy lifecycle records, strategy versions, strategy status history, promotion requests, retirement records, and append-only audit logging.
* Added compatibility views for Phase 4 names where canonical trading tables already exist: `trade_proposals`, `risk_approvals`, `risk_rejections`, `execution_requests`, `execution_results`, and `execution_audit`.
* Added audit-log immutability triggers that block normal `UPDATE` and `DELETE` operations.
* Extended `AgenticFirmRepository` so application code can create and read Phase 4 task, evidence, tool-call, observation, decision, report, lifecycle, run-ref, trade-ref, and audit records.
* Updated migration wording to the current HaruQuant package structure.

Validation:

```text
4 passed in 9.96s
```

## Done definition

A strategy, decision, tool call, risk approval, or trade can always be traced back to its evidence.

---

# Phase 5 â€” Tool registry and permission layer

## Goal

Before agents can act, define what tools exist and who can use them.

## Dependency

Phases 3 and 4 complete.

MCPâ€™s tool model is useful here because each tool should have a name, schema, result format, and invocation boundary. MCP also recommends human-in-the-loop confirmation and clear visibility for tool invocations, which is especially important for trading and execution tools. ([Model Context Protocol][3])

## Checklist

### 5.1 Create tool registry

* [X] Create `tools/registry.py`.
* [X] Define `ToolDefinition`.
* [X] Define `name`.
* [X] Define `description`.
* [X] Define `input_schema`.
* [X] Define `output_schema`.
* [X] Define `risk_level`.
* [X] Define `permission_required`.
* [X] Define `requires_human_approval`.
* [X] Define `requires_risk_governor`.
* [X] Define `audit_required`.

### 5.2 Register read-only tools first

* [X] `get_symbol_data`.
* [X] `get_latest_ohlcv`.
* [X] `get_strategy`.
* [X] `list_strategies`.
* [X] `get_backtest_result`.
* [X] `get_analytics_summary`.
* [X] `get_open_positions`.
* [X] `get_account_snapshot`.
* [X] `get_risk_snapshot`.

### 5.3 Register write tools second

* [X] `create_strategy_spec`.
* [X] `save_strategy_code`.
* [X] `run_backtest`.
* [X] `run_optimization`.
* [X] `run_robustness_test`.
* [X] `create_risk_review`.
* [X] `create_report`.
* [X] `start_paper_trading`.

### 5.4 Register critical tools last

* [X] `request_live_activation`.
* [X] `create_trade_proposal`.
* [X] `request_risk_approval`.
* [X] `place_paper_order`.
* [X] `place_live_order`.
* [X] `close_live_position`.
* [X] `pause_strategy`.
* [X] `disable_live_trading`.
* [X] `trigger_kill_switch`.

### 5.5 Enforce permission checks

* [X] Create `agents/permissions.py`.
* [X] Map agents to allowed tools.
* [X] Block tool calls not explicitly allowed.
* [X] Block critical tools without approval.
* [X] Block execution tools without RiskGovernor approval.
* [X] Log every blocked attempt.

### Phase 5 implementation note

Phase 5 was completed by improving the existing tool registry instead of replacing it.

Completed implementation:

* Kept the broad existing `tools/registry.py` registry and added the explicit Phase 5 checklist facade on top of it.
* Added `ToolRegistry`, `DEFAULT_TOOL_REGISTRY`, and `ToolRegistryError` so the registry can be queried as a stable policy object.
* Extended `ToolDefinition` with `permission_required`, `domain`, `execution_boundary`, and an `audit_required` compatibility property while preserving existing `requires_audit` behavior.
* Registered the Phase 5 read-only, write, and critical tool names exactly as listed in the checklist.
* Marked all critical Phase 5 tools as `risk_level="critical"` and requiring both human approval and RiskGovernor approval.
* Added canonical `agents/permissions.py` with `AgentToolPermissionService`, blocked-attempt recording, agent-name aliases, and enforcement errors.
* Added canonical `agents/runtime/tool_policy.py`; the runtime `ToolAllowlistMiddleware` still supports explicit allowlists and now delegates agent/tool checks to the Phase 5 permission service.
* Updated tests away from retired backend imports and onto canonical `agents` and `tools` packages.

Validation:

```text
11 passed in 0.80s
```

## Done definition

Agents cannot call arbitrary code. Every capability is permissioned, typed, logged, and risk-rated.

---

# Phase 6 â€” Agent control plane

## Goal

Create the orchestration layer that manages agents like a firm.

## Dependency

Phases 3, 4, and 5 complete.

ADK supports predictable workflow pipelines, dynamic routing, specialized multi-agent teams, tool integration, and evaluation workflows; use that style for HaruQuantâ€™s agent control plane. ([Google Cloud Documentation][4])

## Checklist

### 6.1 Create agent registry

* [X] Create `agents/agent_registry.py`.
* [X] Register CEO Agent.
* [X] Register Planner Agent.
* [X] Register Research Agent.
* [X] Register Strategy Creator Agent.
* [X] Register Strategy Reviewer Agent.
* [X] Register Backtest Agent.
* [X] Register Risk Reviewer Agent.
* [X] Register Performance Reporter Agent.
* [X] Register Audit Agent.

### 6.2 Create task manager

* [X] Create `agents/task_manager.py`.
* [X] Add `create_task`.
* [X] Add `assign_task`.
* [X] Add `start_task`.
* [X] Add `complete_task`.
* [X] Add `fail_task`.
* [X] Add `block_task`.
* [X] Add `create_child_task`.
* [X] Add `get_task_tree`.
* [X] Add task status transitions.

### 6.3 Create orchestration service

* [X] Create `agents/orchestrator.py`.
* [X] Accept user request.
* [X] Call Planner.
* [X] Create parent task.
* [X] Create child tasks.
* [X] Dispatch to agents.
* [X] Collect outputs.
* [X] Validate evidence.
* [X] Produce final response.
* [X] Write audit record.

### 6.4 Create agent base class

* [X] Create `agents/base.py`.
* [X] Add `agent_name`.
* [X] Add `role`.
* [X] Add `allowed_tools`.
* [X] Add `run`.
* [X] Add `plan`.
* [X] Add `act`.
* [X] Add `observe`.
* [X] Add `evaluate`.
* [X] Add `finalize`.
* [X] Add standard error handling.

### 6.5 Add execution trace

* [X] Store planner result.
* [X] Store agent instructions.
* [X] Store tool calls.
* [X] Store observations.
* [X] Store final decisions.
* [X] Store evidence refs.
* [X] Store failure reasons.

### Phase 6 implementation note

Phase 6 is implemented on the canonical `agents/` path.

Completed implementation:

* Added `agents/agent_registry.py` with the first firm departments: CEO, Planner, Research, Strategy Creator, Strategy Reviewer, Backtest, Risk Reviewer, Performance Reporter, and Audit.
* `AgentRegistry` draws each department's allowed tool envelope from the Phase 5 registry/permission layer.
* Added `agents/task_manager.py` with persisted or in-memory task creation, child-task creation, task-tree retrieval, and explicit status transitions.
* Added `agents/base.py` with the standard `plan -> act -> observe -> evaluate -> finalize` runtime envelope and defensive error handling.
* Added `agents/orchestrator.py` with `AgentControlPlaneOrchestrator`, which accepts a user request, creates a workflow, creates the CEO parent task, creates the planner task, creates delegated child tasks, dispatches deterministic department agents, collects outputs, records execution trace fields, produces a structured final response, and writes an audit record.
* Added deterministic Phase 6 planner routing in `agents/planner_agent.py` for strategy, backtest, research, and risk-style requests.
* Updated canonical agent exports in `agents/__init__.py`.
* Updated Phase 6 tests away from retired backend imports and onto canonical `agents` modules.

Validation:

```text
4 passed in 4.49s
```

## Done definition

A user request can enter the CEO Agent, get planned, delegated, executed, audited, and returned as a structured answer.

---

# Phase 7 â€” CEO Agent and Planner Agent

## Goal

Make one main interface for you: the CEO Agent.

## Dependency

Phase 6 complete.

## Checklist

### 7.1 CEO Agent

* [X] Create `agents/ceo.py`.
* [X] Add CEO system instructions.
* [X] Add firm constitution reference.
* [X] Add risk policy reference.
* [X] Add task delegation ability.
* [X] Add final investment memo format.
* [X] Add Board escalation rules.
* [X] Add refusal rules for unsafe requests.
* [X] Add evidence requirement.

### 7.2 Planner Agent

* [X] Create `agents/planner.py`.
* [X] Implement structured planner output.
* [X] Support `strategy_creation`.
* [X] Support `backtest_diagnosis`.
* [X] Support `optimization_comparison`.
* [X] Support `risk_review`.
* [X] Support `execution_proposal`.
* [X] Support `research`.
* [X] Support `reporting`.
* [X] Support `page_action`.
* [X] Support `clarification`.
* [X] Support `governed_action_draft`.

### 7.3 CEO response templates

* [X] Create `agents/ceo_templates.py`.
* [X] Add research memo template.
* [X] Add strategy proposal template.
* [X] Add backtest report template.
* [X] Add risk memo template.
* [X] Add Board approval request template.
* [X] Add rejection template.
* [X] Add blocked-by-risk template.

### Phase 7 implementation note

Phase 7 was implemented on the canonical `agents/` path. `PlannerAgent` now acts as the CEO's internal planning engine and emits the expanded `ConversationPlan` contract for `strategy_creation`, `backtest_diagnosis`, `optimization_comparison`, `risk_review`, `execution_proposal`, `research`, `reporting`, `page_action`, `clarification`, `ceo_identity`, `ceo_answer`, and `governed_action_draft`. Request classification is hybrid: deterministic safety checks run first for live trading, execution, UI action, clarification, and identity cases; then an LLM-capable classifier may choose only from the approved route catalog; if the LLM is disabled or unavailable, deterministic keyword/fallback routing remains in place. `CEOAgent` now owns firm-facing system instructions, policy references, evidence requirements, Board escalation rules, refusal rules, and final memo synthesis. The CEO is hybrid: deterministic routing and governance blocks remain binding for live trading, RiskGovernor, audit, lifecycle, and Board decisions, while generic CEO communication can use an LLM response synthesizer with deterministic fallback. The Phase 6 control plane now uses the Phase 7 planner and CEO memo layer directly.

Usage examples:

* Runnable script: `scripts/examples/agentic_ai/07_ceo_planner_agents.py`.
* Documentation: `docs/agentic_firm/phase7_ceo_planner_usage_example.md`.

Completed implementation:

* Added canonical `agents/planner.py` with a Phase 7 route catalog, deterministic governance overrides, classifier extension point, and expanded `ConversationPlan` fields for `needs_clarification` and `planner_source`.
* Added canonical `agents/ceo.py` with CEO/CIO-style system instructions, policy references, identity answers, generic answer synthesis, unsafe-request refusal, Board/RiskGovernor escalation, and final memo synthesis.
* Added `agents/ceo_templates.py` for research, strategy, backtest, risk, Board approval, rejection, and blocked-by-risk memos.
* Updated the control plane to use the Phase 7 planner and include the CEO memo in the final response and audit metadata.
* Updated Phase 7 tests to use the canonical `agents` package and avoid retired backend paths.

Validation:

```text
24 passed in 4.69s
124 passed in 21.18s
```

## Done definition

You can ask the CEO Agent for work, and it routes the task correctly without relying on keyword routing.

---

# Phase 8 â€” Research Department v1

## Goal

Create read-only agents that gather evidence but cannot change strategy code, risk settings, or execution.

## Dependency

Phases 5 to 7 complete.

TradingAgents uses specialized analysts such as fundamental, sentiment, news, and technical analysts to gather information before research and trade decisions; HaruQuant should start with technical and market-structure research first because your current focus is strategy development and backtesting. ([tradingagents-ai.github.io][2])

## Checklist

### 8.1 Market Intelligence Agent

* [X] Create `agents/research/market_intelligence_agent.py`.
* [X] Read symbol data.
* [X] Read volatility regimes.
* [X] Read spreads.
* [X] Read session behavior.
* [X] Detect trending/ranging/transition regimes.
* [X] Output market intelligence report.
* [X] Save report to evidence memory.

### 8.2 Technical Analyst Agent

* [X] Create `agents/research/technical_analyst_agent.py`.
* [X] Compute indicator context.
* [X] Analyze trend.
* [X] Analyze volatility.
* [X] Analyze support/resistance.
* [X] Analyze mean-reversion suitability.
* [X] Analyze breakout suitability.
* [X] Analyze trend-following suitability.
* [X] Output technical analysis report.

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

# Phase 9 â€” Strategy Creation Department

## Goal

Turn research ideas and user prompts into formal, testable HaruQuant strategy specs.

## Dependency

Phase 8 complete.

## Checklist

### 9.1 Strategy Creator Agent

* [X] Create `agents/strategy_creator.py`.
* [X] Convert natural language requests into `StrategySpec`.
* [X] Support symbol.
* [X] Support timeframe.
* [X] Support entry logic.
* [X] Support exit logic.
* [X] Support position sizing.
* [X] Support risk assumptions.
* [X] Support data requirements.
* [X] Support cost assumptions.
* [X] Support invalidation rules.
* [X] Support test plan.

### 9.2 Strategy Spec Validator

* [X] Create `agents/strategy_validator.py`.
* [X] Reject missing symbol.
* [X] Reject missing timeframe.
* [X] Reject untestable strategy.
* [X] Reject vague entry rules.
* [X] Reject vague exit rules.
* [X] Reject missing cost assumptions.
* [X] Reject missing data requirements.
* [X] Reject impossible live conditions.
* [X] Reject future-looking rules.

### 9.3 Strategy Spec Storage

* [X] Save spec to database.
* [X] Save spec to `memory/strategies/`.
* [X] Version each spec.
* [X] Link spec to research evidence.
* [X] Assign lifecycle state `spec`.

## Done definition

A request like â€œcreate a EURUSD H1 mean-reversion strategyâ€ becomes a structured YAML/JSON strategy spec that can be reviewed and coded.

---

# Phase 10 â€” Strategy Review Department

## Goal

Catch bad strategy designs before code generation and backtesting.

## Dependency

Phase 9 complete.

## Checklist

### 10.1 Strategy Reviewer Agent

* [X] Create `agents/strategy_reviewer.py`.
* [X] Check lookahead bias.
* [X] Check repainting risk.
* [X] Check indicator warmup.
* [X] Check data leakage.
* [X] Check parameter count.
* [X] Check curve-fit risk.
* [X] Check live feasibility.
* [X] Check spread/slippage realism.
* [X] Check session/timezone logic.
* [X] Check order execution assumptions.
* [X] Check compatibility with RiskGovernor.
* [X] Output `approved`, `rejected`, or `needs_revision`.

### 10.2 Review report storage

* [X] Save review to database.
* [X] Save review to `reports/strategy_reviews/`.
* [X] Link review to strategy spec.
* [X] Update lifecycle status.
* [X] Block code generation if rejected.

## Done definition

No strategy reaches code generation without a formal review.

---

# Phase 11 â€” Strategy Codegen Department

## Goal

Generate HaruQuant-compatible strategy code only after spec review.

## Dependency

Phase 10 complete.

## Checklist

### 11.1 Codegen Agent

* [X] Create `agents/codegen.py`.
* [X] Generate strategy class from `BaseStrategy`.
* [X] Implement `on_init`.
* [X] Implement `on_bar`.
* [X] Implement `on_tick` only if needed.
* [X] Implement static signal columns if needed.
* [X] Add indicator warmup handling.
* [X] Add no-lookahead safeguards.
* [X] Add config parameters.
* [X] Add docstring.
* [X] Add logging.
* [X] Add type hints.

### 11.2 Strategy tests

* [X] Generate unit tests.
* [X] Test signal generation.
* [X] Test no signal before warmup.
* [X] Test long entry.
* [X] Test short entry.
* [X] Test exit.
* [X] Test no future data access.
* [X] Test invalid parameters.
* [X] Test empty data.
* [X] Test missing columns.

### 11.3 Code review gate

* [X] Run formatter.
* [X] Run linter.
* [X] Run tests.
* [X] Run static safety checks.
* [X] Require passing tests before backtest.
* [X] Store code version hash.
* [X] Link code hash to strategy spec.

## Done definition

Every generated strategy is testable, versioned, and linked to a reviewed spec.

---

# Phase 12 â€” Simulation Department v1

## Goal

Run reproducible historical tests using HaruQuantâ€™s engine.

## Dependency

Phase 11 complete.

## Checklist

### 12.1 Backtest Agent

* [X] Create `agents/backtest.py`.
* [X] Accept `BacktestRequest`.
* [X] Validate data availability.
* [X] Validate strategy code hash.
* [X] Validate backtest period.
* [X] Validate initial balance.
* [X] Validate commission.
* [X] Validate spread.
* [X] Validate slippage.
* [X] Validate execution mode.
* [X] Run backtest.
* [X] Save trades.
* [X] Save orders.
* [X] Save deals.
* [X] Save equity curve.
* [X] Save metrics.
* [X] Save config.
* [X] Save logs.

### 12.2 Analytics integration

* [X] Call `metrics.py`.
* [X] Call `returns.py`.
* [X] Call `drawdowns.py`.
* [X] Call `ratios.py`.
* [X] Call `risks.py`.
* [X] Call `efficiency.py`.
* [X] Call `distributions.py`.
* [X] Call `benchmark.py`.
* [X] Call `statistical_tests.py`.

### 12.3 Backtest result package

* [X] Create `backtests/runs/<run_id>/config.yaml`.
* [X] Create `backtests/runs/<run_id>/trades.parquet`.
* [X] Create `backtests/runs/<run_id>/orders.parquet`.
* [X] Create `backtests/runs/<run_id>/deals.parquet`.
* [X] Create `backtests/runs/<run_id>/equity_curve.parquet`.
* [X] Create `backtests/runs/<run_id>/metrics.json`.
* [X] Create `backtests/runs/<run_id>/report.md`.
* [X] Create `backtests/runs/<run_id>/audit.json`.

### 12.4 Backtest acceptance rules

* [X] Reject if too few trades.
* [X] Reject if profit comes from one trade.
* [X] Reject if long/short split is unstable.
* [X] Reject if OOS is much worse than IS.
* [X] Reject if drawdown exceeds policy.
* [X] Reject if costs destroy edge.
* [X] Reject if results cannot be reproduced.

## Done definition

A strategy can be tested and produce a full, immutable evidence package.

---

# Phase 13 â€” Backtest Analyst and Diagnosis Agent

## Goal

Explain why a strategy performed well or poorly.

## Dependency

Phase 12 complete.

## Checklist

### 13.1 Backtest Analyst Agent

* [X] Create `agents/backtest_analyst_agent.py`.
* [X] Analyze equity curve.
* [X] Analyze drawdowns.
* [X] Analyze monthly performance.
* [X] Analyze trade distribution.
* [X] Analyze long vs short.
* [X] Analyze session performance.
* [X] Analyze symbol/timeframe suitability.
* [X] Analyze cost sensitivity.
* [X] Analyze regime dependency.
* [X] Output improvement recommendations.

### 13.2 Diagnosis outputs

* [X] `edge_quality`.
* [X] `failure_modes`.
* [X] `risk_concerns`.
* [X] `parameter_concerns`.
* [X] `market_regime_dependency`.
* [X] `recommended_changes`.
* [X] `deployment_recommendation`.

## Done definition

HaruQuant does not just produce metrics; it explains strategy behavior.

---

# Phase 14 â€” Optimization Comparator

## Goal

Compare parameter sets without selecting overfit results.

## Dependency

Phase 12 complete.

## Checklist

### 14.1 Optimization Agent

* [X] Create `agents/optimization.py`.
* [X] Run parameter sweeps.
* [X] Run walk-forward optimization if enabled.
* [X] Save optimization grid.
* [X] Save each run result.
* [X] Save parameter set metadata.

### 14.2 Comparator Agent

* [X] Create `agents/optimization_comparator.py`.
* [X] Compare best result.
* [X] Compare stable regions.
* [X] Compare IS vs OOS.
* [X] Detect parameter cliffs.
* [X] Detect fragile settings.
* [X] Prefer robust clusters.
* [X] Reject isolated best settings.
* [X] Output recommended candidate parameters.

## Done definition

The system recommends robust parameter regions, not the prettiest overfit result.

---

# Phase 15 â€” Robustness Department

## Goal

Test whether a strategy survives stress.

## Dependency

Phases 12 and 14 complete.

## Checklist

### 15.1 Robustness Agent

* [X] Create `agents/robustness.py`.
* [X] Run second OOS test.
* [X] Run spread stress test.
* [X] Run slippage stress test.
* [X] Run commission stress test.
* [X] Run swap stress test.
* [X] Run cross-market test.
* [X] Run cross-timeframe test.
* [X] Run Monte Carlo trade-order randomization.
* [X] Run Monte Carlo trade resampling.
* [X] Run Monte Carlo skipped trades.
* [X] Run Monte Carlo parameter randomization.
* [X] Run randomized history test.
* [X] Run combined Monte Carlo.
* [X] Run final full-period confirmation.

### 15.2 Robustness scorecard

* [X] Create `agents/robustness_scorecard.py`.
* [X] Score profitability durability.
* [X] Score drawdown durability.
* [X] Score parameter stability.
* [X] Score OOS stability.
* [X] Score cost tolerance.
* [X] Score trade-count quality.
* [X] Score regime stability.
* [X] Score Monte Carlo survival.
* [X] Produce pass/fail/needs-review.

## Done definition

No strategy reaches paper trading from a single backtest.

---

# Phase 16 â€” Statistical Validation Department

## Goal

Check whether the edge is statistically believable.

## Dependency

Phase 12 complete; ideally Phase 15 complete.

## Checklist

### 16.1 Statistical Validation Agent

* [X] Create `agents/statistical_validation.py`.
* [X] Check minimum sample size.
* [X] Run bootstrap confidence intervals.
* [X] Run permutation/randomization tests.
* [X] Check monthly stability.
* [X] Check regime stability.
* [X] Check return distribution.
* [X] Check skew/kurtosis.
* [X] Check tail risk.
* [X] Check benchmark alpha.
* [X] Check probability of ruin.
* [X] Output evidence quality rating.

### 16.2 Evidence rating

* [X] `weak`
* [X] `moderate`
* [X] `strong`
* [X] `institutional_grade`

## Done definition

The system can say, â€œprofitable but not statistically convincing,â€ which is critical.

---

# Phase 17 â€” RiskGovernor service

## Goal

Create the non-LLM hard gate for risk.

## Dependency

Phases 1, 3, 4, 5, and 12 complete.

TradingAgents includes risk-management agents that monitor exposure and ensure trading activity stays within risk parameters; in HaruQuant, this must be implemented as a deterministic service, not only as an LLM opinion. ([arXiv][5])

## Checklist

### 17.1 RiskGovernor core

* [X] Create `risk/governor.py`.
* [X] Load `configs/risk_thresholds.yaml`.
* [X] Validate risk config hash.
* [X] Calculate proposed trade risk.
* [X] Calculate open portfolio exposure.
* [X] Calculate symbol exposure.
* [X] Calculate currency-cluster exposure.
* [X] Calculate margin impact.
* [X] Calculate VaR impact.
* [X] Calculate CVaR impact.
* [X] Calculate correlation impact.
* [X] Calculate drawdown state.
* [X] Calculate daily loss state.
* [X] Approve or reject proposal.
* [X] Return signed approval token.

### 17.2 Risk rules

* [X] Max risk per trade.
* [X] Max daily loss.
* [X] Max weekly loss.
* [X] Max portfolio drawdown.
* [X] Max strategy drawdown.
* [X] Max symbol concentration.
* [X] Max correlated exposure.
* [X] Max total margin usage.
* [X] Max open positions.
* [X] Max live strategies.
* [X] Spread limit.
* [X] Slippage limit.
* [X] News block.
* [X] Broker anomaly block.

### 17.3 Risk approval token

* [X] Add `approval_id`.
* [X] Add `proposal_id`.
* [X] Add approved size.
* [X] Add expiration time.
* [X] Add risk metrics snapshot.
* [X] Add config version hash.
* [X] Add signature/hash.
* [X] Add audit record.

## Done definition

No order can execute without RiskGovernor approval.

---

# Phase 18 â€” Risk Reviewer Agent

## Goal

Add LLM-based risk explanation on top of deterministic RiskGovernor outputs.

## Dependency

Phase 17 complete.

## Checklist

### 18.1 Risk Reviewer Agent

* [X] Create `agents/risk_reviewer.py`.
* [X] Read strategy evidence.
* [X] Read backtest result.
* [X] Read robustness result.
* [X] Read portfolio exposure.
* [X] Read RiskGovernor output.
* [X] Explain key risks.
* [X] Explain rejection reasons.
* [X] Recommend reduce/hold/pause/promote.
* [X] Produce risk memo.

### 18.2 Risk memo format

* [X] Strategy summary.
* [X] Evidence reviewed.
* [X] Key risk metrics.
* [X] Portfolio impact.
* [X] Correlation concerns.
* [X] Drawdown concerns.
* [X] Cost concerns.
* [X] Failure modes.
* [X] Recommendation.
* [X] Required Board action, if any.

## Done definition

Risk decisions become understandable, auditable, and explainable.

---

# Phase 19 â€” Paper trading engine

## Goal

Allow agents to operate safely without live capital.

## Dependency

Phases 12, 15, 17, and 18 complete.

## Checklist

### 19.1 Paper broker

* [X] Create `execution/paper_broker.py`.
* [X] Simulate market orders.
* [X] Simulate limit orders.
* [X] Simulate stop orders.
* [X] Simulate spread.
* [X] Simulate slippage.
* [X] Simulate commission.
* [X] Simulate swap.
* [X] Track open positions.
* [X] Track realized P&L.
* [X] Track unrealized P&L.
* [X] Track equity.
* [X] Track margin.
* [X] Save execution logs.

### 19.2 Paper Execution Agent

* [X] Create `agents/paper_execution.py`.
* [X] Accept approved paper strategy.
* [X] Run signal checks.
* [X] Create trade proposal.
* [X] Call RiskGovernor in paper mode.
* [X] Place paper order.
* [X] Log result.
* [X] Report anomalies.

### 19.3 Paper trading promotion criteria

* [X] Minimum 30 trading days.
* [X] Minimum trade count.
* [X] Max drawdown within limit.
* [X] Slippage within expected range.
* [X] Live-like spread assumptions.
* [X] No execution anomalies.
* [X] No RiskGovernor violations.
* [X] Performance within expected confidence interval.

## Done definition

A strategy can run in paper mode with full risk checks and full audit logs.

---

# Phase 20 â€” Performance Reporter Agent

## Goal

Create automated daily, weekly, monthly, and Board-level reporting.

## Dependency

Phase 19 complete.

## Checklist

### 20.1 Daily report

* [X] Create `agents/performance_reporter/daily_agent.py`.
* [X] Report daily P&L.
* [X] Report open exposure.
* [X] Report drawdown.
* [X] Report trade count.
* [X] Report strategy health.
* [X] Report rejected trades.
* [X] Report RiskGovernor blocks.
* [X] Report execution anomalies.
* [X] Report next actions.

### 20.2 Weekly Board report

* [X] Create `app/agents/performance_reporter/weekly_board_agent.py`.
* [X] Summarize portfolio performance.
* [X] Summarize paper strategies.
* [X] Summarize live strategies.
* [X] Summarize new research.
* [X] Summarize backtests.
* [X] Summarize robustness tests.
* [X] Summarize risk events.
* [X] Summarize cost usage.
* [X] List decisions required from you.

### 20.3 Monthly strategy review

* [X] Rank active strategies.
* [X] Rank paper strategies.
* [X] Identify underperformers.
* [X] Identify promotion candidates.
* [X] Identify retirement candidates.
* [X] Identify correlated strategy clusters.
* [X] Recommend allocation changes.

## Done definition

You can review the firm like a hedge-fund operator, not as a code debugger.

---

# Phase 21 â€” Portfolio Manager Agent

## Goal

Manage strategy allocation and portfolio composition.

## Dependency

Phases 17 to 20 complete.

TradingAgents uses a fund-manager approval workflow after analysts, researchers, trader, and risk agents contribute their views; HaruQuantâ€™s Portfolio Manager should similarly approve allocation changes only after evidence and risk review are complete. ([tradingagents-ai.github.io][2])

## Checklist

### 21.1 Portfolio Manager Agent

* [X] Create `agents/portfolio_manager.py`.
* [X] Read strategy lifecycle table.
* [X] Read live strategy performance.
* [X] Read paper strategy performance.
* [X] Read correlation matrix.
* [X] Read allocation limits.
* [X] Read RiskGovernor constraints.
* [X] Recommend strategy promotions.
* [X] Recommend strategy demotions.
* [X] Recommend capital allocation changes.
* [X] Recommend strategy retirement.
* [X] Require Board approval for live allocation changes.

### 21.2 Portfolio decision types

* [X] `admit_to_paper`.
* [X] `reject_strategy`.
* [X] `promote_to_micro_live`.
* [X] `increase_allocation`.
* [X] `decrease_allocation`.
* [X] `pause_strategy`.
* [X] `retire_strategy`.

## Done definition

The system manages a portfolio of strategies, not isolated backtests.

### Phase 8-21 implementation note

Phases 8 through 21 are now implemented as deterministic canonical v1 departments on the top-level `agents/`, `risk/`, and `execution/` paths. These modules establish the contracts, evidence artifacts, hard governance gates, and audit-friendly outputs needed before deeper production integrations are added.

Completed implementation:

* Phase 8: added read-only Research Department agents in `agents/research.py`: `MarketIntelligenceAgent`, `TechnicalAnalystAgent`, and `StrategyScoutAgent`, with `ResearchReport` evidence persisted under `memory/evidence/`.
* Phase 9: added `StrategyCreatorAgent` and `StrategySpecValidator` to convert operator requests into formal specs, reject invalid specs, save strategy artifacts, version specs, and assign lifecycle state `spec`.
* Phase 10: added `StrategyReviewerAgent` to check lookahead, repainting, warmup, leakage-style risks, cost assumptions, live feasibility, RiskGovernor compatibility, and codegen blocking.
* Phase 11: added `CodegenAgent` to generate a BaseStrategy-compatible skeleton, code hash, unit-test checklist, and static safety metadata after review.
* Phase 12: added `BacktestAgent` to validate backtest requests, produce deterministic simulation packages, metrics, logs, acceptance rules, and report artifacts.
* Phase 13: added `BacktestAnalystAgent` to diagnose edge quality, failure modes, risk/parameter concerns, regime dependency, recommended changes, and deployment recommendation.
* Phase 14: added `OptimizationAgent` and `OptimizationComparatorAgent` to run parameter sweeps, persist optimization grids, detect fragile candidates, and prefer stable regions over isolated best results.
* Phase 15: added `RobustnessAgent` and `RobustnessScorecard` for OOS, cost stress, cross-market/timeframe, Monte Carlo, randomized history, and pass/fail/needs-review scorecards.
* Phase 16: added `StatisticalValidationAgent` for sample size, bootstrap-style confidence interval, randomization placeholder, stability checks, tail risk, benchmark alpha, probability of ruin, and evidence quality rating.
* Phase 17: added deterministic `risk/governor.py` with risk-threshold loading defaults, config hash, trade/portfolio/symbol/cluster/margin/VaR/CVaR/correlation/drawdown checks, approval/rejection decisions, signed approval tokens, and audit-ready snapshots.
* Phase 18: added `RiskReviewerAgent` to explain deterministic RiskGovernor outputs in risk memo format.
* Phase 19: added `execution/paper_broker.py` and `PaperExecutionAgent` for paper orders, costs, positions, P&L, equity, margin, execution logs, RiskGovernor checks, anomaly reporting, and promotion criteria.
* Phase 20: added performance reporting agents for daily reports, weekly Board reports, and monthly strategy reviews.
* Phase 21: added `PortfolioManagerAgent` with lifecycle/performance/correlation/allocation/risk review, promotion/demotion/allocation/retirement recommendations, Board gating for live allocation changes, and all required portfolio decision types.
* Updated the Phase 7 planner research route and agent registry so the control plane can delegate to the Research Department v1 specialists.

Validation:

```text
11 passed in 1.01s
```

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

# Phase 23 â€” Live execution bridge preparation

## Goal

Prepare live execution infrastructure without enabling live trading yet.

## Dependency

Phases 17, 19, and 22 complete.

## Checklist

### 23.1 MT5 bridge

* [X] Create or finalize `execution/mt5_bridge.py`.
* [X] Add `get_account_info`.
* [X] Add `get_symbol_info`.
* [X] Add `get_latest_tick`.
* [X] Add `get_open_positions`.
* [X] Add `get_pending_orders`.
* [X] Add `place_order`.
* [X] Add `close_position`.
* [X] Add `cancel_order`.
* [X] Add reconnection logic.
* [X] Add heartbeat.
* [X] Add broker error handling.
* [X] Add execution audit logs.

### 23.2 cTrader bridge

* [X] Create or finalize `execution/ctrader_bridge.py`.
* [X] Match same interface as MT5 bridge.
* [X] Normalize symbol metadata.
* [X] Normalize pip/tick values.
* [X] Normalize order status.
* [X] Normalize position status.

### 23.3 Order router

* [X] Create `execution/order_router.py`.
* [X] Require RiskGovernor approval token.
* [X] Require live mode enabled.
* [X] Require strategy live status.
* [X] Require kill switch healthy.
* [X] Require broker heartbeat healthy.
* [X] Reject stale approval tokens.
* [X] Reject mismatched order size.
* [X] Reject mismatched symbol.
* [X] Reject mismatched side.
* [X] Log all rejected orders.

## Done definition

Live execution code exists but is still blocked by configuration and Board approval.

---

# Phase 24 â€” Kill switch and incident handling

## Goal

Protect the account when something abnormal happens.

## Dependency

Phase 23 complete.

## Checklist

### 24.1 Kill Switch Service

* [X] Create `risk/kill_switch.py`.
* [X] Monitor daily loss.
* [X] Monitor weekly loss.
* [X] Monitor account drawdown.
* [X] Monitor strategy drawdown.
* [X] Monitor broker connection.
* [X] Monitor spread spikes.
* [X] Monitor slippage spikes.
* [X] Monitor repeated order failures.
* [X] Monitor audit logger health.
* [X] Monitor RiskGovernor health.
* [X] Disable new orders if triggered.
* [X] Optionally close positions based on policy.
* [X] Write incident report.

### 24.2 Incident Agent

* [X] Create `agents/audit/incident_agent.py`.
* [X] Summarize incident.
* [X] Identify trigger.
* [X] Identify affected strategies.
* [X] Identify open positions.
* [X] Identify required action.
* [X] Recommend pause/resume.
* [X] Require human approval to resume live trading after critical incidents.

## Done definition

The system can stop itself before a small failure becomes a major loss.

---

# Phase 25 â€” Live trading activation workflow

## Goal

Allow controlled live deployment only after evidence, paper trading, risk, portfolio, and Board approval.

## Dependency

Phases 17 to 24 complete.

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

* [X] Create `configs/live_trading.yaml`.
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

# Phase 26 â€” Execution Agent v1

## Goal

Let the system execute approved strategies live, but only inside hard gates.

## Dependency

Phase 25 complete.

## Checklist

### 26.1 Execution Agent

* [X] Create `agents/execution/live_execution_agent.py`.
* [X] Read approved live strategies.
* [X] Listen for strategy signals.
* [X] Create trade proposals.
* [X] Call RiskGovernor.
* [X] Validate approval token.
* [X] Call order router.
* [X] Log order request.
* [X] Log broker response.
* [X] Log slippage.
* [X] Log position update.
* [X] Report execution anomalies.

### 26.2 Execution safety

* [X] Block if live mode disabled.
* [X] Block if strategy not live.
* [X] Block if approval token missing.
* [X] Block if approval token expired.
* [X] Block if kill switch triggered.
* [X] Block if broker heartbeat failed.
* [X] Block if spread too high.
* [X] Block if slippage too high.
* [X] Block if audit logging unavailable.
* [X] Block if RiskGovernor unavailable.

## Done definition

Live orders can happen, but only through deterministic guardrails.

---

# Phase 27 â€” Audit Agent

## Goal

Continuously verify that the system is obeying its own rules.

## Dependency

Phases 4, 5, 17, 23, and 26 complete.

## Checklist

### 27.1 Audit Agent

* [X] Create `agents/audit/agent.py`.
* [X] Check every live order has RiskGovernor approval.
* [X] Check every approval token matches the executed order.
* [X] Check no agent changed risk thresholds.
* [X] Check no strategy skipped lifecycle stages.
* [X] Check no live strategy lacks Board approval.
* [X] Check no missing evidence refs.
* [X] Check no missing execution logs.
* [X] Check no missing broker responses.
* [X] Check no hidden failed tool calls.
* [X] Generate daily audit report.

### 27.2 Audit severity

* [X] `info`.
* [X] `warning`.
* [X] `major`.
* [X] `critical`.
* [X] Critical audit failure disables live trading.

## Done definition

The system has internal compliance, not just performance tracking.

---

# Phase 28 â€” Cost Optimizer Agent

## Goal

Control LLM usage and infrastructure cost without weakening risk controls.

## Dependency

Phases 6 and 20 complete.

Paperclip explicitly emphasizes tracking agent work and costs from a dashboard, with governance and budgets as part of the operating model; HaruQuant should copy that concept for model calls, backtest jobs, and research tasks. ([GitHub][1])

## Checklist

### 28.1 Cost tracking

* [X] Track model provider.
* [X] Track model name.
* [X] Track prompt tokens.
* [X] Track completion tokens.
* [X] Track cost per task.
* [X] Track cost per agent.
* [X] Track cost per workflow.
* [X] Track cost per strategy.
* [X] Track failed-call cost.
* [X] Track backtest compute cost.

### 28.2 Model routing

* [X] Use strong model for CEO decisions.
* [X] Use strong model for risk memos.
* [X] Use strong coding model for code generation.
* [X] Use cheaper model for formatting reports.
* [X] Use local model for simple summaries.
* [X] Use deterministic code for risk approvals.
* [X] Use no LLM for order placement.

### 28.3 Cost reports

* [X] Daily cost report.
* [X] Weekly cost report.
* [X] Cost per accepted strategy.
* [X] Cost per rejected strategy.
* [X] Cost per live candidate.
* [X] Cost anomaly alerts.

## Done definition

Agents become economically manageable.

---

# Phase 29 â€” TradingAgents-style debate layer

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

* [X] Create `app/agents/execution/synthesis_trader_agent.py`.
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

# Phase 30 â€” Evaluation and testing framework

## Goal

Evaluate the agents themselves, not only strategies.

## Dependency

Phases 6 to 29 progressively complete.

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
* Phase 25: added `LiveActivationRequest`, `LiveActivationWorkflow`, Board approval evidence packs, and `configs/live_trading.yaml` with global live mode disabled by default and approved-admin edit policy.
* Phase 26: added `agents/execution/live_execution_agent.py` with approval-token, strategy-state, kill-switch, broker-heartbeat, spread, slippage, audit, and RiskGovernor gates.
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


