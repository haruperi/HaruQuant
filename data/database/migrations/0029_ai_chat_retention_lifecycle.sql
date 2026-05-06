PRAGMA foreign_keys = OFF;

CREATE TABLE IF NOT EXISTS ai_chat_threads_lifecycle_new (
    thread_id TEXT PRIMARY KEY,
    user_id TEXT NOT NULL,
    title TEXT NOT NULL,
    status TEXT NOT NULL DEFAULT 'active' CHECK (status IN ('active', 'archived', 'deleted', 'purged')),
    retention_class TEXT NOT NULL DEFAULT 'standard' CHECK (retention_class IN ('standard', 'ephemeral', 'regulated', 'legal_hold')),
    active_context_revision TEXT,
    current_route TEXT,
    current_page_type TEXT,
    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    last_message_at TEXT,
    archived_at TEXT,
    deleted_at TEXT,
    purged_at TEXT,
    retention_expires_at TEXT,
    purge_after TEXT,
    legal_hold_until TEXT,
    legal_hold_reason TEXT
);

INSERT INTO ai_chat_threads_lifecycle_new (
    thread_id,
    user_id,
    title,
    status,
    retention_class,
    active_context_revision,
    current_route,
    current_page_type,
    created_at,
    updated_at,
    last_message_at
)
SELECT
    thread_id,
    user_id,
    title,
    status,
    retention_class,
    active_context_revision,
    current_route,
    current_page_type,
    created_at,
    updated_at,
    last_message_at
FROM ai_chat_threads;

DROP TABLE ai_chat_threads;
ALTER TABLE ai_chat_threads_lifecycle_new RENAME TO ai_chat_threads;

CREATE INDEX IF NOT EXISTS idx_ai_chat_threads_user_status_updated
    ON ai_chat_threads (user_id, status, updated_at DESC);

CREATE INDEX IF NOT EXISTS idx_ai_chat_threads_retention_due
    ON ai_chat_threads (status, retention_class, retention_expires_at, purge_after);

CREATE TABLE IF NOT EXISTS ai_chat_lifecycle_audit_events (
    event_id TEXT PRIMARY KEY,
    thread_id TEXT NOT NULL,
    user_id TEXT NOT NULL,
    actor_id TEXT NOT NULL,
    action TEXT NOT NULL,
    from_status TEXT,
    to_status TEXT,
    from_retention_class TEXT,
    to_retention_class TEXT,
    reason TEXT NOT NULL DEFAULT '',
    metadata_json TEXT NOT NULL DEFAULT '{}',
    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (thread_id) REFERENCES ai_chat_threads(thread_id) ON DELETE CASCADE
);

CREATE INDEX IF NOT EXISTS idx_ai_chat_lifecycle_audit_thread_created
    ON ai_chat_lifecycle_audit_events (thread_id, created_at DESC);

PRAGMA foreign_keys = ON;
