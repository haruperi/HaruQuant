# HaruQuant AI Chatbot User Training & Support SOP

Status: Active
Scope: User Guide, Support Procedures, and Ownership for the AI Chatbot
Owner: Product Owner & AI Platform Lead

## 1. User Training Guide

### Overview
The HaruQuant AI Chatbot is a persistent, context-aware copilot designed to assist with quantitative research, portfolio monitoring, and strategy validation.

### Key Capabilities
- **Context-Aware Responses:** The Chatbot reads the current page (e.g., Dashboard, Strategy Detail, Backtest) to provide relevant insights without needing explicit copy-pasting.
- **Read-Only Data Grounding:** Answers are backed by real HaruQuant data rather than generic LLM knowledge.
- **Persistent Memory:** Conversations persist across page navigation. A thread can be resumed at any time.
- **Signal Proposals:** The assistant can draft structured trading signals. *These are non-executable and must be reviewed.*
- **Action Drafts:** The assistant can propose system actions (e.g., launching a backtest). *These require explicit operator approval.*

### Limitations
- **No Direct Execution:** The AI Chatbot CANNOT execute live trades directly. All actions are drafts requiring human review.
- **Knowledge Boundaries:** The assistant is trained on internal documentation and current system state. It may occasionally lack real-time external market news unless provided via a specific tool.

### Best Practices
- **Be Specific:** Ask targeted questions (e.g., "Why did Strategy 42 underperform yesterday?" rather than "What's wrong?").
- **Verify Evidence:** Review the "Grounded tools used" section in the chatbot's response to ensure its conclusions are based on accurate data.
- **Report Issues:** Escalate inaccurate or unsafe responses through the standard HaruQuant support and issue-tracking path.

## 2. Support Standard Operating Procedure (SOP)

### Triage & Initial Response
When a user reports an issue with the AI Chatbot:
1. **Identify the Scope:** Is it a UI bug, a hallucination, a data leak, or a system outage?
2. **Check Telemetry:** Review the Latency, Cost, and Error dashboards in the DevOps console. Look for API timeouts or rate-limit spikes.
3. **Review Audit Logs:** If the issue involves an Action Draft or Signal Proposal, locate the `request_id` in the `ConversationMessageRecord` database.

### Resolution Paths
- **UI/UX Issues:** Route to the Frontend Team. (e.g., "Widget not expanding", "History not loading").
- **Hallucinations/Inaccurate Data:** Route to the AI Platform Lead and Quant/Risk Lead. (e.g., "Assistant claims my portfolio is down 50% but it's up 2%"). *Action: Tune prompts or correct tool payloads.*
- **Action/Execution Errors:** Route to the Backend Lead and Security Owner. (e.g., "Draft action created without proper RBAC validation"). *Action: Immediate Sev-1 response, potentially triggering the kill switch.*

### Escalation Matrix
- **Sev-1 (Safety/Security):** Escalate immediately to Security Owner and On-Call SRE. Trigger Kill Switch.
- **Sev-2 (Outage/Degradation):** Escalate to On-Call SRE and Backend Lead.
- **Sev-3 (Quality/UX):** Log a ticket for the next sprint review with the Product Owner.

## 3. Ownership & Ongoing Tuning

### Prompt & Tool Tuning
- **Primary Owner:** AI Platform Lead
- **Responsibility:** Review post-launch metrics and user feedback to refine the `ChatPromptBuilder` and domain-specific prompts. Adjust `ContextCompactor` bounds if payloads are consistently truncated too aggressively.
- **Cadence:** Bi-weekly review during the rollout phases, transitioning to monthly steady-state reviews.

### Domain Intelligence Updates
- **Primary Owner:** Quant/Risk Lead
- **Responsibility:** Ensure the assistant's quantitative logic, risk explanations, and signal generation rules remain aligned with HaruQuant's evolving models.
- **Cadence:** Ad-hoc, tied to major risk engine or strategy catalog updates.

### Infrastructure & Cost Management
- **Primary Owner:** DevOps/SRE
- **Responsibility:** Monitor token usage, API costs, and latency targets. Adjust `ChatRateLimiter` settings as user adoption scales.
- **Cadence:** Continuous monitoring with weekly reporting to the Product Owner.
