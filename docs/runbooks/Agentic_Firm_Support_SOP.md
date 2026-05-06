# Agentic Firm Support SOP

Support ownership:

- UI behavior: frontend owner.
- `/api/ai-chat/*` route behavior: backend owner.
- Planner and CEO routing: AI platform owner.
- Tool permissions and governance: agent tools and risk owners.
- Audit review: compliance owner.

Standard triage:

1. Identify the chat thread id and request id.
2. Export the conversation from the chat API.
3. Inspect planner metadata and CEO memo metadata.
4. Confirm no prohibited side effect occurred.
5. Escalate governance or execution concerns to the Human Board workflow.

