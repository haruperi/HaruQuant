# Tool Call Schema

CEO chat exposes tool definitions using `services.schemas.chat.ChatToolDefinition`.

Current chat tool policy:

- Only enabled read-only tools are surfaced to the widget.
- Side-effect policy is `none`.
- Critical and write tools remain hidden from free-form chat.
- Tool definitions are sourced from `tools.registry.DEFAULT_TOOL_REGISTRY`.
- Actual tool execution must pass the canonical permission layer before later phases wire execution.

Live execution remains prohibited from chat.

