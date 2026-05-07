# HaruQuant AI Chatbot Implementation Plan

Status: canonical feature implementation plan
Scope: phased delivery plan for the HaruQuant AI chatbot and trading copilot
Use this when: you need the full execution roadmap, phase tasks, owners, deliverables, dependencies, and acceptance criteria
Companion docs: `../specs/AI_Chatbot_Architecture.md`, `../specs/AI_Chatbot_Context_Contract.md`, `../specs/AI_Chatbot_Event_Schema.md`, `../governance/AI_Chatbot_Execution_Safety.md`, `../governance/AI_Chatbot_RBAC_Matrix.md`
Owner: product owner and AI platform lead
Review cadence: weekly during active implementation

## Purpose

This document is the canonical phased implementation plan for introducing a
global, context-aware AI chatbot into HaruQuant.

The feature is intentionally staged so HaruQuant gains early value through
read-only intelligence and workflow assistance before any supervised action or
paper automation capability is considered.

## Strategic Goals

1. Provide a persistent AI assistant available on every authenticated page.
2. Preserve conversation continuity across navigation while injecting current
   page context.
3. Ground responses in HaruQuant state, tools, and internal documents rather
   than generic model output.
4. Progress safely from a basic chatbot to a context-aware copilot, then to a
   signal assistant, then to a supervised action assistant, then to tightly
   governed automation.
5. Preserve strict execution boundaries, auditability, approval controls, and
   rollback capability.

## Planning Assumptions

- HaruQuant already has an agentic AI direction with agents, tools, governed
  orchestration, and frontend separation.
- The chatbot is global, but its intelligence must remain page-aware.
- Page context is additive and ephemeral; thread memory is durable.
- No phase may bypass execution governance.
- Direct LLM-to-broker execution is prohibited.
- Production readiness requires observability, RBAC, auditability, retention,
  rollback, and policy enforcement.

## Suggested Ownership Model

| Role                        | Responsibility                                                     |
| --------------------------- | ------------------------------------------------------------------ |
| Product Owner               | Scope, prioritization, rollout decisions                           |
| AI Platform Lead            | LLM gateway, orchestration, prompts, model routing                 |
| Frontend Lead               | Widget, state management, streaming UI, context provider           |
| Backend Lead                | API endpoints, conversation service, persistence, context service  |
| Quant / Risk Lead           | Signal semantics, risk checks, governor rules, trading constraints |
| MCP / Tooling Lead          | Tool contracts, adapters, read/write boundary enforcement          |
| DevOps / SRE                | Infrastructure, deployment, monitoring, scaling, secrets           |
| QA Lead                     | Test plans, regression coverage, acceptance certification          |
| Security / Compliance Owner | RBAC, audit, retention, prompt injection and misuse review         |

## Workstreams

1. Architecture and governance
2. Frontend chat experience
3. Conversation and memory backend
4. Context injection layer
5. AI orchestration and streaming
6. Read-only tooling
7. Trading intelligence
8. Governed actions and risk controls
9. Search, retrieval, and knowledge
10. Observability, cost, and scale
11. Testing, rollout, and operations

## Phase Summary

| Phase | Name                                           | Outcome                                                   |
| ----- | ---------------------------------------------- | --------------------------------------------------------- |
| 0     | Architecture Alignment and Contract Freeze     | Approved architecture, schemas, governance boundaries     |
| 1     | Global Widget Foundation                       | Global expandable chat widget on all authenticated pages  |
| 2     | Persistent Conversations and Memory            | Durable threads and session continuity                    |
| 3     | Page Context Injection                         | Route-aware, entity-aware assistant context               |
| 4     | AI Gateway and Streaming Orchestration         | Real-time model responses with structured orchestration   |
| 5     | Read-Only HaruQuant Tool Integration           | Grounded answers using platform state                     |
| 6     | UX Maturity and Conversation Management        | Search, delete, regenerate, export, polished interaction  |
| 7     | Trading Intelligence Copilot                   | Strategy, backtest, and risk-aware domain intelligence    |
| 8     | Signal Assistant Mode                          | Structured signal proposals with zero execution authority |
| 9     | Supervised Action Layer                        | Drafts and operator-approved actions                      |
| 10    | Execution Governance and Paper Automation      | Governed, auditable paper execution                       |
| 11    | Retrieval and Internal Knowledge Grounding     | Answers from docs, reports, and internal artifacts        |
| 12    | Observability, Latency, Cost, and Scale        | Production telemetry and cost-managed serving             |
| 13    | Certification, Rollout, and Operationalization | Safe release, rollback, and steady-state ops              |

## Phase Details

### Phase 0 - Architecture Alignment and Contract Freeze

#### Objective

Establish the architecture, boundaries, schemas, and governance rules before
feature implementation.

#### Tasks

1. Define end-to-end AI chatbot system architecture.
2. Freeze the conversation thread schema and page context schema.
3. Define tool permission tiers: read-only, simulated actions, draft actions,
   live actions.
4. Define AI-to-action boundary and ban direct broker invocation from
   free-form chat.
5. Define audit logging requirements and data retention policy.
6. Define role model and entitlement matrix.
7. Define streaming transport approach and failure handling.
8. Define model routing strategy and prompt composition structure.

#### Deliverables

- `docs/haruquant/plans/AI_Chatbot_Implementation_Plan.md`
- `docs/haruquant/specs/AI_Chatbot_Architecture.md`
- `docs/haruquant/specs/AI_Chatbot_Context_Contract.md`
- `docs/haruquant/specs/AI_Chatbot_Event_Schema.md`
- `docs/haruquant/governance/AI_Chatbot_Execution_Safety.md`
- `docs/haruquant/governance/AI_Chatbot_RBAC_Matrix.md`

#### Suggested Owners

- Primary: AI Platform Lead
- Supporting: Backend Lead, Security / Compliance Owner, Quant / Risk Lead

#### Dependencies

- none

#### Acceptance Criteria

- architecture diagram approved
- context schema versioned
- tool tier matrix approved
- explicit decision recorded that LLM cannot place live trades directly
- audit and RBAC requirements signed off

### Phase 1 - Global Widget Foundation

#### Objective

Deploy a global AI widget shell on every page with expand/collapse behavior and
persistent UI presence.

#### Tasks

1. Add a global chat launcher in the app shell.
2. Implement bottom-right widget with expand/collapse states.
3. Build responsive desktop and mobile layouts.
4. Add route-aware header label.
5. Add draft input area with multiline support.
6. Add local widget state persistence.
7. Add loading, empty, and offline states.

#### Deliverables

- `ui/components/ai-chat/ChatLauncher.tsx`
- `ui/components/ai-chat/ChatPanel.tsx`
- `ui/components/ai-chat/ChatHeader.tsx`
- `ui/components/ai-chat/ChatInput.tsx`
- `ui/components/ai-chat/MessageList.tsx`
- `ui/stores/chatWidgetStore.ts`
- layout integration change

#### Suggested Owners

- Primary: Frontend Lead
- Supporting: Product Owner, QA Lead

#### Dependencies

- phase 0 architecture decisions

#### Acceptance Criteria

- widget visible on all authenticated product pages
- expand/collapse works without page reload
- widget does not unmount during route transitions
- mobile layout remains usable
- accessibility basics pass

### Phase 2 - Persistent Conversations and Memory

#### Objective

Introduce durable threads, message history, summaries, and continuity across
refresh and navigation.

#### Tasks

1. Design conversation storage schema.
2. Implement thread create/list/get/delete API.
3. Implement message persistence.
4. Implement rolling summary generation for long chats.
5. Implement pinned facts store for durable user/entity context.
6. Add reload-safe thread restoration.
7. Add thread title generation rules.
8. Define retention and archival policy.

#### Deliverables

- `services/conversation_service.py`
- `repositories/conversation_repository.py`
- `repositories/message_repository.py`
- `repositories/memory_summary_repository.py`
- DB migrations for conversation tables
- conversation API endpoints
- frontend thread restore behavior

#### Suggested Owners

- Primary: Backend Lead
- Supporting: AI Platform Lead, Frontend Lead

#### Dependencies

- phase 0
- phase 1 UI shell

#### Acceptance Criteria

- user can start chat, refresh browser, and resume same thread
- navigating between pages does not lose conversation history
- long chats remain coherent using summary plus recent window
- delete and retention behavior comply with policy
- API and DB tests pass

### Phase 3 - Page Context Injection

#### Objective

Make the assistant context-aware by injecting structured, page-specific context
on every route change.

#### Tasks

1. Define normalized `page_context` schema.
2. Build client-side context observer hooked to route changes.
3. Build backend `ContextAssembler` service.
4. Implement page-specific context builders for dashboard, strategy detail,
   backtest detail, optimization, portfolio/risk, live trading, data, and
   operator/workflow pages.
5. Limit payload size with compact summaries.
6. Add freshness markers and authority markers to context.
7. Add context revision events to conversation metadata.
8. Add guardrails to prevent raw table dumps into prompts.

#### Deliverables

- `services/context_service.py`
- `services/context_builders/*.py`
- `ui/providers/PageContextProvider.tsx`
- `ui/hooks/usePageContext.ts`
- versioned context schema
- route-to-context registry

#### Suggested Owners

- Primary: Backend Lead
- Supporting: Frontend Lead, Quant / Risk Lead

#### Dependencies

- phase 2 durable conversations
- existing page and domain data access paths

#### Acceptance Criteria

- same user question returns page-relevant answers on different pages
- thread memory persists while current page context updates automatically
- context packet size remains within token budget
- unsupported pages degrade gracefully with generic context

### Phase 4 - AI Gateway and Streaming Orchestration

#### Objective

Replace placeholder responses with real model-backed responses and structured
orchestration.

#### Tasks

1. Build AI gateway endpoint for chat requests.
2. Implement streaming response transport.
3. Implement request lifecycle: authenticate, load thread, load memory summary,
   assemble context, classify intent, route prompt/tool/agent mode, stream
   response, persist result.
4. Implement cancellation and retry handling.
5. Add model routing policy by task class.
6. Implement prompt builder with layered context.
7. Implement output schemas for structured response modes.
8. Add failure fallbacks and degraded responses.

#### Deliverables

- `api/ai_chat.py`
- `services/ceo_gateway.py`
- `agents/executive/planner_agent/service.py`
- `services/prompt_builder.py`
- `services/stream_manager.py`
- request and response schemas
- frontend streaming handler

#### Suggested Owners

- Primary: AI Platform Lead
- Supporting: Backend Lead, Frontend Lead

#### Dependencies

- phase 2
- phase 3

#### Acceptance Criteria

- responses stream in real time
- requests can be canceled safely
- prompt composition logs are inspectable in debug mode
- routing works across plain answer versus tool-assisted answer
- errors surface clearly in UI without corrupting thread state

### Phase 5 - Read-Only HaruQuant Tool Integration

#### Objective

Ground the assistant in real HaruQuant state through safe read-only tools.

#### Tasks

1. Define read-only tool contracts.
2. Expose tools for portfolio summary, open positions, backtest summary,
   strategy parameters, optimization results, risk snapshot, alert history, and
   symbol stats.
3. Add adapter wrappers where applicable.
4. Implement tool usage logging.
5. Add tool timeout and retry policy.
6. Add response provenance markers in the UI.
7. Add allowlist-based tool policy enforcement.

#### Deliverables

- `tools/read_only/*.py`
- `agents/runtime/tool_executor.py`
- `policies/tool_policy.py`
- provenance display in UI
- tool integration tests

#### Suggested Owners

- Primary: MCP / Tooling Lead
- Supporting: AI Platform Lead, Backend Lead, Quant / Risk Lead

#### Dependencies

- phase 4 orchestration
- domain data access layer stability

#### Acceptance Criteria

- assistant can answer using live HaruQuant state
- read-only tools are the only enabled tool class
- tool call provenance appears in logs and optionally in UI
- tool failures degrade gracefully to explanation instead of silent
  hallucination

### Phase 6 - UX Maturity and Conversation Management

#### Objective

Make the assistant production-usable from a daily workflow perspective.

#### Tasks

1. Add scrollable virtualized message history.
2. Add conversation search.
3. Add conversation deletion and rename.
4. Add regenerate last response.
5. Add export conversation.
6. Add timing metrics and response status indicators.
7. Add message actions: copy, pin, save note.
8. Add tools-used and data-source disclosure.
9. Add polish: animation, transitions, skeleton states, pending states.
10. Add keyboard shortcuts and improved accessibility.

#### Deliverables

- conversation management UI
- export endpoint and format spec
- regenerate endpoint
- search API and UI
- timing and status display

#### Suggested Owners

- Primary: Frontend Lead
- Supporting: Backend Lead, Product Owner, QA Lead

#### Dependencies

- phases 2 through 5

#### Acceptance Criteria

- users can search, rename, delete, and export conversations
- regenerate works without duplicating tool side effects
- UX remains responsive under long-thread load
- accessibility and keyboard workflows pass QA

### Phase 7 - Trading Intelligence Copilot

#### Objective

Add domain-specific intelligence so the assistant becomes a true trading
copilot.

#### Tasks

1. Define domain prompts for strategy explanation, backtest interpretation,
   drawdown diagnosis, risk explanation, optimization comparison, and
   performance summary.
2. Add structured response modes: summary, compare, warning, recommendation,
   diagnostic.
3. Add domain templates for core trading questions.
4. Add quantitative grounding rules to avoid vague answers.
5. Add human-readable explanations for metrics and anomalies.

#### Deliverables

- domain prompt library
- structured response format definitions
- test corpus for common trading questions
- benchmark set for answer quality

#### Suggested Owners

- Primary: Quant / Risk Lead
- Supporting: AI Platform Lead, Product Owner

#### Dependencies

- phase 5 grounded data access
- phase 6 UX maturity

#### Acceptance Criteria

- assistant gives materially useful, domain-aware answers
- quant team signs off on explanation quality for core workflows
- metric explanations remain grounded in actual system state

### Phase 8 - Signal Assistant Mode

#### Objective

Allow the assistant to generate structured trade or research signal proposals
without execution authority.

#### Tasks

1. Define `signal_proposal` schema.
2. Add signal proposal response mode.
3. Add confidence, rationale, and risk note fields.
4. Add workflow to save proposals to watchlist or review queue.
5. Clearly label all signal proposals as non-executed.
6. Add review screen for comparing AI proposals to deterministic model outputs.
7. Add anti-overclaim rules in prompts and output validators.

#### Deliverables

- `signal_proposal` schema
- review queue UI
- proposal persistence model
- save-to-watchlist flow
- evaluation suite for proposal format validity

#### Suggested Owners

- Primary: Quant / Risk Lead
- Supporting: AI Platform Lead, Backend Lead, Frontend Lead

#### Dependencies

- phase 7 domain intelligence
- policy approval from Security / Compliance Owner

#### Acceptance Criteria

- assistant can output structured signal proposals
- no signal proposal can directly place or simulate a live order
- all proposals include risk notes and confidence metadata
- proposal queue is auditable

### Phase 9 - Supervised Action Layer

#### Objective

Enable AI-assisted but human-approved actions.

#### Tasks

1. Define action draft schemas for order draft, backtest launch, optimization
   launch, export request, and simulation request.
2. Add approval UI and confirmation steps.
3. Add entitlement checks by role.
4. Add risk pre-check hook before any action creation.
5. Add immutable audit event for all action attempts and approvals.
6. Add operator queue for pending AI-generated drafts.
7. Ensure regenerate does not repeat side-effectful actions.

#### Deliverables

- action draft schemas
- approval modal and workflow
- audit event pipeline
- action queue UI
- backend action orchestration service

#### Suggested Owners

- Primary: Backend Lead
- Supporting: Quant / Risk Lead, Security / Compliance Owner, Frontend Lead

#### Dependencies

- phase 8
- approved RBAC and audit policy

#### Acceptance Criteria

- draft actions require human confirmation
- all action attempts are logged
- unauthorized roles are blocked
- risk pre-check is enforced before action creation
- side effects are idempotent or protected against duplication

### Phase 10 - Execution Governance and Paper Automation

#### Objective

Introduce governed execution, starting strictly in paper or simulated mode.

#### Tasks

1. Build trade action governor service.
2. Define execution gating checks: account mode, trading session status, symbol
   tradability, role entitlement, exposure limits, concentration limits, VaR or
   drawdown budget, kill switch, approved strategy status.
3. Convert approved action drafts into validated command objects.
4. Integrate with paper-trading bridge only.
5. Add replayable execution log.
6. Add operator override and kill-switch controls.
7. Run scenario drills and failure tests.

#### Deliverables

- `services/execution/trade_action_governor.py`
- validated command schema
- paper execution adapter
- execution audit log
- kill-switch controls
- scenario playbooks

#### Suggested Owners

- Primary: Quant / Risk Lead
- Supporting: Backend Lead, MCP / Tooling Lead, DevOps / SRE

#### Dependencies

- phase 9 supervised actions
- paper-trading environment readiness

#### Acceptance Criteria

- no live execution path exists in this phase
- all paper actions pass governor checks
- every paper action is replayable from logs
- kill switch can block all paper execution attempts instantly

### Phase 11 - Retrieval and Internal Knowledge Grounding

#### Objective

Give the assistant retrieval over HaruQuant docs, reports, and internal
artifacts.

#### Tasks

1. Identify knowledge domains: architecture docs, strategy docs, runbooks,
   reports, experiment summaries, incident notes.
2. Build indexing and retrieval layer.
3. Add citation and provenance behavior.
4. Add hybrid search where appropriate.
5. Define document freshness and trust ranking.
6. Add retrieval-augmented answer mode for internal questions.

#### Deliverables

- retrieval service
- indexed corpus pipeline
- citation rendering in chat
- retrieval quality benchmark

#### Suggested Owners

- Primary: AI Platform Lead
- Supporting: MCP / Tooling Lead, Product Owner

#### Dependencies

- phase 4 orchestration
- documentation corpus availability

#### Acceptance Criteria

- assistant can answer internal-system questions using indexed docs
- answers show provenance where possible
- retrieval quality meets defined relevance threshold

### Phase 12 - Observability, Latency, Cost, and Scale

#### Objective

Make the AI layer operable and economically sustainable in production.

#### Tasks

1. Instrument request latency, stream latency, tool latency, token usage, and
   cost.
2. Add dashboards and alerts.
3. Add per-model and per-endpoint cost accounting.
4. Add caching for stable context fragments and repeated queries.
5. Add rate limits and concurrency controls.
6. Add queueing and backpressure behavior.
7. Add context compaction policies and budget enforcement.
8. Define p50 and p95 latency targets and cost budgets.

#### Deliverables

- telemetry dashboards
- alert rules
- token and cost accounting reports
- caching policy
- scale test results

#### Suggested Owners

- Primary: DevOps / SRE
- Supporting: AI Platform Lead, Backend Lead

#### Dependencies

- phases 4 through 11 with sufficient maturity

#### Acceptance Criteria

- p95 latency target defined and measured
- per-conversation cost is visible
- alerts exist for error spikes, tool failures, and cost anomalies
- load tests pass agreed concurrency thresholds

### Phase 13 - Certification, Rollout, and Operationalization

#### Objective

Release safely through controlled rollout stages and establish steady-state
operating procedures.

#### Tasks

1. Build full QA and certification checklist.
2. Run internal dogfooding.
3. Run read-only beta.
4. Run signal-assistant beta.
5. Run supervised-action beta.
6. Run paper-automation pilot.
7. Prepare rollback and incident response playbooks.
8. Train users and operators.
9. Define ownership for support and ongoing prompt and tool tuning.

#### Deliverables

- rollout plan
- go/no-go checklist
- incident runbooks
- user training materials
- support SOP
- post-launch review template

#### Suggested Owners

- Primary: Product Owner
- Supporting: QA Lead, Security / Compliance Owner, DevOps / SRE, AI Platform Lead

#### Dependencies

- all prior phases as applicable to release scope

#### Acceptance Criteria

- each rollout ring has explicit entry and exit criteria
- rollback path tested
- support handoff completed
- post-launch KPI set agreed

## Cross-Phase Standards

### Required Architectural Rules

- chat UI must remain globally mounted
- conversation memory must be durable and separate from page context
- page context must be structured, compact, and versioned
- LLMs may generate proposals, never direct live broker mutations
- all tool calls must pass allowlist policy
- all action attempts must be audited
- live execution cannot be enabled without governor enforcement

### Required Quality Standards

- unit tests for all services and context builders
- integration tests for chat continuity and tool usage
- contract tests for APIs and schemas
- security testing for prompt injection, privilege escalation, and data leakage
- load testing for streaming concurrency
- regression tests for role permissions and action gating

### Required UX Standards

- fast first render for widget
- responsive mobile fallback
- clear user-visible states for thinking, tool running, waiting, blocked by
  policy, and approval required
- no silent failures

## Dependency Graph

- phase 0 blocks all phases
- phase 1 is required for user-visible deployment
- phase 2 depends on 0 and 1
- phase 3 depends on 0 and 2
- phase 4 depends on 2 and 3
- phase 5 depends on 4
- phase 6 depends on 2 through 5
- phase 7 depends on 5 and 6
- phase 8 depends on 7
- phase 9 depends on 8
- phase 10 depends on 9
- phase 11 depends on 4 and corpus readiness
- phase 12 depends on post-phase-4 maturity
- phase 13 depends on target rollout scope

## Milestones

| Milestone | Included Phases | Target Outcome                                                          |
| --------- | --------------- | ----------------------------------------------------------------------- |
| A         | 0-2             | Global persistent assistant                                             |
| B         | 3-5             | Context-aware copilot grounded in HaruQuant data                        |
| C         | 6-7             | Production-usable AI copilot for research, backtests, and risk analysis |
| D         | 8-9             | Structured proposals and human-approved operational workflows           |
| E         | 10-13           | Paper automation, retrieval, observability, and safe rollout            |

## Recommended Execution Order

If capacity is limited, execute in this order:

1. phase 0
2. phase 1
3. phase 2
4. phase 3
5. phase 4
6. phase 5
7. phase 6
8. phase 7
9. phase 11
10. phase 8
11. phase 9
12. phase 12
13. phase 10
14. phase 13

## Immediate Next Sprint Recommendation

### Scope

- finalize phase 0 documents
- implement phase 1 widget shell
- start phase 2 conversation schema and API

### Deliverables

- architecture approval pack
- visible global widget
- conversation CRUD backend skeleton
- initial DB migration
- thread persistence stub
- route observer stub

### Acceptance Criteria

- leadership sign-off on architecture and safety boundaries
- widget visible across authenticated app
- thread create/list/get working in development
- no chat reset on route navigation

## Program Definition of Done

The AI chatbot initiative is complete when:

1. the assistant is globally available and persistent
2. it retains thread memory while correctly updating current page context
3. it answers using grounded HaruQuant data and internal knowledge
4. it can generate structured proposals and supervised action drafts
5. no trading action can bypass risk, audit, approval, and execution
   governance
6. paper automation is controlled, observable, and reversible
7. production telemetry, support runbooks, and rollback paths are in place

## Governing Principle

The assistant must remember the conversation, but it must trust current system
state more than prior chat memory.
