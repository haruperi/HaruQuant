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
- `live_ops_summary`
- `portfolio_allocation_review`
- `daily_desk_pack`
- `trade_review_assistant`

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

### 7. Live Ops Summary

`n8n` steps:
1. Schedule during live trading hours or after a live heartbeat
2. Build `live_ops_summary` payload with `session_id`
3. Sign request
4. HTTP Request -> HaruQuant
5. Route the returned operating-state memo to the operations channel when useful

### 8. Daily Desk Pack

`n8n` steps:
1. Schedule once per desk reporting cycle
2. Build `daily_desk_pack` payload with the required research and risk inputs
3. Optionally include:
   - `session_id`
   - `backtest_id`, `optimization_id`, `strategy_version_id`
   - `incident_run_id`
4. Sign request
5. HTTP Request -> HaruQuant
6. Route the returned consolidated summary and artifact refs to the desk distribution channel

### 9. Trade Review Assistant

`n8n` steps:
1. Usually do not schedule this workflow
2. Use it only when an operator-facing approval or review surface needs a structured advisory response
3. Build `trade_review_assistant` payload with:
   - `session_id`
   - `trade_request`
   - optional `what_if_actions`
   - optional `edge_snapshot_id`
4. Sign request
5. HTTP Request -> HaruQuant
6. Route the advisory response back to the human operator

## Example Payload Files

See:
- [daily_edge_brief.json](C:/Users/rharu/Documents/MyApplications/HaruQuant/docs/haruquant/ai_agents/n8n_examples/daily_edge_brief.json)
- [risk_alert.json](C:/Users/rharu/Documents/MyApplications/HaruQuant/docs/haruquant/ai_agents/n8n_examples/risk_alert.json)
- [daily_desk_pack.json](C:/Users/rharu/Documents/MyApplications/HaruQuant/docs/haruquant/ai_agents/n8n_examples/daily_desk_pack.json)

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

## Phase 6 Notes

Phase 6 is now implemented on the Python side as an approval boundary for privileged actions.

Current approval-backed action families:
- `strategy_promotion`
- `live_deployment`
- `live_pause_session`
- `live_stop_session`
- `risk_override`

What `n8n` may eventually do:
- notify an operator that a new approval request exists
- present approval details in Slack/Telegram/email/ticketing
- call HaruQuant again after a human decision is made

What `n8n` should not do:
- decide approvals itself
- rewrite approval payloads
- execute live stop/pause or risk overrides directly

When the final `n8n` integration pass happens, the intended approval flow is:
1. HaruQuant creates an approval artifact with `approval_request_action`.
2. `n8n` routes that artifact to a human approval surface.
3. A human decision is sent back to HaruQuant through `approval_apply_decision`.
4. HaruQuant executes the matching privileged wrapper only after the artifact is in `approved` status.

## Phase 7 Notes

Phase 7 adds deterministic report packaging and the first consolidated desk memo.

Current packaged workflow:
- `daily_desk_pack`

When `n8n` is eventually wired, it should:
- trigger `daily_desk_pack` on a schedule
- route the returned summary
- optionally forward the returned `artifact_refs` links or paths to downstream operators

It should not:
- assemble the desk pack itself
- merge workflow summaries itself
- regenerate the report artifacts itself

## Live Ops Notes

`live_ops_summary` is now available on the Python side and is the preferred live-operations input for `daily_desk_pack`.

When `n8n` is eventually configured, it should:
- trigger `live_ops_summary` directly when operations wants a standalone memo
- provide `session_id` to `daily_desk_pack` so the live-ops section is included

It should not:
- compute live operating state itself
- infer pause/stop recommendations from raw counters outside HaruQuant

## Trade Review Notes

`trade_review_assistant` is now available on the Python side as a bounded simulator/manual-review workflow.

When `n8n` is eventually configured, it should only use this workflow for human-facing review orchestration, not as an autonomous trade path.

It should not:
- submit reviewed trades automatically
- reinterpret simulator governance outside HaruQuant
- bypass the existing approval boundary for privileged actions
