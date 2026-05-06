# AI Chat Conversation Management

Status: production UX contract
Scope: daily-use conversation controls, export, search, regeneration, and status display

## Conversation UI

The AI Chat panel provides:

- searchable conversation list
- rename, delete, archive, restore, purge, retention, and export actions
- active/archived/retention badges
- regenerate last response
- response status and timing/provider metadata
- tools-used, sources-used, and specialists-consulted disclosures on assistant messages
- message-level copy, pin, and save-note actions
- keyboard focus trap while the panel is open

## Keyboard Shortcuts

| Shortcut | Action |
|---|---|
| `/` | Focus conversation search when not typing |
| `Ctrl+N` / `Cmd+N` | Create new conversation |
| `Ctrl+E` / `Cmd+E` | Export active conversation |
| `Ctrl+R` / `Cmd+R` | Regenerate last response |
| `Esc` | Close chat panel |
| `Enter` | Send message |
| `Shift+Enter` | Insert newline |

## Search API

`GET /api/ai-chat/threads?q=<query>&include_archived=<boolean>`

Search matches conversation titles and returns thread summaries sorted by recent activity.

## Export API

`GET /api/ai-chat/threads/{thread_id}/export?format=markdown`

Markdown format:

```markdown
# Conversation title

## User
Message text

## Assistant
Message text
```

`format=json` returns the full `ChatThreadDetail` payload, including messages, pinned facts, memory summary, lifecycle metadata, and message metadata.

Exports write a lifecycle audit event.

## Regenerate API

`POST /api/ai-chat/threads/{thread_id}/responses/regenerate`

The endpoint reuses the latest user message and streams a new assistant answer. Tool side effects remain governed by policy: the chat can propose or display action plans, but direct live execution remains prohibited, and page actions still require the frontend approval/auto-approval path.

## Long Thread Responsiveness

The message list uses a windowed render. Recent messages render first, and older history is loaded into the DOM on demand with `Load older`, keeping long conversations responsive.
