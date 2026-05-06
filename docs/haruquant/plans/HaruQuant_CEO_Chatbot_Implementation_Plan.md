# HaruQuant CEO Chatbot Implementation Plan

Status: canonical feature implementation plan  
Scope: phased delivery plan for converting the HaruQuant global AI chatbot into the front door of the HaruQuant Agentic Trading Firm  
Use this when: implementing the global chat UI, CEO Agent routing, conversation memory, page context, tool wrappers, agent orchestration, supervised actions, paper automation, prop-firm controls, and production rollout  
Companion docs:

- `docs/agentic_firm/constitution.md`
- `docs/agentic_firm/risk_policy.md`
- `docs/agentic_firm/agent_permissions.md`
- `docs/agentic_firm/strategy_lifecycle.md`
- `docs/agentic_firm/acceptance_criteria.md`
- `docs/agentic_firm/README.md`

Target structure:

```text
haruquant/
  services/
  tools/
  agents/
    prompts/
    orchestration/
  api/
  ui/
  db/
  configs/
  reports/
  tests/
```

Owner: Product Owner and AI Platform Lead  
Review cadence: weekly during active implementation  
Primary interface: Global chat widget talking to the `CEOAgent`

Implementation update:

- Implemented the canonical CEO chat transport without reintroducing `backend_retiring`.
- Reused the existing global `ui/src/components/ai-chat/` widget and `ui/src/stores/chatWidgetStore.tsx` instead of creating a parallel chat UI.
- Added canonical backend services in `services/conversation/`, `services/context/`, `services/chat/`, and `services/schemas/chat.py`.
- Integrated the CEO chat endpoints into the existing FastAPI package at `api/routes/ai_chat.py` for the `/api/ai-chat/*` surface already expected by the UI.
- Routed every chat turn through `PlannerAgent` and `CEOAgent` with deterministic responses for now; real LLM provider wiring remains intentionally deferred.
- Exposed only read-only CEO tools to chat from the canonical `tools.registry`.
- Preserved the safety rule that free-form chat cannot execute live trades or bypass RiskGovernor, audit, or Human Board approval.
- Added CEO prompt stubs in `agents/prompts/ceo.md` and `agents/prompts/planner.md`.
- Added focused regression coverage in `tests/unit/backend/services/test_ceo_chatbot_canonical.py`.
- Added CEO-specific status UI via `CEOStatusBadge.tsx` and relabeled the global widget as `CEO Chat`.

---

## 1. Purpose

This document updates the old HaruQuant AI Chatbot Implementation Plan into the new Agentic Trading Firm architecture.

The original chatbot plan introduced a global, context-aware AI assistant for HaruQuant. The updated plan keeps the same useful foundations — global widget, persistent conversations, page context, streaming, tool grounding, UX maturity, retrieval, observability, and rollout — but changes the core role of the chatbot:

> The chat is no longer just a generic trading copilot. The chat is the user-facing interface to the HaruQuant CEO Agent.

The CEO Agent is the main conversational entry point into the HaruQuant Agentic Trading Firm. It receives user requests, interprets current page context, plans work, delegates to specialist agents, calls safe tools through permissioned wrappers, reads HaruQuant services, and returns final memos, recommendations, reports, drafts, or approval requests.

The chatbot must therefore support two realities at once:

1. A smooth global chat experience across the HaruQuant UI.
2. A controlled agentic-firm workflow where all meaningful work is routed through the CEO Agent, Planner Agent, tools, services, RiskGovernor, audit system, and lifecycle policies.

---

## 2. Strategic Goals

1. Provide a persistent AI chat interface available on every authenticated HaruQuant page.
2. Make the chat interface the front door to the `CEOAgent`, not a standalone chatbot.
3. Preserve conversation continuity across navigation while injecting current page context.
4. Ground every response in HaruQuant services, current page state, internal documents, reports, simulations, strategy records, and risk state.
5. Route all domain work through the Agentic Trading Firm architecture:
   - CEO Agent
   - Planner Agent
   - Research Agent
   - Strategy Creator Agent
   - Strategy Reviewer Agent
   - Codegen Agent
   - Simulation Agent
   - Simulation Analyst Agent
   - Risk Reviewer Agent
   - Reporter Agent
   - Audit Agent
   - Later: Robustness, Portfolio Manager, Execution Agent
6. Preserve strict boundaries between conversation memory, page context, tools, services, agents, RiskGovernor, human approvals, and execution.
7. Support early value through read-only intelligence, strategy explanation, simulation interpretation, risk explanation, and report generation before any side-effectful actions.
8. Progress safely from CEO chat to tool-assisted analysis, then supervised drafts, then paper-trading automation, and only later tightly gated live execution.
9. Preserve prop-firm compliance:
   - 5% max daily loss,
   - 10% static total loss,
   - 10% profit target cycle/month,
   - high-impact news restriction window,
   - weekend/overnight restrictions,
   - forbidden practices,
   - EA/automation compliance,
   - allocation compliance,
   - Best Day Rule / consistency score.
10. Make every tool call, agent decision, draft action, approval, rejection, simulation, and execution attempt auditable.

---

## 3. Key Architectural Change

### Old model

```text
Global Chatbot
  -> Context Service
  -> AI Gateway
  -> Tools
  -> Optional workflow/action layer
```

### New model

```text
Global Chat UI
  -> Chat API
  -> Conversation Service
  -> Page Context Service
  -> CEO Agent
      -> Planner Agent
      -> Specialist Agent(s)
      -> Tool wrapper(s)
      -> HaruQuant services/
      -> Audit
      -> Final CEO response
```

The chat system is not the intelligence layer by itself. It is a delivery channel for the CEO Agent.

The CEO Agent is not allowed to bypass tools, services, governance, RiskGovernor, audit, lifecycle, or human approval. It can coordinate, explain, delegate, recommend, draft, and request approvals.

---

## 4. Planning Assumptions

- HaruQuant uses the simplified architecture with top-level `services/`, `tools/`, `agents/`, `api/`, and `ui/`.
- MCP is intentionally skipped for now.
- HaruQuant exposes a clean public Python API through `import haruquant as hqt`.
- Internal agents call permissioned tool wrappers.
- Tool wrappers call HaruQuant services.
- Services contain business logic.
- The simulation/backtest engine lives inside `services/simulation/`.
- Prompts live inside `agents/prompts/`.
- The global chat widget is always mounted in the UI shell.
- Page context is additive and ephemeral.
- Conversation memory is durable.
- Current system state is more authoritative than prior chat memory.
- Direct LLM-to-broker execution is prohibited.
- Live execution cannot be enabled without approved strategy lifecycle status, RiskGovernor approval, prop-firm compliance checks, kill-switch health, audit logging, and human Board approval where required.
- All side effects must be idempotent or protected against duplicate execution.
- Production readiness requires observability, RBAC, retention, rollback, prompt-injection controls, cost control, and policy enforcement.

---

## 5. Updated Ownership Model

| Role | Responsibility |
|---|---|
| Product Owner | Scope, prioritization, rollout, Board approval workflow |
| AI Platform Lead | CEO Agent, Planner, orchestration, prompts, model routing, evaluation |
| Backend Lead | Services, API endpoints, conversation backend, context service, persistence |
| Frontend Lead | Global chat widget, page context provider, streaming UI, approval UI |
| Quant / Risk Lead | RiskGovernor, prop-firm rules, strategy lifecycle, simulation validity, risk memos |
| Agent Tools Lead | Tool registry, permissions, schemas, audit wrappers, tool safety |
| DevOps / SRE | Deployment, monitoring, scaling, secrets, worker infrastructure |
| QA Lead | Unit, integration, acceptance, regression, red-team test coverage |
| Security / Compliance Owner | RBAC, audit, prompt injection, data leakage, permission and approval review |

Note: the old `MCP / Tooling Lead` role is replaced with `Agent Tools Lead` because this phase intentionally skips MCP.

---

## 6. Workstreams

1. Architecture and governance alignment
2. Global chat UI and conversation experience
3. Conversation memory and durable thread backend
4. Page context injection
5. CEO Agent orchestration and streaming
6. Tool registry and permissioned service wrappers
7. Read-only HaruQuant intelligence
8. Strategy and simulation intelligence
9. Risk and prop-firm compliance intelligence
10. Internal retrieval and knowledge grounding
11. Supervised action drafts and approval queue
12. Paper automation and execution governance
13. Observability, cost, latency, and operations
14. Certification, rollout, and ongoing operations

---

## 7. Target Code Structure

```text
haruquant/
  __init__.py

  services/
    utils/
      config.py
      constants.py
      enums.py
      errors.py
      logging.py
      time.py
      ids.py
      security.py
      validation.py

    schemas/
      common.py
      data.py
      indicator.py
      strategy.py
      simulation.py
      analytics.py
      risk.py
      execution.py
      agent.py
      chat.py
      report.py

    data/
      service.py
      mt5.py
      csv.py
      parquet.py
      storage.py
      quality.py
      calendar.py

    indicator/
      service.py
      trend.py
      momentum.py
      volatility.py
      volume.py
      patterns.py

    strategy/
      service.py
      base.py
      spec.py
      signals.py
      validators.py
      library.py
      codegen.py

    simulation/
      service.py
      engine.py
      broker.py
      portfolio.py
      result.py
      optimization.py
      robustness.py
      statistical_validation.py

    analytics/
      service.py
      metrics.py
      returns.py
      drawdowns.py
      ratios.py
      risks.py
      efficiency.py
      distributions.py
      benchmark.py
      statistical_tests.py

    risk/
      service.py
      governor.py
      prop_firm.py
      portfolio.py
      exposure.py
      correlation.py
      consistency.py
      kill_switch.py

    execution/
      service.py
      paper.py
      live.py
      order_router.py
      mt5_bridge.py
      ctrader_bridge.py
      models.py

    conversation/
      service.py
      memory.py
      summaries.py
      title.py

    context/
      service.py
      builders.py
      freshness.py

    reporting/
      service.py
      templates.py
      exporters.py

    retrieval/
      service.py
      indexer.py
      search.py

    memory/
      service.py
      institutional.py
      evidence.py
      lessons.py

    audit/
      service.py
      chain.py
      findings.py

    cost/
      service.py
      usage.py
      routing.py

  tools/
    registry.py
    permissions.py
    base.py
    policy.py
    task.py
    data.py
    strategy.py
    code.py
    simulation.py
    analytics.py
    risk.py
    execution.py
    reporting.py
    retrieval.py
    audit.py

  agents/
    base.py
    ceo.py
    planner.py
    research.py
    strategy_creator.py
    strategy_reviewer.py
    codegen.py
    simulation.py
    simulation_analyst.py
    robustness.py
    statistical_validator.py
    risk_reviewer.py
    portfolio_manager.py
    execution.py
    reporter.py
    audit.py

    prompts/
      ceo.md
      planner.md
      research.md
      strategy_creator.md
      strategy_reviewer.md
      codegen.md
      simulation.md
      simulation_analyst.md
      robustness.md
      statistical_validator.md
      risk_reviewer.md
      portfolio_manager.md
      execution.md
      reporter.md
      audit.md

    orchestration/
      orchestrator.py
      task_manager.py
      workflow.py
      state.py
      evaluator.py

  api/
    public.py
    data.py
    indicator.py
    strategy.py
    simulation.py
    analytics.py
    risk.py
    execution.py
    reporting.py
    agents.py

  ui/
    components/
      ai-chat/
    providers/
    hooks/
    stores/
    app/

  db/
    session.py
    models.py
    repositories.py
    migrations/

  configs/
    constitution.md
    risk_policy.md
    agent_permissions.md
    strategy_lifecycle.md
    risk_thresholds.yaml
    agent_registry.yaml
    tool_registry.yaml
    live_trading.yaml

  reports/
    daily/
    weekly/
    monthly/
    board/
    simulations/
    risk/
    audit/

  tests/
    unit/
    integration/
    acceptance/
    red_team/
```

---

## 8. Phase Summary

| Phase | Name | Outcome |
|---:|---|---|
| 0 | Agentic Chat Architecture Alignment | Chat becomes CEO Agent interface with approved architecture and governance |
| 1 | Global CEO Chat Widget | Global chat widget available on all authenticated pages |
| 2 | Conversations, Memory, and Thread Continuity | Durable CEO conversations with summaries and page-independent memory |
| 3 | Page Context Injection | CEO Agent becomes page-aware and entity-aware |
| 4 | CEO Agent Gateway and Streaming Orchestration | Chat routes to CEO Agent and streams responses |
| 5 | Tool Registry and Permissioned Read-Only Tools | CEO can answer using safe HaruQuant state |
| 6 | UX Maturity and Conversation Operations | Search, rename, delete, regenerate, export, provenance, polished UI |
| 7 | Agentic Trading Intelligence | CEO delegates to research, strategy, simulation, analytics, and risk agents |
| 8 | Strategy Creation and Simulation Workflow | CEO can create, review, code, simulate, analyze, and report strategies |
| 9 | Risk, Prop-Firm, and Lifecycle Governance | CEO can evaluate strategies and proposals against firm rules |
| 10 | Internal Knowledge and Evidence Retrieval | CEO answers from docs, reports, memories, and evidence |
| 11 | Supervised Action Drafts and Board Approval Queue | CEO creates drafts but cannot execute without approval |
| 12 | Governed Paper Automation | Approved paper actions run through RiskGovernor and audit |
| 13 | Observability, Latency, Cost, and Scale | Production telemetry, budgets, rate limits, dashboards |
| 14 | Certification, Rollout, and Operations | Controlled release, rollback, training, support, steady-state ops |

---

# Phase 0 - Agentic Chat Architecture Alignment

## Objective

Establish the architecture, boundaries, schemas, and governance rules for the CEO-facing chatbot before implementation.

## Key update from old plan

The chatbot is no longer the primary intelligence. The `CEOAgent` is the primary intelligence. The chat is the UI and transport layer.

## Tasks

1. Approve the CEO-chat architecture:
   - `ui/` global chat widget,
   - `api/routes/ai_chat.py`,
   - `services/conversation/`,
   - `services/context/`,
   - `agents/ceo.py`,
   - `agents/planner.py`,
   - `tools/`,
   - `services/`.
2. Freeze the `ChatThread` schema.
3. Freeze the `ChatMessage` schema.
4. Freeze the `PageContext` schema.
5. Freeze the `AgentTask` schema.
6. Freeze the `AgentPlan` schema.
7. Freeze the `ToolCall` schema.
8. Freeze the `EvidenceRef` schema.
9. Define chat-to-agent routing:
   - all user chat starts with `CEOAgent`,
   - CEO may delegate to Planner,
   - Planner may route to specialist agents,
   - specialist agents may call tools,
   - tools call services.
10. Define safety boundary:
    - free-form chat cannot place live orders,
    - agents cannot call services directly,
    - agents must call permissioned tools,
    - tools must audit,
    - critical tools must enforce RiskGovernor and approval requirements.
11. Replace old tool tier labels with HaruQuant tool tiers:
    - read-only,
    - analysis/write,
    - critical,
    - human-approval required,
    - RiskGovernor required.
12. Define response modes:
    - direct CEO answer,
    - page-aware summary,
    - evidence-grounded explanation,
    - research memo,
    - strategy spec draft,
    - simulation report,
    - risk memo,
    - action draft,
    - approval request,
    - blocked-by-policy response.
13. Define observability and audit baseline.
14. Define rollout gates.

## Deliverables

- `docs/haruquant/plans/CEO_Chatbot_Implementation_Plan.md`
- `docs/haruquant/specs/CEO_Chat_Architecture.md`
- `docs/haruquant/specs/CEO_Chat_Context_Contract.md`
- `docs/haruquant/specs/CEO_Chat_Event_Schema.md`
- `docs/haruquant/specs/Agent_Plan_Schema.md`
- `docs/haruquant/specs/Tool_Call_Schema.md`
- `configs/agent_registry.yaml`
- `configs/tool_registry.yaml`
- `configs/agent_permissions.md`
- updated `configs/risk_policy.md`
- updated `configs/strategy_lifecycle.md`

## Suggested owners

- Primary: AI Platform Lead
- Supporting: Backend Lead, Frontend Lead, Quant/Risk Lead, Security/Compliance Owner

## Dependencies

- Governance docs complete:
  - Constitution
  - Risk Policy
  - Agent Permissions
  - Strategy Lifecycle
- Final HaruQuant folder structure approved.

## Acceptance criteria

- Architecture diagram approved.
- CEO Agent is explicitly defined as the only chat entry agent.
- Direct chatbot-to-broker execution is explicitly prohibited.
- Chat memory, page context, agent task state, and system state are separated.
- Tool tier matrix approved.
- Human approval and RiskGovernor boundaries approved.
- All schema contracts are versioned.
- Audit requirements signed off.

---

# Phase 1 - Global CEO Chat Widget

## Objective

Deploy a global chat widget shell that represents the CEO Agent and is available on every authenticated HaruQuant page.

## Tasks

1. Add global CEO chat launcher in the UI shell.
2. Implement bottom-right expandable chat widget.
3. Label the assistant as `HaruQuant CEO` or `HaruQuant Chief Investment Officer`.
4. Add route-aware header label:
   - page type,
   - active entity,
   - active tab.
5. Add status indicators:
   - ready,
   - thinking,
   - planning,
   - using tools,
   - waiting for approval,
   - blocked by policy,
   - offline.
6. Implement responsive desktop and mobile layouts.
7. Implement multiline prompt input.
8. Add local UI state persistence.
9. Add empty-state CEO welcome message.
10. Add offline and backend-unavailable states.

## Deliverables

```text
ui/components/ai-chat/ChatLauncher.tsx
ui/components/ai-chat/ChatPanel.tsx
ui/components/ai-chat/ChatHeader.tsx
ui/components/ai-chat/ChatInput.tsx
ui/components/ai-chat/MessageList.tsx
ui/components/ai-chat/CEOStatusBadge.tsx
ui/stores/chatWidgetStore.ts
ui/providers/CEOChatProvider.tsx
```

## Suggested owners

- Primary: Frontend Lead
- Supporting: Product Owner, QA Lead

## Dependencies

- Phase 0 architecture decisions.

## Acceptance criteria

- Widget visible on all authenticated product pages.
- Widget identifies itself as the CEO Agent interface.
- Expand/collapse works without page reload.
- Widget does not unmount during route transitions.
- Mobile layout remains usable.
- Header displays current route/page context label.
- Accessibility basics pass.

---

# Phase 2 - Conversations, Memory, and Thread Continuity

## Objective

Introduce durable CEO conversations, message history, rolling summaries, and continuity across refresh and navigation.

## Tasks

1. Create conversation storage schema:
   - `chat_threads`,
   - `chat_messages`,
   - `chat_summaries`,
   - `chat_context_events`,
   - `agent_task_refs`,
   - `tool_call_refs`,
   - `evidence_refs`.
2. Implement thread create/list/get/delete APIs.
3. Implement message persistence.
4. Implement streaming-safe partial message persistence.
5. Implement rolling summary generation.
6. Implement pinned facts store.
7. Implement reload-safe thread restoration.
8. Implement thread title generation rules.
9. Define retention and archival policy.
10. Ensure page context does not pollute durable memory unless explicitly saved.
11. Link CEO conversation turns to agent task IDs.

## Deliverables

```text
services/conversation/service.py
services/conversation/memory.py
services/conversation/summaries.py
services/conversation/title.py
services/schemas/chat.py
db/models.py
db/repositories.py
api/routes/ai_chat.py
ui/hooks/useCEOChatThread.ts
```

## Suggested owners

- Primary: Backend Lead
- Supporting: AI Platform Lead, Frontend Lead

## Dependencies

- Phase 0
- Phase 1 UI shell

## Acceptance criteria

- User can start a chat, refresh, and resume the same thread.
- Navigating between pages does not lose conversation history.
- Long CEO conversations remain coherent using summary plus recent window.
- Page context is not incorrectly stored as permanent memory.
- Thread title generation works.
- Delete and retention behavior comply with policy.
- API and DB tests pass.

---

# Phase 3 - Page Context Injection

## Objective

Make the CEO Agent page-aware by injecting structured page context on route changes and major UI state changes.

## Tasks

1. Define versioned `PageContext` schema.
2. Build frontend page context provider.
3. Build backend `ContextAssembler`.
4. Add context builders for dashboard, strategy lab, strategy detail, simulation/backtest result detail, analytics, risk center, execution center, agent task board, board room, reports, and data pages.
5. Include route, page type, active entity, active tab, visible filters, selected timeframe, visible metrics, data freshness, authority level, and current user role.
6. Add freshness markers.
7. Add authority markers:
   - UI-observed,
   - database canonical,
   - simulation result,
   - broker snapshot,
   - user-provided,
   - LLM-derived.
8. Limit payload size with compact summaries.
9. Prevent raw table dumps into prompts.
10. Add context revision events to conversation metadata.

## Deliverables

```text
services/context/service.py
services/context/builders.py
services/context/freshness.py
services/schemas/chat.py
ui/providers/PageContextProvider.tsx
ui/hooks/usePageContext.ts
ui/stores/pageContextStore.ts
```

## Suggested owners

- Primary: Backend Lead
- Supporting: Frontend Lead, Quant/Risk Lead

## Dependencies

- Phase 2 durable conversations.
- Existing UI pages and service access paths.

## Acceptance criteria

- Same user question returns page-relevant answers on different pages.
- CEO can identify current page, active tab, and primary entity.
- Thread memory persists while current page context updates automatically.
- Context packet remains within token budget.
- Unsupported pages degrade gracefully.
- CEO distinguishes between current page context and durable memory.

---

# Phase 4 - CEO Agent Gateway and Streaming Orchestration

## Objective

Replace placeholder chat responses with streamed CEO Agent responses and structured orchestration.

## Tasks

1. Build chat endpoint with streaming response support.
2. Implement CEO request lifecycle:
   - authenticate user,
   - load thread,
   - load memory summary,
   - load current page context,
   - build CEO input packet,
   - invoke CEO Agent,
   - stream response,
   - persist response,
   - log audit event.
3. Implement `CEOAgent`.
4. Implement `PlannerAgent`.
5. Implement orchestration loop: reason, plan, act, observe, evaluate, finish.
6. Implement cancellation.
7. Implement retry handling.
8. Implement model routing.
9. Add response schemas.
10. Add failure fallbacks and degraded responses.

## Deliverables

```text
api/routes/ai_chat.py
agents/ceo.py
agents/planner.py
agents/orchestration/orchestrator.py
agents/orchestration/task_manager.py
agents/orchestration/state.py
agents/prompts/ceo.md
agents/prompts/planner.md
services/schemas/agent.py
services/schemas/chat.py
```

## Suggested owners

- Primary: AI Platform Lead
- Supporting: Backend Lead, Frontend Lead

## Dependencies

- Phase 2
- Phase 3

## Acceptance criteria

- Responses stream in real time.
- User can cancel a request safely.
- Every chat request is routed through CEO Agent.
- Planner output is inspectable in debug mode.
- CEO can delegate to at least one specialist agent in test mode.
- Errors surface clearly without corrupting thread state.
- Conversation response is persisted after streaming.

---

# Phase 5 - Tool Registry and Permissioned Read-Only Tools

## Objective

Ground the CEO Agent in real HaruQuant state through safe read-only tools.

## Tasks

1. Build tool registry.
2. Build tool permission checker.
3. Build base tool wrapper.
4. Build audit wrapper for all tools.
5. Define read-only tool contracts.
6. Implement policy tools.
7. Implement data tools.
8. Implement strategy read tools.
9. Implement simulation read tools.
10. Implement analytics summary tools.
11. Implement risk snapshot tools.
12. Add tool timeout and retry policy.
13. Add response provenance markers.
14. Add UI tool disclosure.

## Deliverables

```text
tools/registry.py
tools/permissions.py
tools/base.py
tools/policy.py
tools/data.py
tools/strategy.py
tools/simulation.py
tools/analytics.py
tools/risk.py
tools/audit.py
configs/tool_registry.yaml
```

## Suggested owners

- Primary: Agent Tools Lead
- Supporting: AI Platform Lead, Backend Lead, Quant/Risk Lead

## Dependencies

- Phase 4 orchestration.
- Service layer for data, strategy, simulation, analytics, and risk.

## Acceptance criteria

- CEO can answer using live HaruQuant state.
- Only read-only tools are enabled in this phase.
- Tool calls are permission-checked.
- Tool calls are audit-logged.
- Tool provenance appears in logs and optionally UI.
- Tool failures degrade gracefully instead of hallucinating.

---

# Phase 6 - UX Maturity and Conversation Operations

## Objective

Make the CEO chat interface production-usable for daily workflow.

## Tasks

1. Add scrollable virtualized message history.
2. Add conversation search.
3. Add rename/delete/archive thread.
4. Add regenerate last response.
5. Add export conversation.
6. Add message actions: copy, pin, save as note, create task, attach evidence.
7. Add timing metrics.
8. Add response status indicators.
9. Add tools-used and data-source disclosure.
10. Add agent path disclosure.
11. Add keyboard shortcuts.
12. Add improved accessibility.
13. Add polished loading/skeleton/pending states.

## Deliverables

```text
ui/components/ai-chat/ThreadSidebar.tsx
ui/components/ai-chat/ToolTrace.tsx
ui/components/ai-chat/AgentTrace.tsx
ui/components/ai-chat/MessageActions.tsx
ui/components/ai-chat/ApprovalBanner.tsx
api/routes/ai_chat.py
services/conversation/service.py
```

## Suggested owners

- Primary: Frontend Lead
- Supporting: Backend Lead, Product Owner, QA Lead

## Dependencies

- Phases 2 through 5.

## Acceptance criteria

- Users can search, rename, delete, archive, and export conversations.
- Regenerate works without duplicating side effects.
- UX remains responsive with long threads.
- User can see when tools/agents were used.
- Accessibility and keyboard workflows pass QA.

---

# Phase 7 - Agentic Trading Intelligence

## Objective

Turn the CEO chat into a true trading-firm interface by enabling domain-specialist delegation.

## Tasks

1. Implement `ResearchAgent`.
2. Implement `StrategyCreatorAgent`.
3. Implement `StrategyReviewerAgent`.
4. Implement `CodegenAgent`.
5. Implement `SimulationAgent`.
6. Implement `SimulationAnalystAgent`.
7. Implement `RiskReviewerAgent`.
8. Implement `ReporterAgent`.
9. Implement `AuditAgent`.
10. Create prompts for each agent.
11. Define agent output schemas.
12. Implement task creation and delegation.
13. Implement evidence references.
14. Add domain response modes.

## Deliverables

```text
agents/research.py
agents/strategy_creator.py
agents/strategy_reviewer.py
agents/codegen.py
agents/simulation.py
agents/simulation_analyst.py
agents/risk_reviewer.py
agents/reporter.py
agents/audit.py
agents/prompts/*.md
services/schemas/agent.py
```

## Suggested owners

- Primary: AI Platform Lead
- Supporting: Quant/Risk Lead, Backend Lead

## Dependencies

- Phase 5 grounded tools.
- Phase 6 UX maturity.

## Acceptance criteria

- CEO can delegate work to specialist agents.
- Specialist agent outputs are structured and auditable.
- CEO final response summarizes specialist outputs.
- Agent task tree is visible in debug/admin UI.
- Domain answers are grounded in HaruQuant state and evidence.

---

# Phase 8 - Strategy Creation and Simulation Workflow

## Objective

Enable the first complete vertical agentic workflow:

```text
CEO -> Planner -> Research -> Strategy Creator -> Strategy Reviewer -> Codegen -> Simulation -> Analytics -> Risk Reviewer -> Reporter -> CEO final memo
```

## Tasks

1. Implement strategy spec creation.
2. Implement strategy spec validation.
3. Implement strategy review.
4. Implement code generation.
5. Implement strategy test generation.
6. Implement simulation request creation.
7. Implement simulation run.
8. Implement analytics calculation.
9. Implement simulation analysis.
10. Implement risk review.
11. Implement CEO final memo generation.
12. Implement strategy lifecycle state transitions.
13. Store all evidence references.
14. Add report generation.
15. Add acceptance tests for the full workflow.

## Deliverables

```text
services/strategy/
services/simulation/
services/analytics/
services/risk/
tools/strategy.py
tools/code.py
tools/simulation.py
tools/analytics.py
tools/risk.py
agents/strategy_creator.py
agents/strategy_reviewer.py
agents/codegen.py
agents/simulation.py
agents/simulation_analyst.py
agents/risk_reviewer.py
reports/simulations/
```

## Suggested owners

- Primary: Quant/Risk Lead
- Supporting: AI Platform Lead, Backend Lead, QA Lead

## Dependencies

- Phase 7 agentic trading intelligence.
- Core services for strategy, simulation, analytics, risk.

## Acceptance criteria

- User can ask: “CEO, create and validate a EURUSD H1 mean-reversion strategy.”
- CEO creates a plan and delegates to specialists.
- Strategy spec is generated and validated.
- Strategy review catches untestable or unsafe logic.
- Codegen creates runnable strategy code.
- Simulation runs.
- Analytics are calculated.
- Risk review is produced.
- CEO returns final recommendation: reject, revise, run robustness, or admit to paper candidate queue.
- All steps are traceable.

---

# Phase 9 - Risk, Prop-Firm, and Lifecycle Governance

## Objective

Ensure CEO chat and all agentic workflows obey the HaruQuant constitution, prop-firm risk policy, agent permissions, and strategy lifecycle.

## Tasks

1. Implement deterministic RiskGovernor service.
2. Implement prop-firm compliance service.
3. Implement consistency scoring.
4. Implement kill-switch service.
5. Implement lifecycle state transition validator.
6. Implement risk/lifecycle tools.
7. Add CEO responses for blocked actions.
8. Add audit verification tools.

## Deliverables

```text
services/risk/governor.py
services/risk/prop_firm.py
services/risk/consistency.py
services/risk/kill_switch.py
services/strategy/validators.py
tools/risk.py
agents/risk_reviewer.py
agents/audit.py
configs/risk_policy.md
configs/strategy_lifecycle.md
```

## Suggested owners

- Primary: Quant/Risk Lead
- Supporting: Security/Compliance Owner, Backend Lead, AI Platform Lead

## Dependencies

- Governance documents.
- Phase 8 strategy and simulation workflow.

## Acceptance criteria

- CEO cannot promote strategy without required evidence.
- Risk Reviewer explains deterministic RiskGovernor outputs.
- Prop-firm rule violations are detected and block actions.
- Best Day Rule is tracked.
- Kill switch can block execution attempts.
- Audit can verify risk/lifecycle compliance.

---

# Phase 10 - Internal Knowledge and Evidence Retrieval

## Objective

Allow the CEO Agent to answer questions using HaruQuant documents, governance files, reports, evidence, lessons, and internal artifacts.

## Tasks

1. Identify knowledge domains.
2. Build retrieval service.
3. Build evidence service.
4. Build citation/provenance behavior.
5. Define freshness and trust ranking.
6. Add internal Q&A mode.
7. Add retrieval tools.
8. Add UI citation rendering.
9. Add retrieval quality tests.

## Deliverables

```text
services/retrieval/service.py
services/retrieval/indexer.py
services/retrieval/search.py
services/memory/evidence.py
services/memory/institutional.py
tools/retrieval.py
ui/components/ai-chat/Citations.tsx
```

## Suggested owners

- Primary: AI Platform Lead
- Supporting: Backend Lead, Product Owner

## Dependencies

- Phase 4 orchestration.
- Docs and reports corpus.

## Acceptance criteria

- CEO answers internal-system questions from indexed docs.
- CEO cites source artifacts where possible.
- CEO distinguishes current data from older docs.
- Retrieval quality meets relevance threshold.
- Missing documents are acknowledged rather than hallucinated.

---

# Phase 11 - Supervised Action Drafts and Board Approval Queue

## Objective

Enable the CEO Agent to draft actions for user approval without direct execution authority.

## Tasks

1. Define action draft schemas.
2. Implement action draft service.
3. Implement approval queue.
4. Implement Board approval UI.
5. Add entitlement checks.
6. Add risk pre-check before draft creation.
7. Add immutable audit events.
8. Ensure regenerate does not repeat side effects.
9. Add draft expiration and cancellation.
10. Add CEO response mode: `approval_required`.

## Deliverables

```text
services/schemas/execution.py
services/audit/service.py
tools/task.py
tools/risk.py
ui/app/board-room/
ui/components/approval/ApprovalCard.tsx
api/routes/agents.py
```

## Suggested owners

- Primary: Backend Lead
- Supporting: Frontend Lead, Quant/Risk Lead, Security/Compliance Owner

## Dependencies

- Phase 9 governance.
- Phase 10 evidence retrieval.

## Acceptance criteria

- Draft actions require human confirmation.
- Unauthorized roles are blocked.
- Risk pre-check is enforced before draft creation.
- Drafts are auditable.
- Regenerate does not duplicate side effects.
- CEO clearly explains what approval is needed and why.

---

# Phase 12 - Governed Paper Automation

## Objective

Introduce tightly governed paper automation through CEO-approved workflows, RiskGovernor checks, and audit logs.

## Tasks

1. Implement paper broker service.
2. Implement paper execution tools.
3. Implement execution command schema.
4. Implement execution gating.
5. Convert approved drafts into validated paper commands.
6. Add replayable execution log.
7. Add operator override controls.
8. Add kill-switch controls.
9. Run scenario drills.
10. Add paper execution reports.

## Deliverables

```text
services/execution/paper.py
services/execution/service.py
services/risk/kill_switch.py
tools/execution.py
agents/execution.py
reports/daily/
reports/audit/
```

## Suggested owners

- Primary: Quant/Risk Lead
- Supporting: Backend Lead, DevOps/SRE, AI Platform Lead

## Dependencies

- Phase 11 supervised actions.
- Paper environment readiness.
- RiskGovernor complete.

## Acceptance criteria

- No live execution path is enabled in this phase.
- All paper actions pass RiskGovernor checks.
- Every paper action is replayable from logs.
- Kill switch can block all paper execution attempts instantly.
- CEO can summarize paper performance and execution incidents.

---

# Phase 13 - Observability, Latency, Cost, and Scale

## Objective

Make the CEO chat and agentic layer operable, traceable, and economically sustainable.

## Tasks

1. Instrument request latency, stream latency, agent latency, tool latency, service latency, token usage, cost, model routing, and failure rates.
2. Add dashboards.
3. Add alerts.
4. Add per-model and per-workflow cost accounting.
5. Add caching for stable context fragments.
6. Add rate limits.
7. Add concurrency controls.
8. Add queueing and backpressure.
9. Add context compaction.
10. Define p50 and p95 latency targets.
11. Define workflow budgets.

## Deliverables

```text
services/cost/service.py
services/cost/usage.py
services/cost/routing.py
services/audit/service.py
agents/reporter.py
reports/weekly/
reports/monthly/
```

## Suggested owners

- Primary: DevOps/SRE
- Supporting: AI Platform Lead, Backend Lead

## Dependencies

- Phase 4 and above.
- Sufficient production-like traffic.

## Acceptance criteria

- p95 latency target is defined and measured.
- Per-conversation and per-workflow cost is visible.
- Alerts exist for error spikes, tool failures, and cost anomalies.
- Load tests pass agreed concurrency thresholds.
- CEO can report operational health of the agentic firm.

---

# Phase 14 - Certification, Rollout, and Operations

## Objective

Release safely through controlled rollout stages and establish steady-state operating procedures.

## Tasks

1. Build full QA checklist.
2. Build certification checklist.
3. Run internal dogfooding.
4. Run read-only CEO chat beta.
5. Run context-aware CEO beta.
6. Run strategy/simulation beta.
7. Run supervised-action beta.
8. Run paper-automation pilot.
9. Prepare rollback playbooks.
10. Prepare incident response playbooks.
11. Train users and operators.
12. Define support ownership.
13. Define prompt/tool tuning ownership.
14. Define post-launch KPI review.

## Deliverables

```text
docs/rollout/CEO_Chat_Rollout_Plan.md
docs/runbooks/CEO_Chat_Incident_Runbook.md
docs/runbooks/Agentic_Firm_Support_SOP.md
tests/acceptance/
tests/red_team/
```

## Suggested owners

- Primary: Product Owner
- Supporting: QA Lead, Security/Compliance Owner, DevOps/SRE, AI Platform Lead

## Dependencies

- All prior phases as applicable to rollout scope.

## Acceptance criteria

- Each rollout ring has explicit entry and exit criteria.
- Rollback path is tested.
- Support handoff completed.
- Post-launch KPI set agreed.
- Red-team tests for prompt injection, privilege escalation, and tool misuse pass.
- Paper automation is proven reversible and auditable before release.

---

# 9. Cross-Phase Standards

## Required architectural rules

- Chat UI must remain globally mounted.
- Chat always talks to the CEO Agent first.
- CEO Agent may delegate but cannot bypass Planner, tool policy, RiskGovernor, or audit.
- Conversation memory must be durable and separate from page context.
- Page context must be structured, compact, versioned, and freshness-marked.
- Current system state is more authoritative than prior chat memory.
- Agents may generate proposals and drafts; they may not directly mutate live broker state.
- All tool calls must pass allowlist policy.
- All tool calls must be audited.
- Critical tools require approval and/or RiskGovernor checks.
- Live execution cannot be enabled without full governance.
- MCP is out of scope for this version.

## Required quality standards

- Unit tests for all services.
- Unit tests for all tool wrappers.
- Integration tests for CEO chat continuity.
- Integration tests for agent delegation.
- Contract tests for schemas.
- Security tests for prompt injection.
- Security tests for privilege escalation.
- Security tests for data leakage.
- Regression tests for RBAC and action gating.
- Acceptance tests for page context.
- Red-team tests for forbidden tool use.

## Required UX standards

- Fast first render for widget.
- Responsive mobile fallback.
- Clear user-visible states:
  - thinking,
  - planning,
  - using tools,
  - delegating,
  - waiting for approval,
  - blocked by policy,
  - error,
  - completed.
- No silent failures.
- Every approval request must explain why approval is required.
- Every blocked action must explain the blocking policy.

---

# 10. Updated Dependency Graph

```text
Phase 0 blocks all phases.
Phase 1 depends on Phase 0.
Phase 2 depends on Phase 1.
Phase 3 depends on Phase 2.
Phase 4 depends on Phases 2 and 3.
Phase 5 depends on Phase 4 and core services.
Phase 6 depends on Phases 2 through 5.
Phase 7 depends on Phase 5.
Phase 8 depends on Phase 7 and simulation services.
Phase 9 depends on Phase 8 and governance docs.
Phase 10 depends on Phase 4 and corpus readiness.
Phase 11 depends on Phases 8 through 10.
Phase 12 depends on Phase 11 and RiskGovernor readiness.
Phase 13 depends on Phase 4+ maturity.
Phase 14 depends on target rollout scope.
```

---

# 11. Updated Milestones

| Milestone | Included phases | Target outcome |
|---|---|---|
| A | 0-2 | Global persistent CEO chat |
| B | 3-5 | Context-aware CEO chat grounded in HaruQuant state |
| C | 6-8 | CEO can delegate strategy/simulation/risk workflows |
| D | 9-11 | CEO enforces governance and creates approval-gated drafts |
| E | 12 | Governed paper automation |
| F | 13-14 | Production rollout, observability, support, certification |

---

# 12. Recommended Execution Order

If capacity is limited, execute in this order:

1. Phase 0 - Agentic Chat Architecture Alignment
2. Phase 1 - Global CEO Chat Widget
3. Phase 2 - Conversations, Memory, and Thread Continuity
4. Phase 3 - Page Context Injection
5. Phase 4 - CEO Agent Gateway and Streaming Orchestration
6. Phase 5 - Tool Registry and Permissioned Read-Only Tools
7. Phase 6 - UX Maturity and Conversation Operations
8. Phase 7 - Agentic Trading Intelligence
9. Phase 8 - Strategy Creation and Simulation Workflow
10. Phase 9 - Risk, Prop-Firm, and Lifecycle Governance
11. Phase 10 - Internal Knowledge and Evidence Retrieval
12. Phase 13 - Observability, Latency, Cost, and Scale
13. Phase 11 - Supervised Action Drafts and Board Approval Queue
14. Phase 12 - Governed Paper Automation
15. Phase 14 - Certification, Rollout, and Operations

Reason: get CEO chat and read-only intelligence useful early, then implement the full agentic trading workflow, then gated drafts, then paper automation.

---

# 13. Immediate Next Sprint Recommendation

## Scope

- Finalize Phase 0 CEO-chat architecture.
- Implement Phase 1 global CEO chat widget shell.
- Start Phase 2 conversation schema and backend skeleton.
- Stub Phase 4 CEO Agent and Planner Agent with no tools.
- Stub Phase 5 tool registry with read-only tools disabled by default.

## Deliverables

```text
ui/components/ai-chat/
ui/providers/CEOChatProvider.tsx
services/conversation/service.py
services/schemas/chat.py
agents/ceo.py
agents/planner.py
agents/prompts/ceo.md
agents/prompts/planner.md
agents/orchestration/orchestrator.py
tools/registry.py
tools/permissions.py
api/routes/ai_chat.py
```

## Acceptance criteria

- CEO chat widget visible across authenticated app.
- Thread create/list/get works in development.
- No chat reset on route navigation.
- CEO Agent returns a basic streamed response.
- Planner stub returns structured plan.
- Tool registry exists but no side-effectful tools enabled.
- Audit log records chat request and response.

---

# 14. Program Definition of Done

The CEO Chatbot initiative is complete when:

1. The assistant is globally available and persistent.
2. The chat talks to the HaruQuant CEO Agent by default.
3. The CEO Agent retains durable thread memory while correctly using current page context.
4. The CEO Agent answers using grounded HaruQuant services, reports, memory, and internal knowledge.
5. The CEO Agent delegates to specialist agents for strategy, simulation, analytics, risk, reporting, and audit.
6. The CEO Agent can create structured strategy specs, simulation requests, risk memos, reports, and supervised action drafts.
7. No trading action can bypass risk, audit, approval, lifecycle, or execution governance.
8. Prop-firm risk controls are enforced before any paper or live execution workflow.
9. Paper automation is controlled, observable, replayable, and reversible.
10. Production telemetry, cost tracking, support runbooks, and rollback paths are in place.

---

# 15. Governing Principle

The CEO Agent must remember the conversation, but it must trust current HaruQuant system state more than prior chat memory.

The CEO Agent may recommend, summarize, delegate, draft, and request approval. It must not directly place live trades, change risk thresholds, bypass tool permissions, bypass RiskGovernor, bypass the kill switch, or bypass audit logging.

Final rule:

```text
Chat is the interface.
CEO is the coordinator.
Tools are the safety boundary.
Services are the business logic.
RiskGovernor protects the account.
Audit records everything.
Human Board approves high-impact actions.
```

