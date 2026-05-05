ALTER TABLE ai_chat_messages ADD COLUMN signal_proposal_id TEXT NULL;

CREATE TABLE IF NOT EXISTS ai_chat_signal_proposals (
    proposal_id TEXT PRIMARY KEY,
    thread_id TEXT NOT NULL,
    user_id TEXT NOT NULL,
    request_id TEXT,
    title TEXT NOT NULL,
    hypothesis TEXT NOT NULL,
    symbol TEXT NOT NULL,
    timeframe TEXT NOT NULL,
    direction TEXT NOT NULL,
    entry_logic TEXT NOT NULL,
    exit_logic TEXT NOT NULL,
    confidence INTEGER NOT NULL,
    rationale TEXT NOT NULL,
    risk_note TEXT NOT NULL,
    status TEXT NOT NULL DEFAULT 'draft',
    watchlist_saved INTEGER NOT NULL DEFAULT 0,
    review_queue_saved INTEGER NOT NULL DEFAULT 0,
    non_executed_label TEXT NOT NULL DEFAULT 'non_executed_signal_proposal',
    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (thread_id) REFERENCES ai_chat_threads (thread_id)
);

CREATE INDEX IF NOT EXISTS ix_ai_chat_signal_proposals_thread_created
    ON ai_chat_signal_proposals (thread_id, created_at DESC);

CREATE INDEX IF NOT EXISTS ix_ai_chat_signal_proposals_user_status_created
    ON ai_chat_signal_proposals (user_id, status, created_at DESC);
