# AI Agentic Orchestration Layer — Workflow Catalog

## 1. Purpose

This document defines the recommended first workflow set for HaruQuant’s AI Agentic Orchestration Layer.

Each workflow is designed to complement existing HaruQuant functionality and to keep deterministic engines as the system of truth.

---

## 2. Workflow design pattern

Recommended standard pattern:

1. Trigger
2. Planner
3. Specialist agent(s)
4. Verifier
5. Reporter
6. Notification / storage / approval follow-up

This pattern keeps workflows modular and auditable.

---

## 3. Workflow 01 — Daily Market Research Brief

### Purpose
Build a desk-style daily summary of what the market currently favors.

### Trigger options
- scheduled time via n8n
- manual request from UI/chat
- post-refresh completion of Edge Lab automation batch

### Inputs
- symbol universe
- timeframe set
- latest Edge snapshots
- optional snapshot comparison baseline

### Flow
1. Planner recognizes a research-brief task.
2. Research Orchestrator checks whether fresh snapshots already exist.
3. If needed, it triggers:
   - dataset prepare
   - core metric
   - seasonality
   - market structure
   - scorecard
4. Edge Intelligence Agent interprets outputs.
5. Verifier checks artifact freshness and completeness.
6. Reporter generates:
   - top opportunities
   - avoid list
   - strategy-fit summary
   - major caveats
7. n8n sends briefing to desired channel.

### Outputs
- daily market brief
- ranked pairs
- notable changes vs prior snapshot
- recommended next research actions

### Reason
This creates an institutional-style morning research workflow without changing strategy execution logic.

---

## 4. Workflow 02 — Snapshot Drift Watch

### Purpose
Detect meaningful changes in pair profile state between snapshots.

### Trigger options
- new snapshot saved
- scheduled comparison job

### Inputs
- current snapshot
- prior snapshot(s)

### Flow
1. Planner routes to Edge Intelligence Agent.
2. Agent compares snapshots.
3. Verifier checks whether changes exceed configured thresholds.
4. Reporter summarizes:
   - score deltas
   - strategy-fit changes
   - tradeability deterioration/improvement
5. n8n sends alert only if material drift exists.

### Outputs
- drift alert
- change summary
- recommendation to refresh research or hold current assumptions

### Reason
This prevents the user from relying on stale profile assumptions.

---

## 5. Workflow 03 — Strategy Promotion Review

### Purpose
Produce a formal AI-assisted validation memo before a strategy is considered for live deployment.

### Trigger options
- optimization complete
- manual review request
- milestone in research pipeline

### Inputs
- backtest id(s)
- optimization run id
- WFO/WFM refs
- Monte Carlo refs
- sensitivity refs
- reproducibility manifest refs

### Flow
1. Planner identifies promotion-review intent.
2. Strategy QA Agent gathers validation artifacts.
3. QA Agent evaluates them against promotion checklist and policy thresholds.
4. Risk Supervisor may optionally review deployment risk fit.
5. Verifier checks that no mandatory validation stage is missing.
6. Reporter builds a structured review memo.
7. Optional approval workflow is created for human sign-off.

### Outputs
- promote / hold / reject
- reasons
- missing validations
- next validation actions
- policy exception notes

### Reason
This reduces weak or overfit strategy promotion decisions.

---

## 6. Workflow 04 — Live Risk Watch

### Purpose
Continuously summarize and escalate portfolio/session risk state.

### Trigger options
- scheduled polling
- new risk snapshot event
- governance state change
- scenario deterioration threshold

### Inputs
- current portfolio state
- risk snapshot
- risk scorecard
- governance report
- regime state
- recommendations

### Flow
1. Planner identifies risk-watch intent.
2. Risk Supervisor Agent loads current state and latest risk artifacts.
3. If thresholds are crossed, agent also runs what-if scenarios.
4. Verifier checks that evidence is current.
5. Reporter outputs a current-state risk memo.
6. n8n routes alerts when necessary.

### Outputs
- safe / caution / stressed / escalate status
- top risk drivers
- suggested hedges or reductions
- governance breach explanation

### Reason
This creates a desk-style risk monitoring loop using your existing risk engine.

---

## 7. Workflow 05 — Trade Review Assistant

### Purpose
Support manual intervention and discretionary simulator/live review with structured context.

### Trigger options
- user requests manual review
- pre-trade preview requested

### Inputs
- candidate trade
- current session state
- governance preview
- what-if result
- risk snapshot

### Flow
1. Planner routes to Risk Supervisor Agent.
2. Agent gathers governance, risk, and what-if context.
3. Optional Edge Intelligence Agent adds pair-condition context.
4. Verifier checks whether evidence is sufficient.
5. Reporter returns a structured advisory note.

### Outputs
- advisory accept / caution / avoid summary
- portfolio impact summary
- top warnings
- better alternative suggestions if any

### Reason
This improves manual decision support without handing control to AI.

---

## 8. Workflow 06 — Incident Review

### Purpose
Reconstruct and explain a failure, anomaly, or unexpected event.

### Trigger options
- explicit user request
- live error / breach / disconnect event
- repeated execution or governance anomalies

### Inputs
- session id
- replay refs
- log refs
- risk snapshot refs
- governance event refs
- execution quality refs

### Flow
1. Planner identifies incident-review intent.
2. Incident Investigator Agent gathers timeline artifacts.
3. Risk Supervisor and Execution Oversight may be called as sub-specialists.
4. Agent reconstructs expected vs actual path.
5. Verifier checks evidence completeness.
6. Reporter generates incident packet.
7. n8n may open ticket / send report.

### Outputs
- root cause analysis
- event timeline
- impacted controls
- recommended preventive actions

### Reason
This reduces time-to-understanding after problems occur.

---

## 9. Workflow 07 — Execution Quality Watch

### Purpose
Detect degraded execution conditions that make live operation less trustworthy.

### Trigger options
- scheduled monitoring
- slippage threshold breach
- latency anomaly
- repeated partial fills or rejections

### Inputs
- execution quality summaries
- reconciliation state
- broker session state
- live logs

### Flow
1. Planner routes to Execution Oversight Agent.
2. Agent gathers quality metrics and anomalies.
3. Verifier checks severity and persistence.
4. Reporter outputs:
   - normal
   - caution
   - unsuitable execution environment
5. n8n routes alerts when needed.

### Outputs
- execution quality memo
- caution state
- deployment suitability note

### Reason
A system can be strategically sound but operationally weak. This workflow covers that gap.

---

## 10. Workflow 08 — Portfolio Allocation Review

### Purpose
Recommend where capital should go across strategies/symbols.

### Trigger options
- periodic portfolio review
- after strategy promotion review
- after edge snapshot refresh

### Inputs
- edge snapshots
- strategy QA output
- current risk state
- recommendation engine output
- regime state

### Flow
1. Planner routes to Portfolio Allocation Agent.
2. Agent gathers ranked strategy candidates and current risk constraints.
3. Agent proposes bounded allocation suggestions.
4. Risk Supervisor verifies feasibility and concentration concerns.
5. Reporter builds allocation review memo.

### Outputs
- ranked allocation candidates
- increase / hold / reduce suggestions
- concentration warnings

### Reason
This uses AI where it is strongest: coordination and ranking, not raw price prediction.

---

## 11. Workflow 09 — Daily Desk Pack

### Purpose
Produce a consolidated end-to-end daily desk report.

### Trigger options
- scheduled via n8n

### Inputs
- latest Edge brief
- latest risk memo
- latest live ops summary
- latest validation updates
- major incidents if any

### Flow
1. n8n triggers daily pack workflow.
2. Planner triggers sub-workflows or loads latest artifacts.
3. Reporter combines outputs into one consolidated memo.
4. n8n routes memo to chosen channels.

### Outputs
- daily desk pack
- summary sections by domain
- high-priority action list

### Reason
This gives HaruQuant a true desk-operations feel.

---

## 12. Workflow 10 — Approval-Gated Action Flow

### Purpose
Handle privileged actions safely.

### Trigger options
- strategy promotion request
- live stop request
- risk override request
- deployment request

### Inputs
- requested action
- operator id
- evidence refs
- policy context

### Flow
1. Agent workflow gathers and summarizes evidence.
2. Approval request is created.
3. Human approves or rejects.
4. Only then may privileged action tool be called.
5. Audit records approval path and outcome.

### Outputs
- approved / rejected / expired
- audit refs

### Reason
Prevents AI from becoming an uncontrolled mutation layer.

---

## 13. n8n workflow mapping

### Recommended first n8n workflows

1. **Daily Edge Brief**
   - scheduled trigger
   - call HaruQuant research workflow
   - send Slack/Telegram/email message

2. **Risk Alert**
   - triggered by governance or risk threshold
   - call HaruQuant risk workflow
   - send structured alert

3. **Strategy Review Request**
   - triggered by optimization completion
   - call Strategy QA workflow
   - send review packet

4. **Incident Escalation**
   - triggered by incident event
   - call incident-review workflow
   - route report to incident channel or ticketing system

5. **Daily Desk Pack**
   - scheduled aggregation workflow
   - collect latest reports
   - send daily summary

---

## 14. Workflow priority

### First release
- Daily Market Research Brief
- Strategy Promotion Review
- Live Risk Watch
- Incident Review

### Second release
- Snapshot Drift Watch
- Execution Quality Watch
- Portfolio Allocation Review
- Daily Desk Pack

### Later release
- richer approval-gated operational workflows
- more advanced orchestration chains

---

## 15. Success criteria

Workflow layer is successful when:
- workflows are understandable and repeatable
- each workflow has a clear purpose
- outputs are evidence-based
- the user receives better desk-style summaries and alerts
- no workflow bypasses deterministic HaruQuant controls
