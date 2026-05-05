CREATE TABLE IF NOT EXISTS core_broker_positions (
    broker_position_id TEXT PRIMARY KEY,
    environment TEXT NOT NULL,
    account_id TEXT NOT NULL,
    symbol TEXT NOT NULL,
    side TEXT NOT NULL,
    quantity REAL NOT NULL,
    avg_price REAL NOT NULL,
    stop_loss REAL NULL,
    take_profit REAL NULL,
    authoritative_snapshot_at TEXT NOT NULL,
    local_status TEXT NOT NULL,
    metadata_json TEXT NOT NULL DEFAULT '{}' CHECK (json_valid(metadata_json))
);

CREATE INDEX IF NOT EXISTS ix_broker_positions_account_symbol
    ON core_broker_positions (account_id, symbol);

CREATE INDEX IF NOT EXISTS ix_broker_positions_symbol_snapshot
    ON core_broker_positions (symbol, authoritative_snapshot_at DESC);

CREATE INDEX IF NOT EXISTS ix_broker_positions_status_snapshot
    ON core_broker_positions (local_status, authoritative_snapshot_at DESC);
