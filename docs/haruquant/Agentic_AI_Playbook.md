# Agentic AI Systems Documentation Playbook

> **Version:** 1.1.3 Final  
> **Editing Principle:** Re-write and re-orient when helpful, but never strip out important information  
> **Purpose:** A single, sequential, detailed documentation playbook for designing, building, integrating, operating, governing, debugging, and evolving production-grade agentic AI systems.  
> **Primary Stack:** Google Agent Development Kit (ADK) for reasoning and orchestration, Model Context Protocol (MCP) for standardized external capabilities.  
> **Audience:** AI architects, backend engineers, systems designers, implementation teams, operators, security reviewers, future maintainers, and machine-assisted builders.

---

# 1. Why This Playbook Exists

Use this playbook whenever you want to:

* design a new agentic AI system
* document a production-ready multi-agent architecture
* define system boundaries between reasoning and external capabilities
* choose the correct workflow pattern for a use case
* decide whether a capability belongs in ADK, MCP, a tool, a resource, or a prompt
* structure memory, state, routing, evaluation, and approvals
* create standards for implementation, testing, deployment, debugging, governance, and operations
* build reusable, maintainable systems instead of ad hoc AI pipelines
* preserve explicit design logic for future-you

This document is intentionally written to be useful as:

* a technical architecture document
* a build and implementation playbook
* a reusable note system for future design work
* a machine-readable and human-readable reference for how the system should be built and operated

## 1.1 Authoring Rule for Future Versions

This playbook is not only a management artifact and not only a coding guide.

It is also:

* a future reference manual for the system architect
* a recovery guide when returning to the system months later
* a decision aid for choosing workflow patterns and boundaries
* a documentation backbone for companion documents like SRS, Design, Runbooks, Policy Maps, and ADRs

### Governing editorial rule

> **When in doubt, prefer explicitness over elegance.**

### Versioning rule

Future versions may re-order, tighten language, and improve structure, but should follow this rule:

> **Add and clarify. Do not silently remove useful engineering detail.**

---

# 2. Core Philosophy

An agentic system is not just an LLM with tool calls.  
It is a structured system with:

* reasoning
* planning
* action
* observation
* evaluation
* refinement

That loop is the foundation of all serious agentic systems.

## 2.1 The Core Loop

```text
User Goal
  ↓
Reason (LLM) → ADK handles planning, CoT/ReAct, routing logic
  ↓
Plan (Tasks) → ADK decomposes into workflow nodes
  ↓
Act (Tools/APIs) → MCP standardizes capability exposure & execution
  ↓
Observe (Results) → MCP returns structured tool/resource outputs
  ↓
Evaluate (Self/External) → ADK Evaluator scores quality & correctness
  ↓
Refine (Loop or Finish) → Feedback loops, retry logic, or final response
```

This loop must appear explicitly or implicitly in every workflow you design.

## 2.2 Enterprise Extension of the Core Loop

In production and enterprise settings, the loop must also account for:

* policy enforcement
* approval boundaries
* evidence capture
* auditability
* rollback or compensation
* cost governance
* escalation paths

So a production interpretation often becomes:

```text
Reason → Plan → Policy Check → Act → Observe → Evaluate → Approve / Refine / Compensate / Finish
```

This is an extension, not a replacement, of the original loop.

## 2.3 Golden Mental Model

**ADK is the brain.  
MCP is the capability bus.**

This single distinction prevents a large amount of design confusion.

---

# 3. System Design Principle

Every production-grade agentic system should be designed in layers.

## 3.1 Recommended Layered Architecture

```text
┌─────────────────────────────────────────────────────────────┐
│               Interface & Routing Layer                     │
│  • User-facing entry points (FastAPI/Flask Gateway, web ui,│
│    CLI, Chat Interface, etc.)                              │
│  • ADK Router Agent     • Intent Classifier & Dispatcher   │
└───────────────────────┬─────────────────────┬───────────────┘
                        │                     │
┌───────────────────────▼──────────┐ ┌───────▼────────────────┐
│        ADK Orchestration         │ │    Workflow Engine     │
│  • Session & Context Manager     │ │  • Sequential/Parallel │
│  • Task Decomposer & Planner     │ │  • Conditional Routing │
│  • Conflict & State Sync         │ │  • Eval-Optimizer Loop │
└───────────────────────┬──────────┘ └───────┬────────────────┘
                        │                     │
┌───────────────────────▼─────────────────────▼────────────────┐
│                  ADK Agent Layer (Workers)                    │
│  • Persona/Role-Defined Agents  • Tool-Augmented LLMs        │
│  • Structured I/O (Pydantic)    • Short/Long-Term Memory     │
└───────────────────────┬─────────────────────┬────────────────┘
                        │                     │
┌───────────────────────▼─────────────────────▼────────────────┐
│              MCP Capability Bus (Integration Layer)           │
│  • MCP Client Wrappers (stdio/HTTP) → Domain MCP Servers     │
│  • Tools (Do) • Resources (Read) • Prompts (Guide)           │
└───────────────────────┬─────────────────────┬────────────────┘
                        │                     │
┌───────────────────────▼─────────────────────▼────────────────┐
│                Data & External Systems                        │
│  • Vector DBs (Chroma/Vertex/etc.) • SQL/NoSQL               │
│  • Web Search • REST/MCP APIs • Files • Services             │
└───────────────────────┬─────────────────────┬────────────────┘
                        │                     │
┌───────────────────────▼─────────────────────▼────────────────┐
│           Evaluation & Observability Layer                    │
│  • ADK Evaluator Class • LLM-as-Judge • Trajectory Logs      │
│  • MCP Inspector/Debug • Cloud Logging • Cost/Latency        │
└──────────────────────────────────────────────────────────────┘
```

## 3.2 Why the Explicit Routing Layer Must Remain

The routing layer must stay visible because it answers:

* who receives the request first
* who normalizes it
* who classifies intent
* who dispatches to the correct workflow
* where first-pass policy checks happen
* where fallback/default routing lives

The routing layer is not “just a detail.”  
It is one of the highest-value design anchors in an agentic system.

## 3.3 Enterprise Overlay on the Layered Architecture

The original layered design remains the technical spine.  
The enterprise additions sit across these layers:

* security and identity
* approval and escalation
* policy enforcement
* audit logging
* benchmark governance
* ownership and change control
* incident response
* cost control

These are cross-cutting controls, not substitutes for the original architecture.

## 3.4 Architecture Review Questions

When reviewing architecture, ask:

* Is the routing layer explicit?
* Is orchestration separated from capability access?
* Are side-effecting capabilities behind clean boundaries?
* Is state ownership clear?
* Is evaluation visible as a first-class layer?
* Are policy, approval, and audit concerns layered on top instead of mixed into everything?

---

# 4. Unified Mental Model: ADK + MCP

To build robust systems, separate intelligence from capability access.

## 4.1 ADK Handles

* reasoning
* planning
* orchestration
* routing
* memory and state
* multi-agent workflow coordination
* evaluation and refinement loops

## 4.2 MCP Handles

* standardized access to external capabilities
* tools
* resources
* reusable prompts
* protocol-based boundaries between host and capability providers

## 4.3 Division of Responsibility

| Layer | Responsibility |
|---|---|
| **Host / ADK App** | user interaction, reasoning, planning, memory, routing, approvals, final synthesis |
| **MCP Client** | protocol connector, session management, capability discovery, clean interface to host |
| **MCP Server** | capability provider, domain-specific tools/resources/prompts, business logic |

**Golden Rule 1:** ADK is the brain. MCP is the capability bus.  
**Golden Rule 2:** Host plans. Client connects. Server provides.

## 4.4 Design Consequence

If the system starts mixing:

* memory into servers
* orchestration into servers
* policy only into prompts
* domain logic only into the host

then boundaries usually start degrading.

---

# 5. MCP Design Standard

MCP should be used to expose external capability boundaries cleanly.

## 5.1 MCP Architecture

```text
User
  ↓
Host Application / ADK Agent
  ↓
MCP Client
  ↓
MCP Server
```

## 5.2 Server Capability Model

| Type | Purpose | Naming Convention | Example |
|---|---|---|---|
| **Tool** | Do/Act | `verb_noun` | `calculate_var`, `place_order`, `search_docs` |
| **Resource** | Read/State | `domain://path` | `risk://policy`, `market://symbol/EURUSD` |
| **Prompt** | Guide/Template | `*_prompt` | `risk_review_prompt`, `trade_approval_prompt` |

### Quick rule

* does it do something? → tool
* does it show something? → resource
* does it guide something? → prompt

## 5.3 Client Features & Decision Rules

| Feature | Purpose | When to Use |
|---|---|---|
| **Roots** | Scope context/folders | Server should focus on specific project dirs |
| **Sampling** | Server requests LLM generation | Client controls model access and credentials |
| **Elicitation** | Server requests user input | Missing data, confirmation, or choices needed |

### Quick rule

* scope → roots
* model generation → sampling
* more user input → elicitation

## 5.4 Transport Selection

| Transport | Best For | Rule of Thumb |
|---|---|---|
| **STDIO** | local dev, subprocess, desktop | start here; host launches server directly |
| **Streamable HTTP** | remote, multi-user, production | move here when server becomes deployable |

## 5.5 Server Design Standards

* One server = one coherent domain. Avoid god servers.
* Tools should be narrow and specific.
* Resources should be stable and readable.
* Prompts should be reusable.
* Use typed parameters, clear docstrings, and structured return values.
* Log to `stderr` only for debug in stdio mode. Never pollute `stdout`.
* Lifecycle should be: Initialize → Discover → Operate → Shutdown cleanly.

## 5.6 Client & Host Wrapper Pattern

```python
class RiskServerConnection:
    def __init__(self, session):
        self.session = session

    async def calculate_var(self, portfolio: dict) -> float:
        res = await self.session.call_tool(
            "calculate_var",
            arguments={"portfolio": portfolio}
        )
        return float(res.content[0].text)
```

### Wrapper rules

* encapsulate client logic
* initialize once and reuse sessions
* host routes → client calls → server executes → host synthesizes
* memory stays in the host
* do not push conversation state into servers

## 5.7 MCP Debugging Checklist

| Symptom | Fix |
|---|---|
| Server hangs on start | normal for stdio; it waits for JSON-RPC messages |
| JSON errors on Enter | normal; raw stdin is not MCP protocol |
| Inspector won’t connect | verify Python path, script path, dependencies, no stdout pollution |
| Tool call fails | check name, argument types, server-side error handling |
| HTTP client fails | verify endpoint, auth, transport compatibility, availability |

## 5.8 When to Introduce MCP

**Use MCP when:**

* a host or agent needs repeatable access to external capabilities
* multiple apps or agents should reuse the same capability provider
* workflows rely on manual handoffs or duplicated integrations
* there is a real system boundary
* you want protocol-level consistency

**Avoid MCP when:**

* everything is local and trivial inside one script
* no meaningful system boundary exists
* a plain internal function call is enough

## 5.9 Enterprise Additions to MCP

For each MCP server, document:

* domain purpose
* owner
* side-effect risk level
* allowed callers
* credentials used
* audit requirements
* failure modes
* rate limits
* timeout budget
* escalation owner
* contract version
* deprecation notes

## 5.10 MCP Server Template

```python
from mcp.server.fastmcp import FastMCP

mcp = FastMCP("risk_server")

@mcp.tool()
def calculate_var(portfolio: dict) -> float:
    """Calculate portfolio VaR."""
    # validate inputs
    # apply domain policy
    # execute business logic
    # return structured result
    return 0.0

@mcp.resource("risk://policy")
def risk_policy() -> str:
    return "Risk policy contents"

@mcp.prompt()
def trade_approval_prompt() -> str:
    return "Review the trade request against the current risk policy."
```

---

# 6. The Anatomy of an Agent

Every agent should be defined through core components.

| Component | Defines | Examples |
|---|---|---|
| **Persona** | role, tone, expertise, behavioral constraints | Quant Analyst |
| **Brain** | LLM, reasoning engine, output behavior, generation constraints | Gemini, OpenAI, Qwen |
| **Capabilities** | what the agent can do | call tools, query MCP, search web, query DB |
| **Memory** | what the agent can remember or retrieve | short-term state, long-term vector memory |
| **State** | what stage the agent or workflow is in | IDLE, PLANNING, EXECUTING, OBSERVING, EVALUATING, COMPLETE, ERROR |

## 6.1 Enterprise Additions to Agent Anatomy

| Component | Defines |
|---|---|
| **Policy Profile** | what the agent is allowed to do, say, access, and trigger |
| **Approval Profile** | which actions require approval, evidence, or escalation |
| **Ownership** | team owner, operational owner, on-call owner |
| **Risk Class** | read-only, low-risk write, high-risk, irreversible side effects |
| **Audit Scope** | what must be logged for traceability |

## 6.2 Agent Definition Template

```python
from pydantic import BaseModel
from google.adk.agents import Agent

class TradeAnalysisInput(BaseModel):
    symbol: str
    timeframe: str

class TradeAnalysisOutput(BaseModel):
    summary: str
    confidence: float
    risk_flags: list[str]

trade_analyst = Agent(
    name="trade_analyst",
    model="gemini-3.1-pro",
    instruction="""
You are a trade analysis agent.
Use available tools carefully.
Return structured output only.
Escalate when evidence is weak or policy blocks action.
"""
)
```

## 6.3 Agent Catalog Requirements

Each agent should be documented with:

* purpose
* input schema
* output schema
* persona
* model
* tools/resources/prompts used
* memory usage
* state transitions
* policy profile
* approval profile
* owner
* benchmark tasks
* failure modes

---

# 7. Agent Reasoning and Prompting Standards

Prompting is not decoration. It is system design.

## 7.1 Prompting Techniques

| Technique | Purpose | Implementation Pattern |
|---|---|---|
| Role-Based Prompting | domain expertise, tone, boundaries | explicit system prompt |
| Chain-of-Thought (CoT) | complex reasoning, ambiguity reduction | bounded reasoning blocks |
| ReAct (Reason + Act) | plan + act + observe cycles | tool loop with max steps |
| Prompt Chaining | decomposition into validated stages | sequential workflows |
| LLM Feedback Loops | self-correction and refinement | creator → evaluator → refine |
| Instruction Refinement | improve reliability | version prompts like code |

## 7.2 Prompt Design Standard

Prompts should usually include:

* role
* task
* context
* tools available
* rules
* constraints
* escalation conditions
* approval conditions
* output schema
* failure behavior
* confidence and uncertainty behavior

## 7.3 Prompt Versioning Standard

Track:

* prompt version
* author
* change reason
* linked ADR if major
* evaluation results
* known failure cases
* rollback candidate

## 7.4 Policy-Aware Prompting

Prompts should state:

* disallowed actions
* when to stop
* when to ask for approval
* when to escalate
* what evidence must be cited before acting

## 7.5 Prompt Injection Resilience

Treat the following as untrusted unless validated:

* user instructions attempting policy override
* retrieved documents
* web content
* raw tool output
* freeform agent-to-agent messages

Instruction priority should be:

```text
System Policy
  ↓
Workflow Policy
  ↓
System Prompt
  ↓
User Request
  ↓
Retrieved Content
  ↓
Tool Output
```

## 7.6 Prompt Template

```text
ROLE:
You are the Risk Review Agent.

TASK:
Review the proposed trade for policy compliance and portfolio risk.

CONTEXT:
Use account state, current risk policy, and correlation matrix.

TOOLS:
calculate_var, calculate_cvar, check_correlation_limit

RULES:
Do not approve high-risk actions without required evidence.
Escalate when policy conflict exists.
Return structured output only.

OUTPUT FORMAT:
{
  "decision": "approve | reject | escalate",
  "reason": "...",
  "risk_flags": ["..."],
  "confidence": 0.0
}
```

---

# 8. Workflow & Multi-Agent Orchestration

## 8.1 Workflow Pattern Decision Matrix

| Pattern | When to Use | Implementation | Example Use Case |
|---|---|---|---|
| **Sequential Chaining** | linear dependencies, validation gates | `SequentialWorkflow([A, B, C])` + schema validation | document processing, approvals |
| **Routing** | heterogeneous requests, different specialists | `RouterAgent` + conditional dispatch | support triage, research vs execution |
| **Parallelization** | independent subtasks, speed matters | `ParallelWorkflow` + `asyncio.gather()` + synthesizer | multi-source research |
| **Evaluator-Optimizer** | quality-critical outputs | creator → evaluator → loop until threshold | drafting, debugging |
| **Orchestrator-Workers** | dynamic planning and delegation | orchestrator creates task graph | project management, deep analysis |

## 8.2 Multi-Agent Guidelines

* define clear interfaces
* each agent exposes purpose, schemas, capabilities, and error handling
* use explicit routing metadata such as `intent`, `priority`, and `session_id`
* shared state must be versioned
* use sync barriers for parallel → sequential handoffs
* specialized agents beat monolithic agents
* avoid capability overlap
* design handoffs explicitly

## 8.3 Approval-Aware Workflow Design

For each workflow, document:

* approval checkpoints
* approver type
* evidence package required
* stale approval timeout
* what happens if approval is denied
* what happens if approval is unavailable

## 8.4 Compensation-Aware Workflow Design

For each side-effecting workflow, document:

* preconditions
* irreversible steps
* compensating actions
* idempotency key
* exactly-once vs at-least-once semantics
* rollback boundary
* partial completion behavior

## 8.5 Escalation-Aware Workflow Design

Specify:

* human escalation triggers
* policy escalation triggers
* ambiguity escalation triggers
* repeated-failure escalation triggers
* security anomaly escalation triggers

## 8.6 Workflow Review Template

Every significant workflow should document:

1. goal  
2. trigger  
3. input schema  
4. output schema  
5. pattern used  
6. agents involved  
7. tools/resources/prompts involved  
8. policy checks  
9. approval checks  
10. compensation design  
11. observability requirements  
12. evaluation metrics  
13. owner  
14. failure modes  

## 8.7 Workflow Template

```python
from pydantic import BaseModel

class ResearchRequest(BaseModel):
    query: str

class ResearchResult(BaseModel):
    summary: str
    citations: list[str]
    confidence: float

# route -> plan -> parallel retrieve -> synthesize -> evaluate -> finalize
```

---

# 9. Memory, State, and Context Engineering

## 9.1 Memory Types

| Type | Storage | Use Case |
|---|---|---|
| Short-Term | session context, ephemeral dict | active conversation, workflow state |
| Long-Term | vector DB, KB, structured records | user prefs, historical interactions, RAG |
| Procedural | tool registry, FSM, workflow defs, schemas, policies | routing rules, retry logic, state machines |

## 9.2 State Machines

All non-trivial workflows should have explicit state transitions.

```text
IDLE → PLANNING → EXECUTING → OBSERVING → EVALUATING → COMPLETE
                                         ↘ ERROR
```

### Rules

* define Pydantic schemas for state payloads
* transitions must be logged
* transitions must be bounded
* loops must have max iteration limits
* error states must be recoverable or terminal by design
* handle concurrency with async locks or optimistic concurrency when needed

## 9.3 Structured Output Standard

All important agent outputs should be structured.

* always enforce JSON outputs via Pydantic models
* prefer model-native JSON mode when available
* validate before passing to downstream steps

## 9.4 Context Engineering Standard

Many failures are context failures, not reasoning failures.

For each workflow, define:

* required context blocks
* optional context blocks
* ranking/prioritization order
* context budget allocation
* stale context eviction rules
* summarization/compression rules
* source-of-truth precedence rules
* contradiction resolution rules

### Context precedence example

```text
System Policy
  ↓
Workflow Policy
  ↓
Structured Session State
  ↓
Approved User Input
  ↓
Trusted Resources / Databases
  ↓
Retrieved Documents
  ↓
Raw Tool Output
```

### Context inclusion checklist

Before sending context to a model, ask:

* is it necessary?
* is it fresh?
* is it trusted?
* is it duplicated?
* is it too verbose?
* does it conflict with a higher-priority source?

## 9.5 Data Retention and Tenant Isolation

Define:

* what is stored
* how long it is stored
* who can access it
* what gets deleted
* what must be redacted
* what may be used for evaluation or retraining

If multi-tenant:

* isolate memory by tenant
* isolate vector stores or namespaces
* prevent cross-tenant retrieval
* log tenant context in traces

## 9.6 State Manager Template

```python
from enum import Enum
from pydantic import BaseModel

class WorkflowState(str, Enum):
    IDLE = "IDLE"
    PLANNING = "PLANNING"
    EXECUTING = "EXECUTING"
    OBSERVING = "OBSERVING"
    EVALUATING = "EVALUATING"
    COMPLETE = "COMPLETE"
    ERROR = "ERROR"

class StatePayload(BaseModel):
    state: WorkflowState
    session_id: str
    data: dict
```

---

# 10. External Integration Standard

## 10.1 Web Search

Use as a tool or MCP capability when current information is required.

Rules:

* ground results
* apply freshness
* cite sources
* never guess current facts

## 10.2 Databases

Use structured access patterns:

* SQLAlchemy or equivalent
* text-to-SQL with validation
* read-only replicas where appropriate
* bounded query policies

## 10.3 APIs

Wrap all major APIs through:

* ADK tools
* MCP tools
* typed clients

Add:

* timeout handling
* retries
* auth rotation
* rate limits

## 10.4 Agentic RAG

Recommended loop:

* reformulate query
* retrieve
* reflect
* retry if weak
* synthesize

## 10.5 Integration Risk Classes

Document whether each integration is:

* read-only
* low-risk write
* high-risk write
* financially material
* compliance-sensitive
* irreversible

## 10.6 Integration Wrapper Policy

Every external integration wrapper should define:

* auth method
* timeout
* retry policy
* circuit breaker policy
* idempotency support
* schema validation
* logging redaction
* error mapping
* ownership

## 10.7 Tool Output Sanitization

Never treat tool output as automatically trusted.  
Sanitize, validate, and reclassify it before reusing it as model context.

## 10.8 API Client Template

```python
import httpx

class ResearchApiClient:
    def __init__(self, base_url: str, api_key: str):
        self.base_url = base_url
        self.api_key = api_key

    async def search(self, query: str) -> dict:
        async with httpx.AsyncClient(timeout=10.0) as client:
            resp = await client.get(
                f"{self.base_url}/search",
                params={"q": query},
                headers={"Authorization": f"Bearer {self.api_key}"}
            )
            resp.raise_for_status()
            return resp.json()
```

---

# 11. Human Approval, Escalation, and Kill-Switch Standard

## 11.1 Action Classes

| Class | Description | Default Rule |
|---|---|---|
| A | read-only, no side effect | auto-allowed |
| B | low-risk write, reversible | allow with policy gate |
| C | material write, approval-worthy | require human approval |
| D | high-risk, financially material, compliance sensitive | require strict approval and audit |
| E | irreversible or prohibited | deny or require special process |

## 11.2 Approval Packet

Before approval, surface:

* proposed action
* reason for action
* evidence used
* confidence and uncertainty
* policy checks passed
* risk classification
* alternatives considered
* expected impact
* rollback or compensation plan

## 11.3 Escalation Triggers

Escalate when:

* policy conflict exists
* required evidence is missing
* repeated failures occur
* financial/compliance threshold exceeded
* ambiguity remains unresolved
* security anomaly detected

## 11.4 Kill Switch Design

Document:

* who can trigger it
* what it disables
* whether it is global or domain-specific
* whether it drains in-flight workflows or hard-stops them
* recovery procedure
* post-incident checks before re-enable

## 11.5 Approval Packet Template

```json
{
  "action": "place_order",
  "reason": "Signal confirmed by strategy and risk checks",
  "evidence": [
    "signal_summary",
    "risk_policy_check",
    "portfolio_var_result"
  ],
  "confidence": 0.86,
  "risk_class": "D",
  "alternatives": ["reduce size", "defer trade"],
  "compensation_plan": "close position if post-check fails"
}
```

---

# 12. Policy and Guardrail Enforcement Map

Policy must not live only in prompts.

## 12.1 Enforcement Layers

| Layer | What to Enforce |
|---|---|
| UI / Gateway | auth, request validation, rate limits |
| Routing Layer | request class, tenant checks, allowed workflow |
| Host / Orchestrator | policy selection, approval gating, escalation |
| Agent Prompt | behavioral constraints, evidence rules |
| Tool Wrapper | argument validation, timeout/retry policy |
| MCP Server | domain-specific business policy |
| Downstream System | final authorization, transaction constraints |

## 12.2 Policy Categories

* input policy
* output policy
* tool-use policy
* data access policy
* model policy
* approval policy
* escalation policy
* retention policy

## 12.3 Policy Authoring Rule

Every policy should define:

* name
* scope
* owner
* enforcement layer
* failure behavior
* logging requirement
* exception process
* review cadence

## 12.4 Policy Map Template

```yaml
policy_name: trade_execution_policy
scope: execution_workflows
owner: risk_team
enforcement_layers:
  - routing
  - orchestrator
  - mcp_server
failure_behavior: reject_and_escalate
logging_requirement: audit_log_required
review_cadence: monthly
```

---

# 13. Failure Recovery, Idempotency, and Compensation

## 13.1 Reliability Principles

* assume retries will happen
* assume partial failures will happen
* assume duplicate requests may happen
* assume downstream systems may succeed after timeout
* assume some steps cannot be rolled back

## 13.2 Required Design Decisions

For each side-effecting action, document:

* idempotency key
* duplicate detection method
* retry semantics
* compensation action
* rollback feasibility
* exactly-once vs at-least-once semantics
* audit record

## 13.3 Compensation Patterns

Examples:

* created record → mark cancelled
* sent order → place offsetting/closing order if allowed
* provisioned resource → deprovision resource
* wrong notification → send correction

## 13.4 Saga-Style Guidance

If a workflow spans multiple systems:

* define step order
* define compensation order
* define commit boundary
* define terminal failure handling

## 13.5 Compensation Template

```python
class CompensationPlan:
    def __init__(self, action_id: str):
        self.action_id = action_id

    async def compensate(self):
        # reverse or mitigate side effect
        # log audit event
        pass
```

---

# 14. Schema Evolution and Contract Governance

## 14.1 Why It Matters

Multi-agent systems break when contracts drift invisibly.

## 14.2 Rules

* every important schema gets a version
* breaking changes require migration notes
* optional fields must be deliberate, not accidental
* contract tests must run in CI
* downstream consumers must validate, not assume

## 14.3 Contract Checklist

For each schema/interface, document:

* version
* owner
* producer
* consumer
* required fields
* optional fields
* invariants
* deprecation date
* migration strategy

## 14.4 Schema Template

```python
from pydantic import BaseModel, Field

class RiskDecisionV1(BaseModel):
    decision: str = Field(description="approve | reject | escalate")
    reason: str
    confidence: float
    risk_flags: list[str] = []
    schema_version: str = "1.0.0"
```

---

# 15. Evaluation, Reliability, and Quality Gates

## 15.1 Evaluation Strategies

| Level | Focus | Method |
|---|---|---|
| Response | final output quality | evaluator rubric, LLM-as-judge |
| Step | tool calls, intermediate logic | unit tests, schema validation, logs |
| Trajectory | full workflow efficiency | success rate, latency, cost, retries |

## 15.2 Metrics and Thresholds

| Metric | Threshold | How to Measure |
|---|---|---|
| Output Schema Compliance | ≥95% | validation logs |
| Tool/MCP Call Success | ≥98% | retry/failure counters |
| Workflow Completion | ≥90% | end-to-end test suite |
| Hallucination Rate | ≤5% | ground-truth comparison + judge |
| Latency (p95) | ≤3s simple / ≤10s complex | middleware / metrics |
| Cost per Query | project-defined | token usage × routing policy |

## 15.3 Enterprise Benchmark Governance

Evaluation is not complete without benchmark ownership.

Define:

* golden tasks
* adversarial tasks
* regression tasks
* domain hard cases
* failure-path benchmarks
* refresh cadence
* benchmark owner
* promotion criteria for prompts/models/tools

## 15.4 Promotion Policy

No prompt, model, workflow, or server should be promoted without:

* regression pass
* benchmark pass
* security review if needed
* rollback plan
* owner sign-off

## 15.5 Evaluator Template

```python
class EvaluationResult:
    def __init__(self, score: float, notes: str):
        self.score = score
        self.notes = notes

def evaluate_output(output: dict) -> EvaluationResult:
    # rubric scoring, schema check, evidence check
    return EvaluationResult(score=0.95, notes="Pass")
```

---

# 16. Trace-Level Observability and Auditability

## 16.1 Minimum Trace Fields

Every serious workflow should log:

* trace_id
* session_id
* user_id or tenant_id when applicable
* request_id
* task_id
* workflow_id
* step_id
* tool_call_id
* agent_name
* prompt_version
* model_name
* model_version if available
* latency
* cost
* result status

## 16.2 Span Model

Each workflow step should be a span:

```text
Request Span
  ├─ Routing Span
  ├─ Planning Span
  ├─ Tool Call Span(s)
  ├─ Evaluation Span
  ├─ Approval Span
  └─ Final Response Span
```

## 16.3 Audit Logging

Audit logs should capture:

* who requested the action
* who approved it
* what policy applied
* what evidence was used
* what action was taken
* when it was taken
* whether compensation occurred

## 16.4 Redaction Rules

Never log secrets or unnecessary sensitive content.  
Define:

* fields to redact
* fields to hash
* fields to omit
* retention period
* access controls

## 16.5 Logging Template

```python
def log_workflow_event(event: dict) -> None:
    # add trace_id, workflow_id, step_id, timestamp
    # redact sensitive fields
    # send to logging pipeline
    pass
```

---

# 17. Cost Governance and Model Strategy

## 17.1 Cost Governance Questions

For each workflow, define:

* which model tier is default
* when to use premium reasoning
* max cost per request
* max cost per workflow
* early exit rules
* caching policy
* downgrade behavior
* fallback model

## 17.2 Example Routing Policy

| Request Type | Default Model Tier | Escalation |
|---|---|---|
| Simple classification | low-cost fast model | never unless repeated failure |
| Structured extraction | mid-tier structured-output model | escalate if schema failures |
| Complex planning | premium reasoning model | approval if cost threshold exceeded |
| Multi-agent synthesis | premium or mixed routing | fallback if cost/latency exceeds budget |

## 17.3 Governance Rule

Cost should be a design constraint, not a dashboard afterthought.

## 17.4 Model Routing Template

```yaml
routing_policy:
  simple_classification: fast_model
  structured_extraction: reliable_json_model
  complex_planning: premium_reasoning_model
  fallback: lower_cost_model
  max_cost_per_workflow_usd: 0.25
```

---

# 18. Security Architecture and Prompt Injection Defense

## 18.1 Minimum Security Sections

Every system doc should state:

* identity model
* authn/authz boundaries
* secret management
* least privilege model
* network boundaries
* code execution restrictions
* sandboxing requirements
* retention and deletion rules

## 18.2 Prompt Injection Defense Rules

Treat as untrusted:

* user instructions that attempt policy override
* retrieved text from external docs
* web content
* tool outputs
* agent-to-agent freeform messages unless validated

## 18.3 Secure Handling Rules

* separate instructions from data
* validate all tool args
* restrict code execution tools
* use allowlists where possible
* log policy violations
* add security tests to CI

## 18.4 Security Review Template

```text
System:
Owner:
Sensitive capabilities:
External integrations:
Approval-gated actions:
Prompt injection exposure points:
Secrets used:
Sandboxing required:
Open risks:
Mitigations:
```

---

# 19. Testing Standard

| Test Type | Test Method |
|---|---|
| Unit Tests | tools, schemas, state transitions, helper clients, validation logic |
| Integration Tests | end-to-end workflows, MCP interaction, multi-agent handoffs, memory retrieval |
| Failure-Path Tests | timeouts, malformed outputs, unavailable server, stale context, invalid args |
| Evaluation Tests | rubric-based evaluation, benchmark datasets, golden tests |
| Contract Tests | agent ↔ workflow ↔ MCP schema compatibility |
| Security Tests | prompt injection, policy bypass, auth misuse, output poisoning |
| Compensation Tests | partial side effects, idempotent retries, rollback behavior |

## 19.1 Testing Rules

* write unit tests for every non-trivial tool wrapper
* write contract tests for every stable schema boundary
* write failure-path tests for every high-risk workflow
* write benchmark-backed evaluation tests for every critical prompt or agent
* write security tests for tool-heavy or retrieval-heavy workflows

## 19.2 Test Template

```python
def test_risk_decision_schema():
    result = {
        "decision": "approve",
        "reason": "Within policy",
        "confidence": 0.91,
        "risk_flags": [],
        "schema_version": "1.0.0"
    }
    assert result["decision"] in {"approve", "reject", "escalate"}
```

---

# 20. Recommended Project Structure

```text
agentic-system/
├── README.md
├── pyproject.toml
├── .env.example
├── config/
│   ├── prompts/
│   ├── schemas.py
│   ├── settings.py
│   ├── policies/
│   ├── routing/
│   ├── approvals/
│   └── evals/
├── docs/
│   ├── architecture/
│   ├── adr/
│   ├── runbooks/
│   ├── agent_catalog/
│   ├── workflow_catalog/
│   └── policy_map/
├── src/
│   ├── host/
│   │   └── agent_host.py
│   ├── agents/
│   │   ├── base_agent.py
│   │   ├── orchestrator.py
│   │   └── workers/
│   ├── workflows/
│   │   ├── chaining.py
│   │   ├── routing.py
│   │   ├── parallel.py
│   │   └── eval_opt.py
│   ├── memory/
│   │   ├── state_manager.py
│   │   └── vector_store.py
│   ├── tools/
│   │   ├── web_search.py
│   │   ├── database.py
│   │   └── api_client.py
│   ├── mcp/
│   │   ├── clients/
│   │   └── servers/
│   ├── approvals/
│   ├── policy/
│   ├── observability/
│   └── evaluation/
│       └── evaluator.py
├── tests/
│   ├── unit/
│   ├── integration/
│   ├── eval/
│   ├── failure/
│   └── contracts/
└── main.py
```

---

# 21. Designing the System Before Coding

Follow this documentation sequence every time.

## Step 1: Define the user-facing host

Document:

* what app the user speaks to
* where orchestration lives
* where approvals happen
* where memory lives

## Step 2: Define system goals

Document:

* primary user goals
* business goals
* operational goals
* non-functional constraints

## Step 3: Define domains

Split the system into coherent capability domains.

Good examples:

* market data
* risk
* execution
* research
* compliance

Bad example:

* one giant everything server

## Step 4: Define workflow types

For each user journey, specify:

* sequential
* routing
* parallel
* evaluator-optimizer
* orchestrator-workers

## Step 5: Classify capabilities

For every domain capability, classify it as:

* tool
* resource
* prompt

## Step 6: Define trust boundaries

Document:

* what is read-only
* what has side effects
* what requires approval
* what requires authentication
* what may execute external code or transactions

## Step 7: Choose transport

* stdio for local process workflows
* streamable HTTP for remote deployable services

## Step 8: Define session lifecycle

Document:

* initialize
* discover capabilities
* operate
* observe results
* shutdown or persist

## Step 9: Define approval and escalation model

Document:

* which actions are auto-approved
* which require human approval
* who can approve
* what evidence is required
* what times out
* what escalates
* what is blocked entirely

## Step 10: Define observability and audit model

Document:

* trace IDs
* session IDs
* task IDs
* tool-call IDs
* prompt versions
* model versions
* stored artifacts
* redaction rules

---

# 22. Implementation Phases

## Phase 0: Environment and Scaffold

Deliverables:

* repo initialized
* dependencies installed
* structure scaffolded
* secrets configured

Acceptance:

* imports resolve
* base agent loads
* settings validate

## Phase 1: Prompting and Reasoning Foundation

Deliverables:

* persona prompts/templates
* CoT/ReAct patterns
* creator/evaluator loop
* prompt versioning

Acceptance:

* prompt compliance tests pass
* structured output works consistently

## Phase 2: Workflow Orchestration

Deliverables:

* sequential workflows with schema gates
* router workflows with fallback
* parallel workflows with synthesis
* evaluator-optimizer loop with rubric scoring

Acceptance:

* workflows succeed end-to-end
* failures are bounded and logged

## Phase 3: Tooling, Memory, and State

Deliverables:

* MCP wrappers
* tool adapters
* FSM state machine
* short-term and long-term memory
* agentic RAG flow

Acceptance:

* tools validate inputs
* state transitions logged
* retrieval quality meets threshold

## Phase 4: Multi-Agent Production Architecture

Deliverables:

* orchestration topology
* inter-agent contracts
* specialized retrievers
* evaluation metrics
* observability hooks
* shared session versioning

Acceptance:

* multi-agent coordination stable
* no stale-state corruption
* costs and latency measurable

## Phase 5: Deployment and Operations

Deliverables:

* service or CLI packaging
* containerization
* CI/CD
* monitoring and alerts
* rollback procedures

Acceptance:

* load testing passes
* alerts exist
* deployment reproducible

## Phase 6: Enterprise Hardening

Deliverables:

* policy enforcement map
* approval service
* compensation logic
* audit logging
* security review
* benchmark governance
* runbooks
* ADRs

Acceptance:

* high-risk actions gated
* audit trail complete
* compensation tested
* incident runbooks approved
* benchmark suite in place

---

# 23. Ownership, Operating Model, and Change Control

## 23.1 Every Major Component Needs an Owner

For each agent, workflow, server, and policy, define:

* product owner
* technical owner
* operational owner
* on-call owner

## 23.2 Change Control

For major changes, require:

* ADR
* benchmark results
* migration notes
* security review if relevant
* rollback plan
* owner sign-off

## 23.3 Decommissioning

Define when to retire:

* old prompts
* old models
* old workflows
* old servers
* deprecated schemas

## 23.4 Ownership Template

```yaml
component: risk_server
product_owner: risk_platform_lead
technical_owner: backend_eng_team
operational_owner: platform_ops
on_call_owner: trading_system_oncall
```

---

# 24. Incident Response and Postmortems

## 24.1 Incident Classes

| Severity | Description |
|---|---|
| Sev 1 | harmful or critical action, severe outage, data/security risk |
| Sev 2 | material workflow failure, repeated bad outputs |
| Sev 3 | degraded behavior, local failures |
| Sev 4 | minor issue, non-critical defect |

## 24.2 Incident Response Checklist

* contain impact
* trigger kill switch if needed
* preserve logs and traces
* identify affected workflows
* compensate or correct side effects
* notify stakeholders
* patch and validate
* run postmortem

## 24.3 Postmortem Template

* summary
* impact
* timeline
* root cause
* contributing factors
* policy/control gaps
* what worked
* what failed
* corrective actions
* owner and due date

---

# 25. Architecture Decision Records (ADR) Standard

Use ADRs for major decisions such as:

* why ADK
* why MCP
* why a workflow pattern
* why a model
* why stdio vs HTTP
* why a server split by domain
* why a policy design

## 25.1 ADR Template

* title
* status
* date
* context
* decision
* consequences
* alternatives considered
* follow-up actions

---

# 26. Production Readiness Checklist and Anti-Patterns

## 26.1 Production Checklist

| Category | Requirement | Status |
|---|---|---|
| Prompting | role, CoT/ReAct, feedback loops versioned | ☐ |
| Outputs | Pydantic validation on important outputs | ☐ |
| State | session + FSM transitions logged & bounded | ☐ |
| Memory | short-term + long-term configured | ☐ |
| Tools/MCP | wrappers with retries, timeouts, schema validation | ☐ |
| Routing | intent classifier + fallback | ☐ |
| Concurrency | bounded async parallelism | ☐ |
| Evaluation | response/step/trajectory metrics tracked | ☐ |
| Security | IAM, vaulted keys, sanitization, auth gates | ☐ |
| Approvals | approval packet + escalation model | ☐ |
| Compensation | partial-failure strategy tested | ☐ |
| Observability | trace-level logging + redaction | ☐ |
| Ownership | component owners assigned | ☐ |
| Runbooks | incident and ops runbooks exist | ☐ |

## 26.2 Common Pitfalls and Mitigations

| Pitfall | Symptom | Fix |
|---|---|---|
| Unbounded loops | runaway cost/retries | cap steps, define convergence threshold |
| Hallucinated tool calls | invalid params, failed executions | strict schema validation |
| Context overflow | degraded reasoning | sliding window, summarization |
| Tight coupling | brittle workflows | config-driven routing, dependency injection |
| No evaluation | unknown failure modes | evaluator + regression suite |
| Everything is a tool | poor MCP design | classify tool/resource/prompt properly |
| God server | hard to scale/own | split by domain |
| stdout pollution | broken stdio protocol | log to `stderr` only |
| No compensation plan | unsafe partial failures | design rollback/compensation up front |
| Approval without evidence | unsafe human review | require approval packet |

---

# 27. Reference and Quick-Start

## 27.1 Syllabus Mapping

| Module | Core Output | ADK+MCP Equivalent |
|---|---|---|
| Prompting & Reasoning | CoT, ReAct, feedback loops | prompts, workflows, loops |
| Agentic Workflows | routing, parallel, eval-opt, orchestrator | workflows, router, evaluator |
| Building Agents | tools, structured I/O, state/memory | MCP clients, session, adapters |
| Multi-Agent Systems | architecture, coordination, RAG | workers, shared state, synthesis |

## 27.2 Capstone Templates

| Template | Workflow Pattern | Focus |
|---|---|---|
| Travel Planner | routing + parallel + chaining | intent → research → synthesis |
| Project Manager | orchestrator-workers + eval-opt | planner delegates → workers → critic |
| Research Agent | agentic RAG + long-term memory | retrieve → reflect → synthesize |
| Sales Team | multi-agent state + routing + RAG | routing → CRM lookup → proposal |

## 27.3 ADK + MCP Architecture Template

```text
User
  ↓
Interface / API / UI
  ↓
ADK Host / Router / Orchestrator
  ├─ MCP Client → Market Data Server
  ├─ MCP Client → Risk Server
  ├─ MCP Client → Execution Server
  ├─ MCP Client → Research Server
  └─ Internal Tools / Memory / DB / RAG
  ↓
Evaluation / Logging / Monitoring
```

---

# 28. Example Domain Blueprint for HaruQuant-Style Systems

## 28.1 Market Data Server

Tools:

* `get_latest_tick`
* `get_ohlcv`
* `get_spread`

Resources:

* `market://symbol/EURUSD`
* `market://session_calendar`

Prompts:

* `market_summary_prompt`

## 28.2 Risk Server

Tools:

* `calculate_var`
* `calculate_cvar`
* `check_correlation_limit`
* `suggest_position_size`

Resources:

* `risk://policy`
* `portfolio://current`
* `market://correlation_matrix`

Prompts:

* `risk_review_prompt`
* `trade_approval_prompt`

## 28.3 Execution Server

Tools:

* `place_order`
* `modify_order`
* `close_position`

Resources:

* `broker://account_snapshot`
* `broker://open_orders`

Prompts:

* `execution_confirmation_prompt`

## 28.4 Research Server

Tools:

* `search_notes`
* `summarize_report`

Resources:

* `research://strategy_docs`
* `research://backtest_reports`

Prompts:

* `research_summary_prompt`

## 28.5 Enterprise Overlays for These Servers

For each domain server, add:

* risk class
* policy owner
* approval class
* audit scope
* compensation options
* benchmark tasks
* on-call owner

---

# 29. Documentation Standard for Every New Agentic System

When creating system docs, include these sections in order:

1. purpose and scope  
2. goals and non-goals  
3. core reasoning loop  
4. system architecture layers  
5. host responsibilities  
6. routing layer responsibilities  
7. agent roles and interfaces  
8. workflow patterns used  
9. memory model  
10. state model  
11. context engineering standard  
12. MCP domain decomposition  
13. tool/resource/prompt catalog  
14. transport decisions  
15. security and approval boundaries  
16. policy enforcement map  
17. failure recovery and compensation  
18. evaluation framework  
19. testing strategy  
20. deployment architecture  
21. operations and observability  
22. ownership and change control  
23. pitfalls and mitigations  
24. acceptance criteria  
25. future evolution notes  

This becomes your documentation backbone.

---

# 30. Companion Documents Recommended for Enterprise Systems

For serious systems, split supporting artifacts into companion docs:

* `SRS.md`
* `Design.md`
* `Agent_Catalog.md`
* `Workflow_Catalog.md`
* `Tool_Resource_Prompt_Catalog.md`
* `Policy_Map.md`
* `Approval_and_Escalation_Standard.md`
* `Observability_and_Audit_Spec.md`
* `Security_Architecture.md`
* `Benchmark_and_Eval_Spec.md`
* `Operations_Runbook.md`
* `ADR_Index.md`

---

# 31. Final Condensed Rules

If you keep only one section, keep this one.

## Agentic AI essentials

* every workflow follows reason → plan → act → observe → evaluate → refine
* ADK handles reasoning and orchestration
* MCP handles standardized capability access
* the host owns orchestration and memory
* clients connect
* servers provide
* tools do
* resources read
* prompts guide
* start local with stdio
* move remote systems to HTTP
* keep servers domain-specific
* keep logs off stdout for stdio
* validate all important outputs
* evaluate every serious workflow
* design first, then code
* approvals must be explicit
* policies must be enforced in layers
* context must be engineered, not dumped
* side effects need compensation plans
* contracts must be versioned
* traces must be replayable and auditable
* security must assume untrusted inputs
* ownership must be explicit
* future versions should add and clarify, not silently subtract

---

# 32. Final Note

This playbook is intentionally explicit.

It is meant to help:

* future-you design faster
* teams implement more consistently
* reviewers inspect system boundaries more clearly
* operators manage production more safely
* machine-assisted builders understand what must exist and how it should fit together

A good playbook is not only elegant.  
It is usable, durable, and hard to misread.

---

*Built for production. Designed for scale. Explicit enough for future-you. Governed enough for enterprise use.*
