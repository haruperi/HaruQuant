CREATE TABLE IF NOT EXISTS ai_chat_action_drafts (
    draft_id TEXT PRIMARY KEY,
    thread_id TEXT NOT NULL,
    user_id TEXT NOT NULL,
    request_id TEXT NULL,
    draft_type TEXT NOT NULL,
    title TEXT NOT NULL,
    description TEXT NOT NULL,
    payload_json TEXT NOT NULL DEFAULT '{}' CHECK (json_valid(payload_json)),
    risk_precheck_status TEXT NOT NULL DEFAULT 'not_required',
    risk_precheck_notes TEXT NOT NULL DEFAULT '',
    approval_id TEXT NULL,
    status TEXT NOT NULL DEFAULT 'draft',
    requires_human_approval INTEGER NOT NULL DEFAULT 1 CHECK (requires_human_approval IN (0, 1)),
    side_effect_status TEXT NOT NULL DEFAULT 'not_executed',
    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (thread_id) REFERENCES ai_chat_threads (thread_id) ON DELETE CASCADE,
    FOREIGN KEY (approval_id) REFERENCES gov_approvals (approval_id)
);

CREATE INDEX IF NOT EXISTS ix_ai_chat_action_drafts_thread_created
    ON ai_chat_action_drafts (thread_id, created_at DESC);
CREATE INDEX IF NOT EXISTS ix_ai_chat_action_drafts_user_status
    ON ai_chat_action_drafts (user_id, status, created_at DESC);
CREATE INDEX IF NOT EXISTS ix_ai_chat_action_drafts_approval
    ON ai_chat_action_drafts (approval_id);

ALTER TABLE ai_chat_messages ADD COLUMN action_draft_id TEXT NULL REFERENCES ai_chat_action_drafts (draft_id);

CREATE INDEX IF NOT EXISTS ix_ai_chat_messages_action_draft
    ON ai_chat_messages (action_draft_id, created_at DESC);
