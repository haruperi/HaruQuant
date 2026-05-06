# AI Gateway and Streaming Orchestration

## Runtime Contract

AI Chat uses the existing Server-Sent Events endpoint:

- `POST /api/ai-chat/threads/{thread_id}/responses/stream`
- `POST /api/ai-chat/threads/{thread_id}/responses/regenerate`

Events are emitted in order:

- `meta`: routing, model, timing, prompt-composition audit, context revision.
- `token`: incremental assistant text delta.
- `done`: final persisted assistant message and refreshed thread.
- `error`: unrecoverable transport error.

The assistant message is persisted only after the stream finishes. If the client
cancels before completion, no partial assistant message is written.

## Gateway Configuration

The gateway uses the same model configuration as the rest of the agent system.
`config.agent_model` loads `config/environments/.env`, then resolves
`HARUQUANT_AGENT_MODEL`.

- `HARUQUANT_AI_GATEWAY_ENABLED`: set `false` to force safe fallback responses.
- `HARUQUANT_AGENT_MODEL`: default chatbot model.
- `GOOGLE_API_KEY`: used when the selected model is Gemini/Google.
- `OPENAI_API_KEY`: used when the selected model is OpenAI/GPT.
- `OLLAMA_BASE_URL`: optional local Ollama URL, defaults to `http://127.0.0.1:11434`.
- `HARUQUANT_AI_GATEWAY_MODEL`: optional chatbot-specific model override.
- `HARUQUANT_AI_MODEL_FAST`: optional page identity/plain-answer override.
- `HARUQUANT_AI_MODEL_ANALYSIS`: optional backtest/optimization override.
- `HARUQUANT_AI_MODEL_STRONG`: optional risk/strategy/tool-assisted override.
- `HARUQUANT_AI_GATEWAY_BASE_URL`: optional OpenAI-compatible base URL.

When model configuration is absent or streaming fails at startup, the gateway
falls back to a page-aware degraded response and marks metadata as
`generation_source=fallback`.

Supported model prefixes:

- `gemini-...` or `google/...`: Google Generative AI.
- `openai/...`, `gpt-...`, `o1...`, `o3...`, `o4...`: OpenAI-compatible chat completions.
- `ollama/...` or `ollama:<model>`: local Ollama `/api/chat` streaming.

## Prompt Layers

`services/prompt_builder.py` composes prompts in ordered layers:

- system governance and answer contract
- conversation memory summary
- pinned facts
- current page context
- attached tool disclosures
- recent messages
- current user prompt

The prompt-composition log is stored in
`metadata.audit.prompt_composition` and is visible in the AI Chat debug panel.

## Routing

`services/agent_router.py` classifies turns into:

- `page_identity`
- `tool_assisted_answer`
- `risk_review`
- `strategy_work`
- `analysis_workflow`
- `general_answer`

Regeneration uses the same read-only route policy and does not execute tool side
effects.
