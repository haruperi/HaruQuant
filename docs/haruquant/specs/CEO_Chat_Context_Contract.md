# CEO Chat Context Contract

Current page context is sent with each chat turn and converted into `services.schemas.chat.PageContext`.

Required boundary:

- Durable memory: thread title, messages, summaries, pinned facts.
- Ephemeral context: route, page title, session, symbol, timeframe, DOM snapshot, page intelligence.

The CEO may use page context to answer the current turn, but it must not treat that context as a durable fact unless the operator explicitly saves or pins it.

Trust ranking:

1. Current system state and page context.
2. Durable HaruQuant records and reports.
3. Conversation summaries.
4. Older chat messages.

