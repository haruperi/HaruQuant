# HaruQuant Agent n8n Integration

This page defines when to move from Python-only agent work into `n8n`, and what to configure there.

## When To Move To n8n

Stay in Python first while:
- adding or changing planner logic
- adding or changing specialist agents
- adding or changing tool implementations
- adding policy, verifier, approval, or evidence rules
- changing business logic for research, risk, validation, or incident workflows

Move to `n8n` only when:
- the Python workflow already runs correctly through HaruQuant
- the payload contract is stable enough to automate
- you need scheduling, notification routing, or external ticketing/integration steps

Short rule:
- Python owns workflow logic
- `n8n` owns scheduling and external routing

## Shared Secret

Set this environment variable on the HaruQuant API host before enabling inbound signed webhooks:

```powershell
$env:HQT_N8N_WEBHOOK_SECRET = "replace-with-long-random-secret"
```

The same secret must be used by `n8n` when it computes `X-Haru-Signature`.

## Inbound Webhook

`n8n` calls HaruQuant here:

`POST /api/agents/n8n/trigger`

Headers:
- `Content-Type: application/json`
- `X-Haru-Signature: sha256=<hmac-hexdigest>`

Body shape:

```json
{
  "task_id": "daily-brief-2026-04-01",
  "task_type": "daily_market_brief",
  "actor_user_id": 0,
  "actor_role": "n8n",
  "scope": "edge",
  "intent": "daily_market_brief",
  "correlation_id": "n8n-daily-brief-2026-04-01",
  "run_id": "run-daily-brief-2026-04-01",
  "input_payload": {
    "symbol": "EURUSD",
    "timeframe": "H1"
  },
  "approval_mode": "auto_read_only"
}
```

## Current Supported Inbound Workflow Types

- `daily_market_brief`
- `live_risk_watch`
- `incident_review`
- `strategy_promotion_review`
- `snapshot_drift_watch`
- `execution_quality_watch`
- `portfolio_allocation_review`

## Outbound Flow

HaruQuant currently supports outbound workflow triggers through the Python `N8NClient`.

Current behavior:
- if `config/agent_settings.json` contains an `n8n.webhook_url`, HaruQuant will POST there
- otherwise HaruQuant writes a signed payload to `artifacts/workflows/n8n_outbox/`

This local outbox mode is the safe default for development.

## Example n8n Workflows To Configure

### 1. Daily Edge Brief

`n8n` steps:
1. Schedule Trigger
2. Set JSON body for `daily_market_brief`
3. Compute HMAC signature
4. HTTP Request -> HaruQuant `/api/agents/n8n/trigger`
5. Send Slack/Telegram/Email message from returned summary

### 2. Risk Alert

`n8n` steps:
1. Schedule Trigger or event trigger
2. Set JSON body for `live_risk_watch`
3. Compute HMAC signature
4. HTTP Request -> HaruQuant `/api/agents/n8n/trigger`
5. Route only if returned metadata/state indicates caution or escalation

### 3. Strategy Review Packet

`n8n` steps:
1. Trigger after optimization completion
2. Build `strategy_promotion_review` payload
3. Sign request
4. HTTP Request -> HaruQuant
5. Send review packet to operator channel

### 4. Snapshot Drift Watch

`n8n` steps:
1. Schedule after a new Edge snapshot is saved
2. Build `snapshot_drift_watch` payload with either:
   - `left_snapshot_id` and `right_snapshot_id`, or
   - `symbol` and `timeframe` so HaruQuant resolves the latest two snapshots
3. Sign request
4. HTTP Request -> HaruQuant
5. Route the returned fit-change memo to research or strategy-review channels

### 5. Execution Quality Watch

`n8n` steps:
1. Schedule during live trading hours or after a session heartbeat
2. Build `execution_quality_watch` payload with `session_id`
3. Sign request
4. HTTP Request -> HaruQuant
5. Route only non-`normal` responses to the operations channel

### 6. Portfolio Allocation Review

`n8n` steps:
1. Trigger after a new risk snapshot or overnight risk batch completes
2. Build `portfolio_allocation_review` payload with `snapshot_id`
3. Optionally include `edge_snapshot_id` for Edge context
4. Sign request
5. HTTP Request -> HaruQuant
6. Route the returned allocation memo to the portfolio manager channel

## Example Payload Files

See:
- [daily_edge_brief.json](C:/Users/rharu/Documents/MyApplications/HaruQuant/docs/haruquant/ai_agents/n8n_examples/daily_edge_brief.json)
- [risk_alert.json](C:/Users/rharu/Documents/MyApplications/HaruQuant/docs/haruquant/ai_agents/n8n_examples/risk_alert.json)

## What You Need To Do In n8n

1. Create an HTTP Request node that posts to HaruQuant `/api/agents/n8n/trigger`.
2. Reuse the exact JSON payload shape from the example files.
3. Add a Code node that computes `X-Haru-Signature` with the shared secret.
4. Route the returned `summary`, `status`, and `metadata` to Slack/Telegram/email or follow-up nodes.
5. Do not reimplement HaruQuant decision logic in `n8n`.

## Phase 5 Notes

These Phase 5 workflows are now ready on the Python side, but the actual `n8n` buildout should still wait until the remaining Python phases are complete:
- `snapshot_drift_watch`
- `execution_quality_watch`
- `portfolio_allocation_review`

When `n8n` is finally configured, it should only:
- trigger those workflows
- route their summaries and warnings
- escalate based on returned metadata

It should not:
- compare snapshots itself
- infer allocation actions itself
- compute execution quality itself
