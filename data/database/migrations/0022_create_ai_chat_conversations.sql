CREATE TABLE IF NOT EXISTS ai_chat_threads (
    thread_id TEXT PRIMARY KEY,
    user_id TEXT NOT NULL,
    title TEXT NOT NULL,
    status TEXT NOT NULL DEFAULT 'active' CHECK (status IN ('active', 'archived', 'deleted')),
    retention_class TEXT NOT NULL DEFAULT 'standard' CHECK (retention_class IN ('standard', 'ephemeral', 'legal_hold')),
    active_context_revision TEXT,
    current_route TEXT,
    current_page_type TEXT,
    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    last_message_at TEXT
);

CREATE INDEX IF NOT EXISTS idx_ai_chat_threads_user_status_updated
    ON ai_chat_threads (user_id, status, updated_at DESC);

CREATE TABLE IF NOT EXISTS ai_chat_messages (
    message_id TEXT PRIMARY KEY,
    thread_id TEXT NOT NULL,
    role TEXT NOT NULL CHECK (role IN ('system', 'user', 'assistant', 'tool')),
    content TEXT NOT NULL,
    request_id TEXT,
    tool_calls_json TEXT NOT NULL DEFAULT '[]',
    context_revision TEXT,
    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (thread_id) REFERENCES ai_chat_threads(thread_id) ON DELETE CASCADE
);

CREATE INDEX IF NOT EXISTS idx_ai_chat_messages_thread_created
    ON ai_chat_messages (thread_id, created_at ASC);

CREATE TABLE IF NOT EXISTS ai_chat_memory_summaries (
    summary_id TEXT PRIMARY KEY,
    thread_id TEXT NOT NULL,
    summary_text TEXT NOT NULL,
    source_message_count INTEGER NOT NULL DEFAULT 0,
    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (thread_id) REFERENCES ai_chat_threads(thread_id) ON DELETE CASCADE
);

CREATE INDEX IF NOT EXISTS idx_ai_chat_memory_summaries_thread_created
    ON ai_chat_memory_summaries (thread_id, created_at DESC);

CREATE TABLE IF NOT EXISTS ai_chat_pinned_facts (
    fact_id INTEGER PRIMARY KEY AUTOINCREMENT,
    thread_id TEXT NOT NULL,
    fact_key TEXT NOT NULL,
    fact_value TEXT NOT NULL,
    source TEXT NOT NULL,
    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (thread_id) REFERENCES ai_chat_threads(thread_id) ON DELETE CASCADE,
    UNIQUE (thread_id, fact_key)
);

CREATE INDEX IF NOT EXISTS idx_ai_chat_pinned_facts_thread_created
    ON ai_chat_pinned_facts (thread_id, created_at DESC);
