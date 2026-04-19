# HaruQuant AI Chatbot Event Schema

Status: canonical feature event schema
Scope: event model for chat requests, streaming, context revisions, tool usage, policy blocks, and supervised actions
Use this when: you need the persisted and observable event shapes for the chatbot lifecycle
Companion docs: `AI_Chatbot_Architecture.md`, `AI_Chatbot_Context_Contract.md`, `../governance/AI_Chatbot_Execution_Safety.md`, `../governance/AI_Chatbot_RBAC_Matrix.md`
Owner: backend lead and platform observability
Review cadence: on every event contract change

## Purpose

This document defines the minimum event shapes required to make the chatbot
auditable, debuggable, and replay-friendly.

## Event Design Principles

- all significant request stages emit structured events
- event shapes are append-only where possible
- request tracing and audit tracing must be joinable
- policy and approval events must be first-class

## Required Event Types

- `chat.request.received`
- `chat.context.assembled`
- `chat.memory.loaded`
- `chat.route.selected`
- `chat.stream.started`
- `chat.stream.chunk`
- `chat.stream.completed`
- `chat.message.persisted`
- `chat.tool.called`
- `chat.tool.completed`
- `chat.tool.failed`
- `chat.policy.blocked`
- `chat.action.draft_created`
- `chat.action.approval_requested`
- `chat.action.approved`
- `chat.action.rejected`
- `chat.error`

## Base Event Shape

```json
{
  "event_type": "chat.request.received",
  "event_version": "v1",
  "occurred_at": "2026-04-19T12:00:00Z",
  "trace_id": "trace_123",
  "request_id": "req_123",
  "thread_id": "thread_123",
  "message_id": "msg_123",
  "user_id": "user_123",
  "session_id": "sess_123",
  "route": "/strategies/alpha",
  "page_type": "strategy_detail",
  "payload": {}
}
```

## Key Event Payloads

### `chat.context.assembled`

Must include:

- `context_revision`
- `schema_version`
- `entity_refs`
- `payload_size_bytes`
- `token_estimate`
- `freshness`

### `chat.route.selected`

Must include:

- `route_mode`
- `model_name`
- `response_mode`
- `tool_policy_tier`
- `why_selected`

### `chat.tool.called`

Must include:

- `tool_name`
- `tool_class`
- `policy_tier`
- `arguments_redacted`
- `attempt`

### `chat.policy.blocked`

Must include:

- `policy_name`
- `reason_code`
- `requested_capability`
- `required_permission`
- `user_role`

### `chat.action.draft_created`

Must include:

- `draft_type`
- `draft_id`
- `approval_required`
- `risk_precheck_status`

## Correlation Requirements

- every event must carry `trace_id`
- request and streaming events must share the same `request_id`
- action events must reference the originating thread and message
- audit and observability pipelines must preserve correlation ids

## Retention Expectations

- request and error events retained per platform observability policy
- action and policy events retained per audit policy
- streaming chunk retention may be sampled if full retention is too expensive

## Acceptance Conditions

- a single chat interaction can be replayed from event data
- policy blocks are visible and attributable
- tool usage is measurable and attributable
- action-draft lifecycle is fully auditable
