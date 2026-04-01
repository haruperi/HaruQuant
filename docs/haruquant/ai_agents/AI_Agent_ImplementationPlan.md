# AI Agentic Orchestration Layer — Implementation Plan

## 1. Goal

Implement a bounded AI/agent layer that complements HaruQuant’s deterministic engines and improves research, risk awareness, validation rigor, and operations.

This implementation plan is intentionally staged so the first release delivers value without introducing unsafe autonomy.

---

## 2. Delivery strategy

### Guiding approach

Build in this order:

1. **tooling and boundaries first**
2. **read-only and advisory agents next**
3. **workflow automation next**
4. **approval-gated privileged flows later**

This keeps robustness ahead of ambition.

---

## 3. Phase breakdown

## Phase 0 — Foundation alignment

### Objectives
- define the agent architecture boundary
- define tool registry contracts
- define audit and policy rules
- define model/provider integration abstraction

### Deliverables
- `apps/agents/` package skeleton
- `agent_models.py`
- `tool_registry.py`
- `policies.py`
- `audit.py`
- `llm_client.py`
- baseline config file for agent policies and model settings

### Tasks
- create module structure
- define shared task/result/tool contracts
- define permission tiers
- define audit log schema
- define provider abstraction for one initial LLM backend

### Exit criteria
- project compiles/tests with empty skeleton
- contract models are in place
- one no-op workflow can run end-to-end

---

## Phase 1 — Tool registry and read-only tools

### Objectives
- wrap existing HaruQuant capabilities in agent-safe tools

### Deliverables
- Edge tools
- Risk tools
- Backtest/validation tools
- Replay/report tools

### Tasks
- implement `edge_tools.py`
- implement `risk_tools.py`
- implement `backtest_tools.py`
- implement `report_tools.py`
- register tools in registry
- add per-tool permission mode and schemas
- add audit logging around tool execution

### Recommended first tool set
- edge_list_snapshots
- edge_get_snapshot
- edge_compare_snapshots
- risk_get_current_state
- risk_get_snapshot
- risk_get_scenarios
- backtest_get_run
- validation_get_manifest
- replay_get_frames
- report_generate_markdown

### Exit criteria
- agents can gather evidence through tools only
- no direct repository or DB assumptions are required inside agent logic

---

## Phase 2 — Planner, verifier, and first agents

### Objectives
- enable useful desk-style workflows

### Deliverables
- planner
- verifier
- Research Orchestrator Agent
- Risk Supervisor Agent
- Strategy QA Agent
- Incident Investigator Agent

### Tasks
- implement `planner.py`
- implement `verifier.py`
- implement specialist agents
- define prompt templates and output schemas
- define evidence completeness rules per workflow

### Recommended initial workflows
- daily market research brief
- strategy promotion review
- live risk watch
- incident review

### Exit criteria
- each workflow can run from task -> tools -> verified result
- outputs are structured and evidence-bound

---

## Phase 3 — Advisory-write tools

### Objectives
- add safe actions that do not mutate live execution dangerously

### Deliverables
- edge refresh / automation tools
- risk what-if tools
- report export tools
- workflow-notification tools

### Tasks
- implement `risk_run_what_if`
- implement Edge automation wrappers
- implement report export wrappers
- implement n8n outbound webhook tool

### Exit criteria
- agents can trigger safe analysis and reporting actions
- no live privileged mutations are required for first user value

---

## Phase 4 — n8n integration

### Objectives
- connect HaruQuant agents to scheduling and notification workflows

### Deliverables
- `n8n_client.py`
- inbound/outbound webhook patterns
- workflow payload schemas
- example n8n workflow definitions

### Tasks
- define webhook auth and signature policy
- define notification payload schema
- create example workflows for:
  - daily Edge brief
  - risk alert
  - strategy review packet
  - incident escalation
  - daily desk pack

### Exit criteria
- at least two production-useful workflows can be triggered through n8n

---

## Phase 5 — Edge Intelligence and Execution Oversight

### Objectives
- deepen agent specialization beyond basic orchestration

### Deliverables
- Edge Intelligence Agent
- Execution Oversight Agent
- Portfolio Allocation Agent

### Tasks
- add snapshot drift and fit-change logic
- add execution quality review workflow
- add allocation review memo workflow

### Exit criteria
- HaruQuant can produce research, risk, execution, and allocation desk memos

---

## Phase 6 — Approval-gated privileged flows

### Objectives
- safely introduce privileged actions behind approval workflow

### Deliverables
- approval request models
- approval routing
- approval status tracking
- privileged action wrappers

### Tasks
- implement `approval_request_action`
- implement `approval_get_status`
- implement `approval_apply_decision`
- add strong policy checks for:
  - strategy promotion
  - live deployment
  - live stop/pause
  - risk override

### Exit criteria
- privileged actions cannot be executed without approval artifact
- audit chain is complete

---

## 4. File and module plan

Recommended initial module tree:

```text
apps/agents/
  __init__.py
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

## 5. Policy model plan

### 5.1 Permission tiers

Implement a policy enum or equivalent model:
- `READ_ONLY`
- `ADVISORY_WRITE`
- `PRIVILEGED`

### 5.2 Action categories

- research
- risk
- reporting
- workflow
- live_ops
- deployment

### 5.3 Approval-required actions

At minimum:
- strategy promotion
- live deployment
- live stop or kill action
- risk override
- any future live order mutation through agent workflow

---

## 6. Prompt and output plan

### Prompt strategy
- keep prompts small and domain-specific
- make each specialist prompt aware of only its allowed scope
- do not create one giant universal prompt

### Output strategy
Every specialist should emit a structured result with:
- status
- summary
- evidence
- recommendations
- required actions
- confidence

This makes downstream automation easier.

---

## 7. Storage and audit plan

### First implementation
Use lightweight structured audit storage with at least:
- agent_run_id
- workflow_name
- task_type
- user_id
- tool_calls
- evidence_refs
- result_summary
- status
- timestamps

Possible first storage target:
- SQLite table(s) under existing infrastructure

Suggested future tables:
- `agent_runs`
- `agent_tool_calls`
- `agent_approvals`
- `agent_artifacts`

---

## 8. Testing plan

## 8.1 Unit tests

Test:
- tool schema validation
- planner routing logic
- verifier completeness rules
- specialist output schema
- policy enforcement

## 8.2 Integration tests

Test:
- full workflow execution over synthetic fixtures
- n8n webhook invocation path
- risk what-if workflow
- strategy QA evidence assembly
- incident review evidence assembly

## 8.3 Acceptance tests

Acceptance workflows:
- daily market brief returns ranked symbols with evidence refs
- strategy promotion review returns promote/hold/reject with reasons
- live risk watch returns risk memo and alerts under stressed scenario
- incident review reconstructs timeline and root cause using replay/log refs

---

## 9. Rollout plan

### Milestone 1
- module skeleton
- tool registry
- read-only tools
- audit scaffolding

### Milestone 2
- planner + verifier
- Research Orchestrator
- Risk Supervisor

### Milestone 3
- Strategy QA Agent
- Incident Investigator
- first Markdown report templates

### Milestone 4
- n8n integration
- daily Edge brief
- risk alert workflow

### Milestone 5
- Edge Intelligence Agent
- Execution Oversight Agent
- Portfolio Allocation Agent

### Milestone 6
- approval-gated privileged flows

---

## 10. Recommended order of build

If only one path is followed, use this order:

1. tool registry
2. read-only edge/risk/backtest tools
3. planner + verifier
4. Research Orchestrator
5. Risk Supervisor
6. Strategy QA Agent
7. Incident Investigator
8. n8n workflows
9. Edge Intelligence
10. Execution Oversight and Allocation
11. approvals and privileged flows

---

## 11. Risks and mitigations

### Risk 1 — Over-automation too early
Mitigation:
- start read-only and advisory only

### Risk 2 — AI recommendations with weak evidence
Mitigation:
- verifier layer + mandatory evidence refs

### Risk 3 — Agent bypass of safety boundaries
Mitigation:
- policy enforcement + explicit permission tiers + approval workflow

### Risk 4 — Tool sprawl and inconsistency
Mitigation:
- central registry and shared schemas

### Risk 5 — n8n becomes the logic brain
Mitigation:
- keep business logic in HaruQuant tools and workflows; use n8n for orchestration and routing only

---

## 12. First-release success definition

The first release is successful when HaruQuant can:

1. generate a daily market research brief from existing Edge artifacts
2. produce a strategy promotion review from existing validation artifacts
3. produce a live/current risk memo from existing risk artifacts
4. produce an incident review using replay/log/snapshot evidence
5. route at least one daily scheduled workflow and one alert workflow through n8n
6. keep all privileged actions outside the first release or behind approval gates
