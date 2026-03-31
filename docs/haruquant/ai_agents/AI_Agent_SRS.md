# AI Agentic Orchestration Layer — Software Requirements Specification (SRS)

## 1. Purpose

This document defines the requirements for the HaruQuant AI Agentic Orchestration Layer.

The goal is **not** to replace the existing deterministic trading, edge, risk, simulator, replay, backtest, optimization, and reporting engines. The goal is to add an AI/agent layer that can:

- orchestrate multi-step workflows across existing HaruQuant subsystems
- interpret outputs from existing engines in a desk-style manner
- monitor system state and surface risks, anomalies, and next actions
- automate repetitive research and operational tasks
- remain bounded by existing risk, governance, and execution controls

This layer should make HaruQuant behave more like a **desk of specialist analysts** than a single static formula.

---

## 2. Scope

In scope:

- agent orchestration over existing HaruQuant APIs and engines
- read-only and advisory agents for research, risk, validation, and operations
- bounded write-capable workflows for safe non-live operations
- integration with workflow systems such as n8n for scheduling, routing, and notifications
- structured outputs, auditability, and human approval boundaries

Out of scope for the first implementation:

- unconstrained autonomous live trading
- direct AI bypass of governance or kill-switch controls
- replacing core risk, simulator, or backtest math with LLM reasoning
- pure “next candle” prediction as the primary AI layer

---

## 3. Architectural Position

The AI layer sits **above** the current HaruQuant deterministic stack.

### Existing deterministic stack remains authoritative

- Edge Lab computes pair profiles, seasonality, market structure, scorecards, snapshots, and reports.
- Risk computes canonical state, snapshots, governance, scorecards, scenarios, recommendations, replay, and storage.
- Trading/Simulation/Backtest own execution truth, order state, replay, and persistence.

### New agentic layer owns

- intent interpretation
- workflow planning
- specialist-agent coordination
- evidence collection from tools
- summary generation
- next-step recommendation
- escalation and notification routing

---

## 4. Objectives

### 4.1 Primary objectives

1. Increase research throughput without weakening rigor.
2. Improve portfolio and operational awareness.
3. Reduce time spent manually connecting outputs across modules.
4. Improve consistency of strategy review and promotion decisions.
5. Improve explainability of current state, incidents, and recommended actions.

### 4.2 Secondary objectives

1. Standardize AI-readable and operator-readable outputs.
2. Enable workflow automation through n8n.
3. Keep strong human control for dangerous actions.
4. Prepare a future path toward more advanced agent collaboration without major rewrites.

---

## 5. Design principles

1. **Deterministic core, agentic orchestration**
   - AI does not replace edge, risk, or execution engines.
   - AI orchestrates and interprets those engines.

2. **Tool-first, not freeform-first**
   - Agents should use structured internal tools and strict schemas.
   - Reasoning should end in bounded tool calls or structured reports.

3. **Advisory before autonomous**
   - Start with read-only and advisory behaviors.
   - Add write capability only for safe, non-live workflows first.

4. **Evidence-based outputs**
   - Every recommendation should include evidence, confidence, and reasoning summary.

5. **Policy-bounded execution**
   - Agents must never bypass existing governance, risk, kill-switch, reconciliation, or execution safeguards.

6. **Human approval for privileged actions**
   - Strategy promotion, live deployment, risk override, and live trade actions require explicit approval.

---

## 6. Agent classes

### 6.1 Research Orchestrator Agent

Purpose:
- Coordinate multi-step research workflows across Edge Lab, backtests, robustness, and reporting.

Responsibilities:
- determine which research workflow to run
- trigger required prerequisite stages
- collect outputs and build a coherent research brief
- recommend next experiments

### 6.2 Edge Intelligence Agent

Purpose:
- Interpret pair profile outputs and convert them into tradeability and strategy-fit narratives.

Responsibilities:
- read snapshots, scorecards, market structure, seasonality
- detect shifts vs prior saved snapshots
- summarize edge condition and strategy suitability

### 6.3 Strategy QA Agent

Purpose:
- Review strategies before promotion or live consideration.

Responsibilities:
- inspect backtests, optimization outputs, WFO/WFM, Monte Carlo, sensitivity, manifests
- enforce validation checklist and policy thresholds
- produce promote / hold / reject advisory output

### 6.4 Risk Supervisor Agent

Purpose:
- Monitor current portfolio and simulation/live risk conditions continuously.

Responsibilities:
- summarize current risk state
- detect concentration drift, governance deterioration, stress regimes, scenario weakness
- recommend safe reductions, hedges, or caution states

### 6.5 Execution Oversight Agent

Purpose:
- Monitor broker, slippage, fills, spread quality, and operational execution anomalies.

Responsibilities:
- detect degraded execution quality
- flag environments unsuitable for deployment or continuation

### 6.6 Incident Investigator Agent

Purpose:
- Reconstruct and explain incidents using replay, logs, governance, and risk bundles.

Responsibilities:
- produce root-cause analysis
- explain expected vs actual behavior
- propose preventive actions

### 6.7 Portfolio Allocation Agent

Purpose:
- Recommend allocation, de-allocation, and deployment prioritization.

Responsibilities:
- consume edge intelligence, strategy QA, and risk data
- suggest capital placement and sequencing

### 6.8 Live Operations Agent

Purpose:
- Coordinate operational workflows, alerts, and summaries.

Responsibilities:
- route alerts and reports
- summarize session health
- escalate incidents and policy concerns

---

## 7. User roles

### 7.1 Portfolio Manager / Owner
Needs:
- summarized decision-ready outputs
- approval controls
- exception alerts
- what-if support

### 7.2 Research Analyst
Needs:
- automated experiment chaining
- snapshot comparison
- strategy fit and degradation analysis

### 7.3 Risk Manager
Needs:
- current portfolio risk narrative
- breach context
- what-if and scenario support

### 7.4 Operations / Trade Support
Needs:
- incident summaries
- session health alerts
- execution anomaly warnings

---

## 8. Functional requirements

### FR-AI-001 Tool-based orchestration
The system shall expose HaruQuant internal capabilities as structured agent tools rather than requiring agents to infer raw database or file semantics.

### FR-AI-002 Specialist-agent routing
The system shall support routing a task to one or more specialist agents based on intent.

### FR-AI-003 Planner-verifier flow
The system shall support a workflow pattern where a planner selects steps and a verifier checks prerequisites, evidence completeness, and policy gates.

### FR-AI-004 Structured outputs
Every agent response shall produce a machine-readable structured output that includes at least:
- status
- summary
- evidence
- recommendations
- required actions
- confidence

### FR-AI-005 Evidence binding
Agent outputs shall reference the exact source artifacts used, such as snapshot ids, run ids, backtest ids, replay frame ids, or report refs.

### FR-AI-006 Snapshot-aware analysis
Agents shall be able to compare current and prior saved snapshots for Edge and Risk artifacts.

### FR-AI-007 What-if support
Risk-oriented agents shall be able to trigger non-mutating what-if workflows.

### FR-AI-008 Replay-assisted investigation
Incident-oriented agents shall be able to retrieve replay and stored risk artifacts to reconstruct a timeline.

### FR-AI-009 Policy-aware review
Strategy QA and promotion workflows shall check configured review policy thresholds and produce explicit pass/hold/reject recommendations.

### FR-AI-010 Notification routing
The system shall support routing alerts and summaries to external systems through n8n or equivalent workflow engines.

### FR-AI-011 Human approval boundary
Privileged actions shall require explicit operator approval and must not execute from freeform AI output alone.

### FR-AI-012 Permission tiers
The system shall support at least three permission tiers:
- read-only
- advisory / safe write
- privileged

### FR-AI-013 Audit trail
Every agent workflow run shall be auditable with inputs, tools used, outputs, approval events, and timestamps.

### FR-AI-014 Workflow templates
The system shall provide reusable workflow templates for:
- daily market research brief
- strategy promotion review
- live risk watch
- manual trade review assistant
- incident review

### FR-AI-015 n8n integration
The system shall support webhook- or API-based integration with n8n for orchestration, scheduling, and notifications.

---

## 9. Non-functional requirements

### NFR-AI-001 Explainability
Agent outputs must be understandable by a human operator and avoid opaque “trust me” recommendations.

### NFR-AI-002 Bounded autonomy
Agent behavior must stay within explicit tool and policy boundaries.

### NFR-AI-003 Reliability
Failure of an agent workflow must not compromise deterministic HaruQuant engines.

### NFR-AI-004 Observability
Agent runs must emit logs, correlation ids, and run metadata.

### NFR-AI-005 Composability
New agents and tools should be addable without changing all existing workflows.

### NFR-AI-006 Security
Secrets, credentials, and privileged mutation paths must remain under existing HaruQuant security controls.

### NFR-AI-007 Versioning
Prompt templates, policy specs, tool schemas, and workflow versions must be versioned.

### NFR-AI-008 Performance isolation
Agent workflows must run outside hot trading execution paths unless explicitly designed for low-latency advisory views.

---

## 10. Constraints

1. The AI layer must not bypass governance.
2. The AI layer must not bypass kill-switch or reconciliation blocks.
3. The AI layer must not place unrestricted live trades.
4. n8n is orchestration support, not the execution brain.
5. Hard portfolio and execution truth remain in deterministic engines.

---

## 11. Acceptance criteria

The first release is acceptable when:

1. A Research Orchestrator can run a structured research workflow over existing Edge tools.
2. A Risk Supervisor can build a current-state risk memo from existing risk snapshot and what-if tools.
3. A Strategy QA Agent can review a completed strategy validation package and produce promote/hold/reject output.
4. An Incident Investigator can reconstruct a replay-backed incident summary.
5. All agent outputs are structured, auditable, and evidence-linked.
6. Privileged actions remain approval-gated.
7. n8n can trigger at least one daily report workflow and one alert workflow.

---

## 12. Initial release recommendation

Recommended first-release agents:

- Research Orchestrator Agent
- Edge Intelligence Agent
- Strategy QA Agent
- Risk Supervisor Agent
- Incident Investigator Agent

These provide the highest robustness gain without increasing live execution risk.