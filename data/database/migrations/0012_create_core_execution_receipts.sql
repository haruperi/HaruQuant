CREATE TABLE IF NOT EXISTS core_execution_receipts (
    receipt_id TEXT PRIMARY KEY,
    execution_intent_id TEXT NOT NULL,
    broker TEXT NOT NULL DEFAULT 'mt5',
    broker_order_id TEXT NULL,
    broker_deal_id TEXT NULL,
    receipt_status TEXT NOT NULL,
    requested_price REAL NULL,
    fill_price REAL NULL,
    fill_qty REAL NULL,
    spread_points REAL NULL,
    slippage_points REAL NULL,
    slippage_bps REAL NULL,
    raw_receipt_ref TEXT NULL,
    broker_message TEXT NULL,
    broker_retcode INTEGER NULL,
    authoritative_state TEXT NOT NULL DEFAULT 'PROVISIONAL',
    received_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (execution_intent_id) REFERENCES core_execution_intents (execution_intent_id)
);

CREATE INDEX IF NOT EXISTS ix_execution_receipts_intent_received
    ON core_execution_receipts (execution_intent_id, received_at DESC);

CREATE INDEX IF NOT EXISTS ix_execution_receipts_broker_order
    ON core_execution_receipts (broker_order_id);

CREATE INDEX IF NOT EXISTS ix_execution_receipts_broker_deal
    ON core_execution_receipts (broker_deal_id);

CREATE INDEX IF NOT EXISTS ix_execution_receipts_status_received
    ON core_execution_receipts (receipt_status, received_at DESC);
