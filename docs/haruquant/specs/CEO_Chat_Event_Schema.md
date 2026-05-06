# CEO Chat Event Schema

The streaming endpoint emits server-sent events:

- `meta`: request id, planner route, CEO memo metadata, telemetry, audit flags, page context.
- `token`: deterministic text delta for the assistant response.
- `done`: persisted assistant message id, thread detail, and final metadata.
- `error`: recoverable stream failure.

Current endpoint:

```text
POST /api/ai-chat/threads/{thread_id}/responses/stream
```

Regeneration uses the latest durable user message and never repeats side effects.

