CREATE TABLE IF NOT EXISTS core_reconciliation_runs (
    reconciliation_run_id INTEGER PRIMARY KEY AUTOINCREMENT,
    execution_intent_id TEXT NOT NULL,
    run_reason TEXT NOT NULL,
    result_state TEXT NOT NULL,
    broker_truth_json TEXT NOT NULL DEFAULT '{}' CHECK (json_valid(broker_truth_json)),
    local_truth_json TEXT NOT NULL DEFAULT '{}' CHECK (json_valid(local_truth_json)),
    conflict_flag INTEGER NOT NULL DEFAULT 0 CHECK (conflict_flag IN (0, 1)),
    incident_id TEXT NULL,
    started_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    completed_at TEXT NULL,
    FOREIGN KEY (execution_intent_id) REFERENCES core_execution_intents (execution_intent_id)
);

CREATE INDEX IF NOT EXISTS ix_reconciliation_runs_intent_started
    ON core_reconciliation_runs (execution_intent_id, started_at DESC);

CREATE INDEX IF NOT EXISTS ix_reconciliation_runs_result_started
    ON core_reconciliation_runs (result_state, started_at DESC);

CREATE INDEX IF NOT EXISTS ix_reconciliation_runs_conflict_started
    ON core_reconciliation_runs (conflict_flag, started_at DESC);
