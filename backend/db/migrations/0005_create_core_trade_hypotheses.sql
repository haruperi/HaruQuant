CREATE TABLE IF NOT EXISTS core_trade_hypotheses (
    hypothesis_id TEXT PRIMARY KEY,
    workflow_id TEXT NOT NULL,
    strategy_id TEXT NULL,
    symbol TEXT NOT NULL,
    direction TEXT NOT NULL,
    thesis_text TEXT NOT NULL,
    entry_rationale TEXT NOT NULL,
    invalidation_rationale TEXT NOT NULL,
    stop_loss_logic_json TEXT NOT NULL CHECK (json_valid(stop_loss_logic_json)),
    take_profit_logic_json TEXT NULL CHECK (take_profit_logic_json IS NULL OR json_valid(take_profit_logic_json)),
    holding_horizon TEXT NOT NULL,
    confidence_score REAL NOT NULL CHECK (confidence_score >= 0.0 AND confidence_score <= 1.0),
    calibration_note TEXT NULL,
    strategy_family TEXT NOT NULL,
    feature_version TEXT NOT NULL,
    strategy_code_hash TEXT NOT NULL,
    evidence_bundle_id TEXT NULL,
    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (workflow_id) REFERENCES core_workflows (workflow_id)
);

CREATE INDEX IF NOT EXISTS ix_core_trade_hypotheses_workflow_created
    ON core_trade_hypotheses (workflow_id, created_at DESC);

CREATE INDEX IF NOT EXISTS ix_core_trade_hypotheses_symbol_created
    ON core_trade_hypotheses (symbol, created_at DESC);

CREATE INDEX IF NOT EXISTS ix_core_trade_hypotheses_strategy_created
    ON core_trade_hypotheses (strategy_id, created_at DESC);
