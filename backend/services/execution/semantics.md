# Execution Semantics: Exactly-Once vs At-Least-Once (Playbook §13)

## Action Class Semantics

| Class | Semantics | Description |
|---|---|---|
| A (read-only) | At-least-once | Safe to retry; no side effects |
| B (low-risk write) | At-least-once with idempotency | Reversible; retry with same idempotency key |
| C (material write) | Exactly-once | Requires idempotency key + dedup check |
| D (high-risk write) | Exactly-once + approval | Idempotency key + human approval before first execution |
| E (irreversible) | Exactly-once + dual-auth | Two approvals + idempotency key, no retry after execution |

## Idempotency Key Design

- Generated from: `SHA-256(action_type + target_ref + params_hash + user_id)`
- Stored in execution record with status: `pending`, `executed`, `failed`
- Duplicate detection: If key exists with status `executed`, return cached result
- TTL: Idempotency keys expire after 24 hours

## Middleware Placement

Idempotency check occurs in `backend/services/execution/idempotency.py` before any side-effecting operation. The check is:

1. Compute idempotency key from request
2. Look up key in execution store
3. If found with `executed` status → return cached result (no re-execution)
4. If found with `pending` status → reject with conflict error
5. If not found → create record with `pending` status, execute, update to `executed`
