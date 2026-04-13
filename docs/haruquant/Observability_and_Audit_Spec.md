# Observability and Audit Specification (Playbook §16)

## Trace Model

Every workflow execution produces a `Trace` with fields:
- `trace_id`, `session_id`, `user_id`, `tenant_id`
- `request_id`, `task_id`, `workflow_id`, `step_id`, `tool_call_id`
- `agent_name`, `prompt_version`, `model_name`, `model_version`
- `latency_ms`, `cost`, `result_status`

## Span Model

Each step within a trace produces a `Span`:
- `span_id`, `parent_span_id`, `trace_id`, `name`
- `start_time`, `end_time`, `duration_ms`, `status`
- `attributes`, `events`, `children`

## Redaction Rules

Fields matching these patterns are redacted to `[REDACTED]`:
- password, secret, token, api_key, auth, credential

## Cost Tracking

Per-trace and per-span cost aggregation via `CostTracker`:
- Input/output token counts
- USD cost based on model pricing
- Per-request, per-workflow, per-session limits

## Audit Services

| Service | Purpose |
|---|---|
| replay.py | Full workflow replay from traces |
| replay_completeness.py | Verify all steps recorded |
| replay_diff.py | Compare two replay runs |
| replay_runner.py | Execute replay |
| export.py | Export audit data |
| legal_hold.py | Prevent data deletion |
| manifest.py | Audit manifest generation |
| signing.py | Cryptographic audit signing |

## Retention

- Audit logs retained per `retention_policy.yaml`
- Legal hold overrides all retention rules
- Personal data redacted before logging
