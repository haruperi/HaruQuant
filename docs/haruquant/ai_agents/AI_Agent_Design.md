# AI Agentic Orchestration Layer — Technical Design

## 1. Overview

This document describes the technical design for the HaruQuant AI Agentic Orchestration Layer.

The design goal is to place a **bounded, tool-driven, auditable agent layer** above the existing deterministic HaruQuant stack. The AI layer should orchestrate and interpret existing subsystems, not replace them.

---

## 2. Design summary

### 2.1 Core idea

HaruQuant should behave like a desk of specialist roles:

- market research desk
- strategy validation desk
- risk desk
- execution oversight desk
- incident review desk
- portfolio allocation desk
- operations desk

Each of these roles becomes a specialist agent that calls structured HaruQuant tools.

### 2.2 Boundary

The AI layer does **not** own:
- core execution math
- risk truth
- governance truth
- simulation truth
- replay truth
- deterministic snapshot/report generation

The AI layer **does** own:
- task planning
- specialist selection
- tool orchestration
- evidence gathering
- summary/report generation
- escalation logic
- workflow coordination with n8n

---

## 3. Layered architecture

```text
UI / API / Chat / Scheduled Trigger / n8n
    -> Agent Gateway
    -> Planner / Router
    -> Specialist Agents
    -> Tool Registry
    -> HaruQuant Existing Engines
    -> Storage / Reports / Notifications
```

### 3.1 Agent Gateway

Responsibilities:
- receive requests from UI, API, CLI, scheduler, or n8n
- normalize request into agent task contract
- attach user, role, scope, permissions, and correlation metadata

### 3.2 Planner / Router

Responsibilities:
- classify intent
- choose workflow template
- select one or more specialist agents
- sequence tool usage

### 3.3 Specialist Agents

Responsibilities:
- run focused reasoning within one domain
- call allowed tools only
- return structured outputs

### 3.4 Tool Registry

Responsibilities:
- provide typed, schema-validated access to HaruQuant capabilities
- separate read-only, advisory-write, and privileged tools
- attach audit metadata to each tool call

### 3.5 Existing HaruQuant engines

Remain unchanged in responsibility:
- edge profile generation
- risk snapshots and governance
- recommendations and what-if
- simulator and replay
- backtests and optimization
- storage and reporting

---

## 4. Proposed module layout

```text
apps/agents/
  core/
    agent_models.py
    agent_registry.py
    tool_registry.py
    planner.py
    verifier.py
    policies.py
    prompts.py
    memory.py
    audit.py

  specialists/
    research_orchestrator.py
    edge_intelligence.py
    strategy_qa.py
    risk_supervisor.py
    execution_oversight.py
    incident_investigator.py
    portfolio_allocator.py
    live_ops.py

  tools/
    edge_tools.py
    risk_tools.py
    backtest_tools.py
    simulator_tools.py
    live_tools.py
    report_tools.py
    workflow_tools.py

  workflows/
    daily_market_brief.py
    strategy_promotion_review.py
    live_risk_watch.py
    trade_review_assistant.py
    incident_review.py

  integrations/
    llm_client.py
    n8n_client.py
    webhook_router.py
```

---

## 5. Core contracts

### 5.1 AgentTask

```python
@dataclass
class AgentTask:
    task_id: str
    task_type: str
    actor_user_id: int
    actor_role: str
    scope: str
    intent: str
    input_payload: dict[str, Any]
    correlation_id: str
    run_id: str
    approval_mode: str
```

### 5.2 AgentResult

```python
@dataclass
class AgentResult:
    status: str
    summary: str
    evidence: list[dict[str, Any]]
    recommendations: list[dict[str, Any]]
    required_actions: list[dict[str, Any]]
    warnings: list[str]
    confidence: float
    metadata: dict[str, Any]
```

### 5.3 ToolSpec

```python
@dataclass
class ToolSpec:
    tool_name: str
    domain: str
    mode: str  # read_only | advisory_write | privileged
    input_schema: dict[str, Any]
    output_schema: dict[str, Any]
    permission_policy: str
```

---

## 6. Agent execution model

### 6.1 Standard execution pattern

1. Receive task.
2. Planner selects workflow.
3. Specialist agent(s) collect evidence through tools.
4. Verifier checks evidence completeness and policy boundaries.
5. Reporter builds final structured output.
6. Audit layer stores run metadata.
7. Optional n8n integration sends notifications or continues workflow.

### 6.2 Planner → Specialist → Verifier → Reporter pattern

This pattern is recommended for all multi-step workflows.

Benefits:
- clearer responsibility boundaries
- easier testing
- easier auditing
- easier failure handling

---

## 7. Specialist agent design

## 7.1 Research Orchestrator Agent

Inputs:
- symbol universe
- timeframe
- requested analysis scope
- optional prior snapshots

Tools:
- prepare dataset
- run core metrics
- run seasonality
- run market structure
- run scorecard
- list snapshots
- compare snapshots
- export reports

Outputs:
- market brief
- top opportunities
- avoid list
- strategy-fit shortlist
- next recommended research steps

## 7.2 Edge Intelligence Agent

Inputs:
- saved edge snapshots
- market structure outputs
- seasonality summaries
- scorecard outputs

Tools:
- load snapshot detail
- compare snapshots
- load profile report

Outputs:
- tradeability interpretation
- current edge condition
- strategy suitability narrative
- degradation / improvement summary

## 7.3 Strategy QA Agent

Inputs:
- backtest id(s)
- optimization id(s)
- WFO/WFM / MC references
- strategy manifest metadata

Tools:
- fetch backtest summary
- fetch optimization summary
- fetch MC / sensitivity / WFO / WFM outputs
- fetch manifests
- export validation report

Outputs:
- promote / hold / reject
- reasons
- missing validations
- policy exceptions

## 7.4 Risk Supervisor Agent

Inputs:
- current or selected risk run
- snapshot / scorecard / regime / governance / recommendations

Tools:
- load current portfolio state
- build risk snapshot
- build scorecard
- evaluate governance
- run what-if
- list scenarios
- load recommendations

Outputs:
- risk memo
- deterioration alerts
- reduction / hedge suggestions
- safe-state classification

## 7.5 Execution Oversight Agent

Inputs:
- fills, slippage, spread, latency, reconciliation, live logs

Tools:
- fetch execution quality summaries
- fetch live logs
- fetch broker state
- fetch reconciliation events

Outputs:
- execution anomaly summary
- deployment caution signals
- operational action list

## 7.6 Incident Investigator Agent

Inputs:
- session id / backtest id / risk run / replay frame ids / log refs

Tools:
- fetch replay frames
- fetch snapshots
- fetch policy events
- fetch logs
- run what-if comparison
- fetch saved reports

Outputs:
- timeline summary
- root cause narrative
- expected vs actual behavior
- recommended preventive actions

---

## 8. Verifier layer

The verifier is responsible for checking:

1. required evidence exists
2. referenced artifacts are current and accessible
3. prerequisites were completed
4. tool outputs are internally consistent enough for reporting
5. no privileged action is being attempted outside policy

Verifier output:
- ok
- incomplete_evidence
- policy_blocked
- stale_inputs
- conflicting_inputs

---

## 9. Tooling model

### 9.1 Tool mode classes

#### Read-only tools
Examples:
- load snapshot
- compare snapshots
- fetch risk state
- fetch backtest results
- fetch replay frames
- export reports

#### Advisory-write tools
Examples:
- run what-if
- trigger report generation
- run research automation
- refresh profile batch
- start safe simulation review job

#### Privileged tools
Examples:
- stop live session
- change risk limits
- promote strategy
- deploy to live
- place live order

These must require explicit approval and stronger policies.

### 9.2 Tool registry design

Tool registry responsibilities:
- register tool metadata
- validate inputs/outputs
- enforce permission policies
- attach correlation and audit metadata
- expose tools to planner and specialists

---

## 10. Memory model

The first release should keep memory simple.

### 10.1 Short-lived run memory
Stores:
- tool outputs from the current workflow
- intermediate notes
- evidence refs
- verifier findings

### 10.2 Persistent agent memory
Stores:
- workflow templates
- prompt versions
- policy versions
- reusable preferences
- agent run history and audit records

Do not store hidden freeform mutable “trading beliefs” as the source of truth.
Saved HaruQuant artifacts remain the source of truth.

---

## 11. Audit and observability

Each agent run should persist at least:
- agent_run_id
- task_id
- workflow_name
- planner choice
- tools called
- input refs
- output refs
- approval events
- status
- duration
- correlation_id
- user_id / role

Agent logs should align with existing HaruQuant logging schema where possible.

---

## 12. n8n integration design

n8n should be used as a workflow and integration bus.

### Good uses
- schedule daily brief generation
- send notifications to Slack / Telegram / email / Notion
- trigger agent workflows from HaruQuant events
- continue multi-step approval workflows
- trigger incident tickets and follow-up actions

### Bad uses
- low-latency trade decision loop
- direct bar-by-bar execution brain
- bypassing HaruQuant governance

### Integration patterns

1. **Inbound webhook to HaruQuant**
   - n8n triggers HaruQuant agent workflow API

2. **Outbound webhook from HaruQuant**
   - HaruQuant agent workflow sends event payload to n8n

3. **Async notification path**
   - HaruQuant stores result and emits compact notification payload

---

## 13. Safety model

### 13.1 Hard rules

Agents must never:
- bypass governance engine
- bypass kill-switch
- bypass reconciliation block
- mutate privileged config without approval
- place live orders from unconstrained natural language

### 13.2 Human approval model

Approval required for:
- strategy promotion
- live deployment
- privileged risk override
- stopping live sessions
- execution-affecting config changes
- live order submission

---

## 14. Deployment model

### 14.1 First-release deployment

- Python-only orchestration layer
- calls existing HaruQuant Python APIs and routes
- optional n8n integration through webhooks
- no dependency on distributed agent runtime in first release

### 14.2 Future extension

- Redis-backed task queue if needed
- async worker pool for long-running research workflows
- richer agent audit storage
- multiple model backends

---

## 15. Recommended first implementation

### Phase 1
- tool registry
- planner
- verifier
- audit trail
- Research Orchestrator Agent
- Risk Supervisor Agent
- Strategy QA Agent
- Incident Investigator Agent
- n8n integration client

### Phase 2
- Edge Intelligence Agent
- Execution Oversight Agent
- Portfolio Allocation Agent
- Live Operations Agent
- approval workflows

### Phase 3
- richer automation, prioritization, and escalation policies
- second LLM/provider support
- optional queue-based execution scaling

---

## 16. Success criteria

The design is successful when:
- the AI layer can operate entirely through typed tools
- deterministic HaruQuant engines remain authoritative
- specialist agents produce useful, auditable desk-style outputs
- n8n can orchestrate scheduled and alert-driven workflows
- privileged actions remain policy-bound and approval-gated
