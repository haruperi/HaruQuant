ALTER TABLE ai_chat_action_drafts ADD COLUMN governed_workflow_id TEXT NULL REFERENCES core_workflows (workflow_id);
ALTER TABLE ai_chat_action_drafts ADD COLUMN execution_intent_id TEXT NULL REFERENCES core_execution_intents (execution_intent_id);
ALTER TABLE ai_chat_action_drafts ADD COLUMN execution_receipt_id TEXT NULL REFERENCES core_execution_receipts (receipt_id);

CREATE INDEX IF NOT EXISTS ix_ai_chat_action_drafts_workflow
    ON ai_chat_action_drafts (governed_workflow_id);
CREATE INDEX IF NOT EXISTS ix_ai_chat_action_drafts_execution_intent
    ON ai_chat_action_drafts (execution_intent_id);
