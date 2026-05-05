# AI Chatbot Conversational Multi-Agent Upgrade Plan

Status: proposed implementation plan  
Scope: upgrade the current HaruQuant chatbot from a routed single-response copilot into a conversational multi-agent assistant with ChatGPT/Gemini-style interaction quality  
Use this when: planning the next stage of chatbot capability after phases 0 to 13  
Companion docs: `AI_Chatbot_Implementation_Plan.md`, `../specs/AI_Chatbot_Architecture.md`, `../specs/AI_Chatbot_Context_Contract.md`, `../governance/AI_Chatbot_Execution_Safety.md`  
Owner: AI platform lead, backend lead, frontend lead  
Review cadence: weekly during design and active implementation

## Purpose

This plan defines how to evolve the HaruQuant AI chatbot from its current architecture:

1. rule-based routing  
2. context assembly  
3. optional tool execution  
4. one main model generation step  
5. fallback if model generation fails

into a genuinely conversational assistant that behaves more like ChatGPT or Gemini while remaining grounded in HaruQuant state, governance, and execution safety.

The goal is not to imitate consumer chat products superficially. The goal is to deliver:

- natural conversational flow
- stronger multi-turn memory use
- clarification before guessing
- hidden internal orchestration
- explicit tool and sub-agent reasoning behind the scenes
- stable, governed trading-domain behavior

## Current Gap

Today the chatbot is good at:

- route-aware grounding
- tool-backed summaries
- signal proposal and action draft generation
- deterministic fallbacks

Today it is still weak at:

- free-form conversational flow
- adaptive follow-up questioning
- latent planning over multiple turns
- maintaining user intent beyond the last prompt
- choosing between direct answer, tool use, clarification, and deeper reasoning in a human-like way
- hiding internal system scaffolding from the user

## Target Outcome

The upgraded chatbot should behave like a conversational HaruQuant copilot:

- it understands the user’s goal, not just the literal latest prompt
- it can ask a short clarification question when context is insufficient
- it can silently decide whether to answer directly, inspect tools, retrieve docs, or consult specialist agents
- it can continue a topic across turns without feeling stateless
- it produces concise normal-chat answers by default, with structure only when the task needs it
- it preserves all existing HaruQuant safety boundaries

## Design Principles

1. Current system state remains higher authority than chat memory.
2. Internal orchestration should be mostly invisible to the user.
3. Clarifying questions are better than confident wrong assumptions.
4. Multi-agent orchestration should be selective, not mandatory on every turn.
5. Tool and sub-agent use must remain governed, logged, and replayable.
6. The default user experience should feel conversational, not like an internal system prompt dump.

## Proposed Capability Layers

### Layer A: Conversational Turn Manager

Add a dedicated conversational controller before final generation.

Responsibilities:

- infer the user’s real intent from the current message plus recent turns
- determine whether the assistant should:
  - answer directly
  - ask a clarification question
  - use tools
  - use retrieval
  - invoke specialist agents
  - prepare a governed artifact such as a signal proposal or action draft
- preserve conversation continuity and topic state

New service candidates:

- `backend/agents/chat/ai_chat/conversation_orchestrator.py`
- `backend/agents/chat/ai_chat/intent_state.py`
- `backend/agents/chat/ai_chat/clarification_policy.py`

Acceptance criteria:

- the chatbot asks for clarification when the user request is underspecified and assumptions would materially change the answer
- repeated topic turns are handled as one ongoing discussion rather than isolated prompts

### Layer B: Hidden Planner Step

Introduce a short internal planning stage before answering.

This is not a visible chain-of-thought feature. It is an internal structured planning step that decides:

- what the user is trying to accomplish
- what evidence is needed
- what tools or agents should be used
- whether the answer is blocked on missing information

Suggested contract:

- `ConversationPlan`
  - `user_goal`
  - `answer_mode`
  - `needs_clarification`
  - `tools_to_run`
  - `agents_to_consult`
  - `response_shape`

Implementation options:

- model-generated planner using the HaruQuant runtime
- deterministic planner for low-risk cases, model planner for ambiguous cases

Acceptance criteria:

- plain conversational questions do not go through heavyweight orchestration unnecessarily
- complex questions can trigger deeper planning automatically

### Layer C: Specialist Agent Consultation

Use actual specialist agents behind the scenes when appropriate.

Examples:

- `PortfolioRiskAgent`
- `BacktestExplainerAgent`
- `OptimizationComparisonAgent`
- `StrategyCreatorAgent`
- `StrategyDiagnosticsAgent`
- `KnowledgeRetrievalAgent`

These agents should not replace the chat surface. They should support it.

Pattern:

1. conversational orchestrator decides specialist help is needed
2. one or more specialist agents produce structured intermediate outputs
3. final responder agent synthesizes them into one conversational reply

New modules:

- `backend/agents/chat/portfolio_risk_agent.py`
- `backend/agents/chat/backtest_explainer_agent.py`
- `backend/agents/chat/optimization_comparison_agent.py`
- `backend/agents/chat/final_responder_agent.py`

Acceptance criteria:

- the user sees one coherent answer, not multiple agent artifacts
- specialist agent outputs are grounded and cite their data/tool basis internally

### Layer D: Clarification and Follow-Up Memory

Add explicit short-horizon conversational memory on top of the durable thread store.

Memory classes:

- current topic
- unresolved user questions
- clarification slots
- entities under discussion
- user preference signals such as brevity, detail level, or preferred symbols/timeframes

Suggested service:

- `backend/agents/chat/ai_chat/conversation_state_service.py`

Example:

User: “Compare this run to the previous one.”  
Assistant should understand:

- what “this run” refers to from page context
- what “previous one” refers to from recent thread state or prior page entity context

Acceptance criteria:

- pronouns and references such as “this”, “that”, “previous run”, “the same strategy”, and “why again?” are handled coherently

### Layer E: Response Composer for Natural Chat

Add a final answer composer whose only job is to turn internal structured results into natural user-facing prose.

It should:

- default to natural concise answers
- only use sections when the task benefits from them
- avoid exposing internal schema labels unless requested
- preserve citations or provenance where useful without cluttering the answer

Suggested service:

- `backend/agents/chat/ai_chat/response_composer.py`

Response modes:

- direct answer
- clarification question
- evidence-backed explanation
- recommendation
- comparison
- guided next-step dialogue

Acceptance criteria:

- ordinary chat feels like conversation, not report generation
- structured outputs remain available when needed for signals/actions/governance

## Proposed Phased Delivery

### Phase C1: Conversational Foundations

Tasks:

1. add `ConversationOrchestrator`
2. add `ConversationPlan` schema
3. add clarification policy
4. add `generation_source`, `provider_name`, and runtime metadata debugging
5. refine fallback behavior to conversational tone only

Deliverables:

- `backend/agents/chat/ai_chat/conversation_orchestrator.py`
- `backend/agents/chat/ai_chat/clarification_policy.py`
- tests for clarification vs direct answer routing

### Phase C2: Topic and Reference Memory

Tasks:

1. add short-horizon conversation state store
2. track active entities and unresolved references
3. add slot resolution for “this strategy”, “previous run”, “that drawdown”
4. update prompt builder to include topic state compactly

Deliverables:

- `backend/agents/chat/ai_chat/conversation_state_service.py`
- tests for reference resolution across turns

### Phase C3: Specialist Agent Mesh

Tasks:

1. define chat-specialist agent interfaces
2. implement first three specialists:
   - backtest explainer
   - portfolio risk
   - optimization comparison
3. add final responder agent
4. add governed agent orchestration logging

Deliverables:

- `backend/agents/chat/*.py`
- `backend/agents/chat/ai_chat/agent_consultation_service.py`
- replayable intermediate artifacts

### Phase C4: Conversational UX Upgrade

Tasks:

1. show when assistant asked a clarification question
2. add expandable “sources used” and “tools used” disclosures
3. add optional debug drawer for model/provider/generation source
4. tune typing, interruption, and response streaming for a smoother feel

Deliverables:

- upgraded chat message rendering
- optional debug disclosure UI
- clarification-turn UI patterns

### Phase C5: Retrieval and Knowledge Dialogue

Tasks:

1. make retrieval conversational rather than document-snippet shaped
2. add retrieval-aware clarifications when query is broad or ambiguous
3. synthesize doc findings with current page context and thread state

Deliverables:

- conversational retrieval composer
- doc-grounded answer evaluation set

### Phase C6: Evaluation and Certification

Tasks:

1. build a conversational evaluation corpus
2. benchmark:
   - naturalness
   - coherence across turns
   - correct clarification behavior
   - tool selection quality
   - specialist-agent invocation quality
3. run red-team tests for prompt injection, retrieval contamination, and execution-boundary leaks

Deliverables:

- `tests/fixtures/ai_chat_conversational_corpus.json`
- `tests/unit/backend/services/test_ai_chat_conversational_orchestrator.py`
- `tests/eval/ai_chat_conversation_quality.py`

## Required Architecture Changes

### New Runtime Flow

Target request lifecycle:

1. authenticate user
2. load thread and conversation state
3. assemble current page context
4. build `ConversationPlan`
5. if clarification is required, return clarification question
6. otherwise run selected tools
7. optionally run specialist agents
8. synthesize results through response composer
9. persist answer, metadata, and intermediate orchestration events
10. stream final response

### Proposed New Metadata

Per assistant turn:

- `generation_source`
- `provider_name`
- `model`
- `conversation_plan_id`
- `answer_mode`
- `clarification_required`
- `specialist_agents_used`
- `tool_selection_rationale`

### Policy Requirements

All new specialist agents must obey:

- read-only constraints unless explicitly operating inside governed action flows
- tool allowlist policy
- audit logging
- context authority ordering
- execution safety boundaries

## Acceptance Criteria

The conversational upgrade is successful when:

1. ordinary user prompts feel natural and concise by default
2. ambiguous prompts trigger short, useful clarifying questions
3. multi-turn references are resolved correctly
4. specialist agents can be used without exposing internal complexity to the user
5. responses stay grounded in HaruQuant state and documents
6. signal and action workflows still remain governed and auditable
7. fallback behavior remains safe and conversational when runtime generation fails

## Immediate Next Sprint Recommendation

Build Phase C1 and C2 first.

That means:

1. add `ConversationOrchestrator`
2. add clarification policy
3. add conversation topic/reference state
4. integrate those into the existing gateway before adding more specialist agents

Reason:

- it fixes the biggest user-visible gap first
- it improves normal chat quality immediately
- it creates the right orchestration surface before adding more agents
