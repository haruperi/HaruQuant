# HaruQuant AI Chatbot Rollout Plan

Status: Pending
Scope: Phased release strategy for the HaruQuant AI Chatbot
Owner: Product Owner & AI Platform Lead

## Objective
Release the AI Chatbot safely through controlled rollout stages to manage risk, gather feedback, and ensure system stability before general availability.

Current operational note: rollout control is deployment-based. The chatbot does not yet have a dedicated feature-flag framework for selectively enabling or disabling capabilities per ring.

## Rollout Rings

### 1. Internal Dogfooding
**Audience:** HaruQuant Development and QA Teams
**Capabilities Enabled:** All currently implemented phases (up to Phase 12).
**Goals:**
- Validate core functionality in production-like environments.
- Verify UI stability and memory persistence.
- Test rate limiting, cost tracking, and logging under light concurrent load.
**Exit Criteria:**
- 0 Sev-1 or Sev-2 bugs reported.
- Latency metrics within target bounds (p95 < 2000ms for read-only queries).
- Telemetry properly populating dashboards.

### 2. Read-Only Beta
**Audience:** Selected subset of power users / internal analysts (opt-in).
**Capabilities Enabled:** Read-Only queries, Dashboard insights, Basic strategy/portfolio summaries.
**Restricted:** Signal Generation, Supervised Actions, Paper Automation.
**Goals:**
- Validate relevance and accuracy of responses grounded in HaruQuant data.
- Assess UX for conversation management (search, history).
- Fine-tune prompt structure and context assembly bounds.
**Exit Criteria:**
- Positive user feedback score (CSAT > 4/5).
- Accurate context injection verified (no cross-contamination).

### 3. Signal-Assistant Beta
**Audience:** Quants and Risk Managers.
**Capabilities Enabled:** Generation of non-executable Signal Proposals.
**Goals:**
- Evaluate domain intelligence for strategy, backtest, and risk.
- Validate formatting and risk-note inclusions in signal proposals.
- Ensure the model's confidence scores align with human intuition.
**Exit Criteria:**
- Proposals structurally sound 99% of the time.
- No hallucinations of non-existent data points leading to dangerous suggestions.

### 4. Supervised-Action Beta
**Audience:** Platform Operators and select Quants.
**Capabilities Enabled:** Creation of Action Drafts requiring human approval.
**Goals:**
- Validate Entitlement checks (RBAC integration).
- Ensure action payloads are correctly structured before approval.
- Confirm audit trail records all draft creation and approval events.
**Exit Criteria:**
- 100% of unauthorized action attempts blocked.
- 100% of approved actions successfully converted to commands.

### 5. Paper-Automation Pilot
**Audience:** Approved Quants and Operators.
**Capabilities Enabled:** Governed execution in paper-trading environments ONLY.
**Goals:**
- Validate trade action governor service.
- Confirm kill switches disable paper execution immediately.
**Exit Criteria:**
- All execution gating checks (limits, session status) function as designed.
- Zero bleed into live-trading environments.

## Go/No-Go Certification Checklist

| Category | Item | Status | Approver |
| :--- | :--- | :--- | :--- |
| **Security** | Prompt Injection controls validated | [ ] | Security Owner |
| **Security** | RBAC boundaries verified for Action Drafts | [ ] | Security Owner |
| **Data** | Context payload sanitization verified | [ ] | Backend Lead |
| **Ops** | Telemetry, Cost, and Latency dashboards active | [ ] | DevOps/SRE |
| **Ops** | Rate limiting and queueing functioning | [ ] | DevOps/SRE |
| **Product** | UX behaves gracefully under load | [ ] | Frontend Lead |
| **Risk** | Paper-execution Kill Switch tested | [ ] | Quant/Risk Lead|
| **Support** | Runbooks and SOPs published and reviewed | [ ] | Support Lead |

## Post-Launch Review Template

**Review Date:** YYYY-MM-DD
**Rollout Phase Reviewed:** [e.g., Read-Only Beta]

### Key Metrics
- **Active Users:** 
- **Total Sessions / Queries:**
- **Average Cost per Query:**
- **p50 / p95 Latency:**
- **Error Rate (Failures / Total):**
- **Rate Limit Hits:**

### Incidents & Anomalies
- Detail any Sev-1/Sev-2 incidents.
- Note any unexpected latency spikes or cost anomalies.

### User Feedback Summary
- Top requested features.
- Most common complaints or confusing UX patterns.

### Action Items
- List technical debt to address before next ring.
- Prompt/Tool tuning requirements.
