CREATE TABLE IF NOT EXISTS core_execution_intents (
    execution_intent_id TEXT PRIMARY KEY,
    workflow_id TEXT NOT NULL,
    proposal_id TEXT NOT NULL,
    risk_decision_id TEXT NOT NULL,
    action_type TEXT NOT NULL,
    symbol TEXT NOT NULL,
    side TEXT NOT NULL,
    order_type TEXT NOT NULL,
    size_json TEXT NOT NULL CHECK (json_valid(size_json)),
    price_params_json TEXT NOT NULL DEFAULT '{}' CHECK (json_valid(price_params_json)),
    sl_tp_params_json TEXT NOT NULL DEFAULT '{}' CHECK (json_valid(sl_tp_params_json)),
    idempotency_key TEXT NOT NULL,
    client_order_id TEXT NULL,
    status TEXT NOT NULL,
    expiry_at TEXT NULL,
    pre_send_validation_snapshot_ref TEXT NULL,
    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (workflow_id) REFERENCES core_workflows (workflow_id),
    FOREIGN KEY (proposal_id) REFERENCES core_trade_proposals (proposal_id),
    FOREIGN KEY (risk_decision_id) REFERENCES risk_risk_decisions (risk_decision_id),
    UNIQUE (idempotency_key)
);

CREATE INDEX IF NOT EXISTS ix_execution_intents_status_created
    ON core_execution_intents (status, created_at DESC);

CREATE INDEX IF NOT EXISTS ix_execution_intents_proposal
    ON core_execution_intents (proposal_id);

CREATE INDEX IF NOT EXISTS ix_execution_intents_risk_decision
    ON core_execution_intents (risk_decision_id);

CREATE INDEX IF NOT EXISTS ix_execution_intents_symbol_created
    ON core_execution_intents (symbol, created_at DESC);

CREATE INDEX IF NOT EXISTS ix_execution_intents_client_order
    ON core_execution_intents (client_order_id);
