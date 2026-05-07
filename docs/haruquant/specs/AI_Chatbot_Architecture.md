# HaruQuant AI Chatbot Architecture

Status: canonical feature architecture spec
Scope: end-to-end architecture for the global HaruQuant AI chatbot and governed copilot
Use this when: you need the system topology, service boundaries, lifecycle, and phase-0 architecture decisions
Companion docs: `AI_Chatbot_Context_Contract.md`, `AI_Chatbot_Event_Schema.md`, `../governance/AI_Chatbot_Execution_Safety.md`, `../governance/AI_Chatbot_RBAC_Matrix.md`, `../plans/AI_Chatbot_Implementation_Plan.md`
Owner: AI platform lead and backend lead
Review cadence: weekly during phase 0 through phase 5, then quarterly

## Purpose

This document defines the approved architecture shape for the HaruQuant AI
chatbot as a global, context-aware assistant and a future governed trading
copilot.

## Architectural Principles

- the chat shell is globally mounted in the authenticated UI
- durable conversation memory is separate from current page context
- page context is structured, compact, versioned, and ephemeral
- the assistant may read, summarize, compare, diagnose, and propose
- the assistant may not directly invoke live trading actions from free-form
  chat
- action creation, approval, and execution are separate governed stages
- audit and provenance are first-class requirements, not later additions

## Logical Components

### Frontend

- `ChatLauncher`
- `ChatPanel`
- `MessageList`
- `ChatInput`
- `PageContextProvider`
- client thread store and widget UI state store

### Backend API Layer

- AI chat API endpoint
- conversation CRUD endpoints
- thread export and search endpoints
- approval endpoints for supervised actions

### Core Services

- `ConversationService`
- `MemorySummaryService`
- `PinnedFactsService`
- `ContextAssembler`
- `CEOChatGateway`
- `PlannerAgent`
- `CEOAgent`
- `PromptBuilder`
- `ToolExecutor`
- `StreamManager`

### Governance Layer

- tool policy enforcement
- RBAC checks
- audit event pipeline
- action draft validation
- risk pre-check hook
- trade action governor

### Domain and Tooling Layer

- read-only HaruQuant tools
- later supervised draft-action adapters
- retrieval/indexing service
- domain data access services

## End-to-End Request Lifecycle

1. user sends a prompt from the global widget
2. frontend includes current thread id and current `page_context`
3. backend authenticates the user and loads thread state
4. memory summary and pinned facts are loaded
5. context is assembled and compacted
6. intent is classified
7. request is routed to:
   - plain response mode
   - tool-assisted response mode
   - structured proposal mode
   - supervised action-draft mode
8. model output is streamed back incrementally
9. final assistant message, provenance, and events are persisted
10. audit records are emitted for the request and any tool or action stages

## Core Separation Rules

### Memory vs Context

- thread memory stores durable conversational continuity
- page context stores current route/entity state
- current structured system state outranks remembered natural-language state

### Read vs Write Capabilities

- read-only tools may be used for grounded answers
- simulated actions may exist only in explicitly governed modes
- draft actions require role checks, policy checks, and audit events
- live actions are out of scope for free-form chat and remain prohibited

### UI vs Backend Responsibility

- frontend owns presentation, draft input, route observation, and streaming UX
- backend owns persistence, orchestration, tool policy, audit, and context
  assembly

## Phase-0 Decisions To Freeze

- streaming transport: SSE unless a later technical review justifies WebSocket
- thread and message schema versioning enabled from day one
- context schema versioning enabled from day one
- tool permissions tiered into read-only, simulated, draft, and live classes
- live broker invocation from free-form chat explicitly forbidden
- prompt composition layered as:
  - system and governance instructions
  - user identity and entitlements
  - memory summary and pinned facts
  - current page context
  - recent thread window
  - tool results and provenance

## Suggested Initial Backend Surface

- `api/ai_chat.py`
- `services/ceo_gateway.py`
- `services/conversation_service.py`
- `services/context_service.py`
- `services/prompt_builder.py`
- `agents/planner.py`
- `agents/ceo.py`
- `services/stream_manager.py`
- `agents/runtime/tool_executor.py`
- `policies/tool_policy.py`

## Observability Requirements

- request lifecycle trace id
- streamed token timing and completion timing
- tool call latency and outcome
- context size and compaction stats
- model route, model version, and response mode
- cost accounting and retry metadata
- policy blocks and approval-required events

## Failure Modes

- widget mounted but backend unavailable
- thread restoration failure
- context assembler timeout
- tool timeout or stale data source
- model route failure
- streaming interruption
- policy block on restricted action request
- duplicate action attempts from regenerate or retry

## Acceptance Conditions For Architecture Freeze

- component ownership is clear
- request lifecycle is agreed
- memory/context separation is explicit
- action boundaries are approved
- observability and audit hooks are designed into the architecture
