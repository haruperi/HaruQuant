# CEO Chat Architecture

The HaruQuant global chat widget is the UI transport for `CEOAgent`.

Flow:

```text
UI chat widget
  -> /api/ai-chat/* via api/routes/ai_chat.py
  -> ConversationService
  -> PageContextService
  -> CEOChatGateway
  -> PlannerAgent
  -> CEOAgent
  -> permissioned read-only tools / governed drafts
```

Rules:

- Chat memory is durable and stored in the `ai_chat_*` tables.
- Page context is ephemeral and is only linked by `context_revision`.
- Every chat turn starts at the CEO gateway.
- The planner route catalog bounds delegation.
- Chat cannot execute live trades.
- Paper execution requires an approved draft and remains separate from free-form chat.
- LLM provider wiring is deferred; current responses are deterministic.
