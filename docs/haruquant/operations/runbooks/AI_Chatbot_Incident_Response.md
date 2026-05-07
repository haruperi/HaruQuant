# HaruQuant AI Chatbot Incident Response & Rollback Runbook

Status: Active
Scope: Incident Response for AI Chatbot Infrastructure
Owner: DevOps/SRE & AI Platform Lead

## Introduction
This document details the incident response procedures and rollback mechanisms for the HaruQuant AI Chatbot service.

## Core Principles
- **Safety First:** If the AI Chatbot is malfunctioning, emitting hallucinations, or leaking data, disable it immediately using the kill switch.
- **Fail Gracefully:** A failure in the AI gateway must degrade gracefully; users should see a clean offline state, and core trading functions must remain unaffected.
- **Preserve Evidence:** Ensure all prompt inputs, tool outputs, and LLM responses are preserved in the audit log prior to rollback, where possible.

## Incident Severities

| Severity | Description | SLA | Example |
| :--- | :--- | :--- | :--- |
| **Sev-1** | Trading safety compromised, unauthorized actions created, or severe data leak. | 15 mins | AI creating direct orders bypassing risk controls; Context cross-contamination between users. |
| **Sev-2** | AI Gateway down, critical tool failure resulting in widespread degradation. | 1 hour | LLM provider API failure; Context assembler returning 500 errors. |
| **Sev-3** | Degraded performance, minor UI bugs, isolated tool timeouts. | Next BD | Occasional timeouts fetching portfolio risk snapshots. |

## Incident Playbooks

### 1. Model Provider Outage (Sev-2)
**Symptoms:** 
- AI gateway returning 502/504. 
- Increased streaming response latencies or connection resets.
- Telemetry dashboards show 100% error rate on `_generate_text`.

**Response Steps:**
1. Check external status pages (e.g., OpenAI, Google Cloud).
2. If the provider is experiencing an outage, keep the chat service in its current failure-safe mode: requests should return clean errors and core trading functions must remain unaffected.
3. Post an internal status update to the trading desk and operators: "AI Chatbot is currently unavailable due to upstream provider issues. Core trading platforms are unaffected."
4. Wait for upstream resolution. Resume service.

### 2. Context Cross-Contamination or Data Leak (Sev-1)
**Symptoms:** 
- User reports seeing another user's portfolio data or strategy details.
- Audit logs flag unauthorized entity access.

**Response Steps:**
1. **IMMEDIATE ACTION:** Trigger the global kill switch to disable the AI Gateway immediately.
2. Escalate to the Security / Compliance Owner.
3. Review `PageContextAssembler` logs to determine the injection flaw.
4. Review conversation threads matching the incident timeframe.
5. Identify the bug in the route-awareness or context-assembly layer.
6. Deploy a hotfix and test extensively before re-enabling the gateway.

### 3. Rogue Supervised Actions (Sev-1)
**Symptoms:** 
- Unexpected action drafts appearing in the operator queue.
- Risk engine flags repeated unauthorized or dangerous action attempts.

**Response Steps:**
1. **IMMEDIATE ACTION:** Trigger the global kill switch.
2. Review the `action_draft` and `signal_proposal` tables in the database.
3. Delete any unauthorized action drafts from the operator queue.
4. Review the system prompt and tool executor logic. Ensure RBAC and action gating are functioning correctly.
5. Deploy a fix, run full integration tests.

### 4. Cost Anomaly / Token Spikes (Sev-2/Sev-3)
**Symptoms:**
- Cost metrics spike unexpectedly.
- Token limits repeatedly hit, rate limiting legitimate users.

**Response Steps:**
1. Review the `ConversationMessageRecord` database for anomalies in `prompt_tokens` or `total_tokens`.
2. Check `ContextCompactor` settings to ensure payloads aren't exceeding expected lengths.
3. If necessary, adjust `ChatRateLimiter` settings in `api/routes/ai_chat.py` to clamp down on usage temporarily.

## Rollback Procedures

### Rollback via Feature Flag (Preferred)
The current implementation does not yet provide chatbot-specific feature flags. Use deployment rollback, route disablement, or widget exposure removal for controlled rollback.

### Full Service Rollback (Kill Switch)
There is no dedicated global AI chatbot kill switch yet.

If the entire chatbot service must be disabled:
1. Remove or disable the AI chat API route exposure in the current deployment.
2. Remove or disable the global chat widget exposure in the UI deployment.
3. Verify that chat requests fail cleanly while core non-chat workflows remain available.

Note: paper execution remains separately protected by the existing execution governance and kill-switch controls.

### Database Rollback
If the conversation service database is corrupted:
1. Isolate the affected partition.
2. Restore from the latest snapshot according to standard HaruQuant database recovery procedures. Ensure no side-effecting action drafts are inadvertently restored and executed.
