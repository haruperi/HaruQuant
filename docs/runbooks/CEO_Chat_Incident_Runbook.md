# CEO Chat Incident Runbook

Immediate checks:

- Confirm `/api/ai-chat/tools` returns only read-only tools.
- Confirm assistant metadata has `live_execution_enabled=false`.
- Confirm affected thread messages are present in `ai_chat_messages`.
- Confirm any action draft remains non-executed unless it was explicitly approved.

Containment:

- Hide the chat launcher in the UI shell.
- Disable the chat API route at the application gateway.
- Preserve `ai_chat_*` tables for audit review.

Recovery:

- Re-enable deterministic mode first.
- Re-run focused CEO chat service tests.
- Review any prompt, tool registry, or route catalog changes before rollout.

