# AI Chat Retention And Archival Policy

Status: canonical governance policy
Owner: AI platform lead and compliance owner
Review cadence: quarterly, and after any material change to chat memory, trading workflows, or regulated artifacts

## Purpose

This policy defines how HaruQuant AI Chat conversations are retained, archived, deleted, purged, exported, and placed under legal hold.

## Policy Classes

| Class | Use | Retention |
|---|---|---|
| `ephemeral` | Short-lived, low-value conversations | 30 days, then delete and purge when eligible |
| `standard` | Normal product support and workflow conversations | 24 months retention; archive after 12 months of inactivity |
| `regulated` | Signal proposals, action drafts, approvals, paper/live execution evidence, or trading-adjacent records | 7 years; archive after 12 months of inactivity; no early purge |
| `legal_hold` | Investigation, dispute, audit, or compliance preservation | Indefinite until released by an authorized operator |

Regulated content overrides user-selected ephemeral retention.

## Lifecycle States

| State | Meaning |
|---|---|
| `active` | Visible in the normal chat list and eligible for active memory |
| `archived` | Hidden from the default list, exportable and auditable |
| `deleted` | Hidden from users; retained until purge eligibility is reviewed |
| `purged` | User-facing content is removed or redacted; audit trail remains |

## Automatic Classification

Conversations are automatically upgraded to `regulated` when they contain or produce:

- signal proposals saved to watchlist or review queue
- action drafts
- approval requests
- governed workflow or execution references
- paper/live execution receipts

## Deletion And Purge

User deletion is a soft-delete. It sets the conversation to `deleted` and hides it from normal views.

Purge is a separate lifecycle action. Purge redacts message content and metadata, removes memory summaries and pinned facts, clears active page context, and records an audit event.

`regulated` and `legal_hold` conversations cannot be purged early.

## Legal Hold

Legal hold changes the retention class to `legal_hold`, clears purge eligibility, and stores the hold reason. Legal hold blocks purge until explicitly released by an authorized operator.

## Audit Requirements

The system records lifecycle audit events for:

- thread creation
- archive, restore, delete, purge
- retention class changes
- export
- legal hold application and release

Audit records include actor, action, previous state, new state, reason, and timestamp.

## Data Minimization

The chatbot must avoid retaining unnecessary sensitive data:

- raw DOM snapshots are not stored as durable memory
- page context remains compact and versioned
- secrets, tokens, passwords, email addresses, and long account/card-like numbers are redacted from stored messages
- archived and deleted conversations are excluded from normal active-thread lists

## Operator Procedure

1. Run the lifecycle job daily.
2. Review lifecycle summaries weekly.
3. Apply legal hold before investigations or disputes.
4. Release legal hold only with compliance approval.
5. Treat purge as irreversible from the user-content perspective.

## Implementation Map

- Schema: `ai_chat_threads` lifecycle columns and `ai_chat_lifecycle_audit_events`
- Service: `ConversationRetentionService`
- API: archive, restore, retention details, retention update, lifecycle run
- UI: thread menu actions for retention details, 30-day retention, archive, export, delete
- Job: `scripts/run_ai_chat_retention_lifecycle.py`
