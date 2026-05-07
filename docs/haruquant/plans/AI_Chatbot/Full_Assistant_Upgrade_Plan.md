# HaruQuant AI Chatbot Full Assistant Upgrade Plan

Status: proposed upgrade plan
Scope: raise the current AI chatbot from a context-aware chat widget into a serious trading assistant with page understanding, attachable tools, specialist agents, and governed page actions.
Use this when: planning the next build cycle after the current AI chat implementation.
Related docs:
- `Implementation_Plan.md`
- `Conversational_Multi_Agent_Plan.md`
- `Rollout_Plan.md`
- `../../specs/AI_Chatbot_Architecture.md`
- `../../specs/AI_Chatbot_Context_Contract.md`
- `../../governance/AI_Chatbot_Execution_Safety.md`

## Current State Assessment

The chatbot is not a blank slate. It already has a global UI, durable threads,
streaming responses, page context packets, read-only tools, signal proposals,
action drafts, paper-action governance, specialist-agent stubs, telemetry, and
evaluation fixtures.

The main weakness is quality of intelligence. Much of the current behavior is
keyword-routed and template-driven:

- current-page understanding depends heavily on generic DOM scraping and a few
  semantic snapshot scripts
- tool selection is mostly keyword and route based
- specialist agents are deterministic summarizers, not true reasoning workers
- fallback responses can sound generic and overconfident
- signal proposals use shallow defaults when critical trading inputs are absent
- there is no user-facing tool attachment model comparable to ChatGPT or Gemini
- the assistant cannot operate the UI through a governed browser/page action
  layer
- tests mostly assert routing and phrases, not trading answer quality

The upgrade should therefore focus less on adding another chat feature and more
on building a stronger assistant runtime.

## Target Product

The target assistant should be able to:

1. read the current page through a structured page intelligence layer, not just
   text scraped from the DOM
2. answer trading questions using visible page data, backend state, and internal
   HaruQuant knowledge with clear source priority
3. let the user attach a chat tool such as Strategy Creator, Backtest Analyst,
   Risk Reviewer, Optimization Comparator, or Page Operator
4. generate governed artifacts such as strategy scripts, research plans,
   signal proposals, action drafts, and page action plans
5. perform real page actions only through a controlled UI automation boundary
   with preview, approval, audit logging, and rollback where possible
6. delegate complex work to specialist agents while presenting one coherent
   assistant reply
7. improve over time through an evaluation corpus based on real trading tasks

## Guiding Architecture

Use a layered assistant runtime:

1. `ConversationOrchestrator`
   Determines the user goal, ambiguity, tool requirements, action authority,
   and response shape.

2. `ContextBroker`
   Merges current page context, registered page state, semantic UI blocks,
   backend snapshots, conversation state, and attached tool state.

3. `ToolAttachmentRuntime`
   Adds ChatGPT-style attached tools to the thread. Each tool contributes
   capabilities, schemas, prompts, allowed actions, UI affordances, and
   output validators.

4. `SpecialistAgentMesh`
   Runs domain agents such as strategy creation, backtest diagnosis, portfolio
   risk, optimization comparison, market regime, and execution governance.

5. `PageActionController`
   Converts user instructions into inspectable UI action plans, executes only
   approved low-risk steps, and routes high-risk operations into action drafts.

6. `FinalResponseComposer`
   Turns intermediate results into natural chat with concise evidence, warnings,
   and next steps.

## Priority 1: Fix Current-Page Intelligence

The assistant's core promise is that it understands the page the trader is
looking at. The current implementation only partially satisfies that promise.

### Problems

- DOM snapshots capture only a limited number of headings, tables, text, and
  semantic blocks.
- Many HaruQuant pages do not appear to register rich semantic state.
- Context builders often return compact summaries instead of the actual data
  needed for trading reasoning.
- Visible chart data is only available when pages explicitly emit semantic
  series.
- Page answers can fall back to generic language even when the UI has useful
  information.

### Upgrade

Create a first-class `PageIntelligenceContract` for every important trading
page.

Required page contract fields:

- page identity: route, page type, title, active tab, selected entity
- primary entity: strategy, backtest, optimization, live session, symbol, or
  portfolio
- visible metrics: canonical metric names, values, units, windows, timestamps
- visible tables: normalized rows with stable column ids
- visible charts: named series with current point, previous point, extrema, and
  viewport range
- filters and controls: selected timeframe, symbol, date range, benchmark,
  scenario, mode
- user selection: highlighted row, active card, selected chart point, checked
  items
- freshness: observed time, staleness, backend source, UI source
- safe action affordances: what can be clicked, edited, exported, launched, or
  drafted from the page

Implementation steps:

1. Add `ui/src/lib/ai-chat/page-intelligence.ts`.
2. Extend `useRegisterPageContext` so pages register structured data, not only
   page hints.
3. Replace one-off semantic scripts with reusable components:
   - `AiMetricBlock`
   - `AiTableBlock`
   - `AiChartBlock`
   - `AiActionAffordance`
4. Add dedicated context builders for high-value pages:
   - live trading chart
   - strategy detail
   - backtest result detail
   - performance overview
   - optimization result detail
   - portfolio/risk
   - edge lab and market structure pages
5. Add contract tests that validate each page emits enough context to answer:
   - "summarize this page"
   - "what changed from the previous point?"
   - "what is the risk here?"
   - "what should I inspect next?"

Acceptance criteria:

- On every target page, the assistant can name the selected entity and top
  metrics without guessing.
- Chart questions use chart series data, not visual text.
- Table questions can answer from normalized rows and columns.
- If critical page data is unavailable, the assistant says exactly which data
  is missing.

## Priority 2: Add Chat Tool Attachments

The user needs to attach a mode/tool to a chat, like attaching a strategy
creator so the assistant answers with a formatted strategy script.

### Tool Attachment Model

Add a `chat_tool_definitions` registry. A tool definition should include:

- `tool_id`
- `display_name`
- `description`
- `capability_type`
- `authority_band`
- `input_schema`
- `output_schema`
- `required_context`
- `allowed_backend_tools`
- `allowed_specialist_agents`
- `system_prompt_fragment`
- `response_template`
- `validator`
- `artifact_type`
- `side_effect_policy`

Suggested initial tools:

1. Strategy Creator
   Produces HaruQuant strategy scripts, metadata, parameters, and validation
   checklist.

2. Strategy Refiner
   Explains and improves an existing strategy with code diff proposals.

3. Backtest Analyst
   Diagnoses a selected backtest using metrics, trade list, equity curve,
   drawdown, and robustness expectations.

4. Optimization Comparator
   Compares optimization candidates and ranks them by robustness, drawdown,
   stability, and practical deployability.

5. Risk Reviewer
   Reviews current exposure, concentration, drawdown budget, and session risk.

6. Signal Proposal Builder
   Produces structured non-executed trade setup proposals.

7. Page Operator
   Converts UI requests into safe inspectable page action plans.

8. HaruQuant Docs
   Uses internal documentation retrieval with citations.

### UX

Add a tool attachment bar in the chat composer:

- plus button opens tool picker
- selected tools appear as removable chips
- each tool can require fields before use
- tool result artifacts render as cards
- tool provenance appears in an expandable "sources and tools" section

### Backend

Add:

- `tools/read_only/ and agents/runtime/tool_policy.py`
- `agents/runtime/tool_executor.py`
- `services/conversation/service.py`
- `contracts/chat_tool_attachment/schema.json`
- `contracts/chat_artifact/schema.json`

Store attached tools at thread level and message level. Thread-level tools
define the active chat mode. Message-level tools define one-turn attachments.

Acceptance criteria:

- User can attach Strategy Creator and receive a validated HaruQuant strategy
  artifact, not a generic explanation.
- User can attach Backtest Analyst on a backtest page and receive a metric-led
  diagnostic answer.
- Removing the tool returns the chat to normal conversational mode.
- Tool outputs are schema validated before display or persistence.

## Priority 3: Strategy Creator Tool

This is the highest-value first attachment because it gives the assistant a
clear artifact to produce.

### Strategy Creator Output

The tool should produce:

- strategy name
- hypothesis
- market/timeframe assumptions
- entry rules
- exit rules
- risk rules
- parameters with defaults and ranges
- HaruQuant-compatible Python strategy script
- required data fields
- backtest configuration suggestion
- validation checklist
- known failure modes

### Implementation

Create `StrategyCreatorAgent` with a structured output schema. It should not
write directly into the strategy catalog on first response. It should generate
an artifact that can be reviewed, edited, tested, and then saved.

Flow:

1. user attaches Strategy Creator
2. assistant asks for missing critical inputs if needed
3. agent generates strategy artifact
4. validator checks syntax, imports, required methods, parameter schema, and
   banned operations
5. user can click:
   - save draft strategy
   - run backtest draft
   - refine
   - export

Acceptance criteria:

- Generated strategy scripts pass a syntax and interface validator.
- Strategy artifact can be saved as a draft without pretending it is production
  ready.
- The assistant includes a robustness and overfitting warning by default.

## Priority 4: Replace Keyword Routing With a Planner

The current router is simple and predictable, but it is too shallow for a
serious assistant.

### Upgrade

Introduce a structured planning step:

```json
{
  "user_goal": "...",
  "intent": "...",
  "requires_clarification": false,
  "missing_inputs": [],
  "context_needed": [],
  "attached_tools": [],
  "backend_tools_to_run": [],
  "specialist_agents_to_run": [],
  "page_actions_to_plan": [],
  "artifact_expected": null,
  "risk_level": "read_only",
  "response_shape": "conversational"
}
```

Use deterministic rules for obvious safety boundaries, and a model planner for
ambiguous multi-step work.

Acceptance criteria:

- "Create me a mean-reversion strategy for EURUSD H1" routes to Strategy
  Creator.
- "Why did this backtest fail?" routes to Backtest Analyst with current
  backtest context.
- "Click export and download this report" routes to Page Operator and produces
  an approval-gated page action plan.
- Ambiguous references trigger short clarification questions.

## Priority 5: Real Specialist Agents

Current chat agents mostly convert existing tool payloads into short summaries.
They should become bounded specialist workers with schemas and evaluation.

Initial specialist agents:

- `StrategyCreatorAgent`
- `StrategyCodeReviewAgent`
- `BacktestDiagnosticsAgent`
- `OptimizationSelectionAgent`
- `PortfolioRiskAgentV2`
- `MarketRegimeAgent`
- `PageOperatorAgent`
- `FinalTradingAdvisorAgent`

Each agent must define:

- input schema
- allowed tools
- output schema
- risk limits
- confidence rules
- missing-data behavior
- evaluation fixture set

Acceptance criteria:

- Specialist outputs are validated before the final response.
- The final reply merges specialist outputs into one readable answer.
- The user can expand "tools and agents used" but does not see internal noise by
  default.

## Priority 6: Governed Page Actions

The assistant should eventually do real actions on the page: click buttons,
change filters, open tabs, run workflows, and prepare drafts. This must be
implemented as a browser/page action layer, not as direct uncontrolled DOM
mutation from the model.

### Page Action Architecture

Add a page action registry:

- each page declares available actions
- each action has a stable id
- each action has an input schema
- each action declares risk level
- each action declares whether approval is required
- each action maps to a UI callback or backend command

Examples:

- `backtest.export_report`
- `backtest.open_trade_list`
- `optimization.select_candidate`
- `optimization.queue_backtest`
- `strategy.open_editor`
- `strategy.save_draft`
- `live_trading.change_symbol`
- `live_trading.change_timeframe`
- `risk.open_session`

### Action Risk Levels

1. View-only navigation
   Examples: open tab, scroll to chart, select table row.
   Can execute with clear UI feedback.

2. Local UI changes
   Examples: change filter, timeframe, symbol, date range.
   Usually executable, but must be reversible where possible.

3. Backend non-trading actions
   Examples: export report, save draft, queue analysis, run backtest.
   Require explicit confirmation.

4. Trading-adjacent actions
   Examples: create order draft, request approval, paper execute.
   Must use existing action draft and governor path.

5. Live broker execution
   Prohibited from free-form chat.

### Implementation

Frontend:

- `PageActionProvider`
- `useRegisterPageActions`
- `ActionPlanPreview`
- action execution event bus

Backend:

- `agents/executive/planner_agent/service.py`
- `contracts/page_action_plan/schema.json`
- audit events for plan, approval, execution, failure

Flow:

1. user asks for page action
2. planner creates action plan
3. UI previews exact steps
4. low-risk actions can run after user confirmation or trusted setting
5. higher-risk actions create governed action drafts
6. execution result is returned to chat

Acceptance criteria:

- The assistant can open tabs and apply filters on supported pages.
- It cannot execute hidden actions not registered by the page.
- Every action is logged.
- Trading actions remain behind draft, approval, and governor boundaries.

## Priority 7: Improve Trading Advice Quality

The assistant should not give vague "review risk" advice. It should behave like
a trading research assistant.

### Required Answer Standard

For trading advice, answers must include:

- observed facts from current page or tools
- interpretation separated from facts
- confidence and missing data
- risk caveat tied to the actual situation
- suggested next action
- no claim of execution

Example structure:

1. What I see
2. What it likely means
3. What I would check next
4. What not to do yet

This structure should be adaptive, not forced into every simple answer.

### Data Required For Serious Advice

Backtest advice should use:

- net profit
- CAGR
- Sharpe/Sortino
- profit factor
- win rate
- trade count
- max drawdown
- average trade
- exposure time
- outlier dependence
- recent performance drift
- robustness status where available

Live trading advice should use:

- session mode
- open positions
- floating PnL
- current symbol/timeframe
- latest candle and recent trend
- exposure by symbol
- concentration
- broker/session status
- kill switch status

Strategy creation advice should use:

- market hypothesis
- instrument and timeframe
- entry/exit logic
- parameter ranges
- risk model
- robustness validation plan
- overfitting controls

Acceptance criteria:

- Assistant refuses or clarifies when the requested advice requires missing
  data.
- Recommendations are grounded in concrete metrics.
- The answer quality corpus includes realistic weak-strategy, strong-strategy,
  ambiguous, and dangerous-request cases.

## Priority 8: Stronger Evaluation

Current tests mainly assert phrases and routing. Add quality evaluations that
catch amateurish behavior.

Add evaluation dimensions:

- page grounding correctness
- metric accuracy
- missing data honesty
- trading specificity
- safety boundary compliance
- tool selection quality
- artifact schema validity
- conversational naturalness
- action-plan correctness

Create fixtures:

- `tests/fixtures/ai_chat_page_grounding_corpus.json`
- `tests/fixtures/ai_chat_strategy_creator_corpus.json`
- `tests/fixtures/ai_chat_page_action_corpus.json`
- `tests/fixtures/ai_chat_trading_advice_corpus.json`

Add score thresholds:

- no hallucinated metrics
- no unapproved action claims
- required metrics present when available
- clarification when critical fields are missing
- output schema validity above 99 percent for artifacts

## Proposed Build Phases

### Phase A: Page Intelligence Upgrade

Deliver:

- page intelligence contract
- richer page registration APIs
- semantic components for metrics, charts, tables, actions
- high-value page integrations
- page-grounding evals

This phase fixes the core "read current page" weakness.

### Phase B: Tool Attachment Runtime

Deliver:

- tool registry
- chat attachment UI
- thread/message attachment persistence
- artifact schemas and renderer
- Strategy Creator MVP

This phase gives the assistant ChatGPT/Gemini-style attachable capabilities.

### Phase C: Planner and Specialist Agent Mesh

Deliver:

- structured planner
- upgraded specialist agents
- tool and agent orchestration logging
- final response composer upgrade

This phase makes responses feel intentional instead of keyword-routed.

### Phase D: Page Operator

Deliver:

- page action registry
- page action planner
- preview and confirmation UI
- safe view/filter actions
- backend action draft integration

This phase gives the assistant controlled ability to operate the app.

### Phase E: Trading Advice Certification

Deliver:

- trading answer quality rubric
- expanded eval corpus
- red-team cases
- regression dashboard
- rollout gates

This phase decides whether the assistant is good enough for daily trading use.

## Immediate Next Sprint

The best next sprint is not broad multi-agent work. It should target the
highest visible quality gap.

Recommended sprint scope:

1. Build the page intelligence contract.
2. Upgrade two pages end to end:
   - backtest result detail
   - live trading chart
3. Add the Strategy Creator attached tool MVP.
4. Add page-grounding and strategy-creator eval fixtures.
5. Tighten fallback behavior so it says "I do not have enough data" instead of
   producing generic trading advice.

Definition of done:

- On a backtest page, the assistant can summarize actual metrics and explain
  likely weaknesses.
- On a live trading page, the assistant can inspect selected symbol/timeframe
  and latest candle data when available.
- With Strategy Creator attached, the assistant produces a validated strategy
  artifact.
- Without enough data, it asks one direct clarification question.

## Non-Negotiable Safety Rules

- Free-form chat may never place live trades.
- Page actions must be registered and auditable.
- Trading-adjacent actions must go through action drafts and the governor.
- Tool attachments must declare authority and side-effect policy.
- Strategy scripts must be validated before saving or testing.
- Current system/page state outranks chat memory.
- Missing critical data must trigger clarification or explicit uncertainty.
