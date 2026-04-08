CREATE TABLE IF NOT EXISTS core_execution_send_attempts (
    send_attempt_id INTEGER PRIMARY KEY AUTOINCREMENT,
    execution_intent_id TEXT NOT NULL,
    attempt_no INTEGER NOT NULL,
    submitted_payload_hash TEXT NOT NULL,
    transport_status TEXT NOT NULL,
    broker_request_ref TEXT NULL,
    error_code TEXT NULL,
    error_message TEXT NULL,
    started_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    finished_at TEXT NULL,
    latency_ms INTEGER NULL,
    FOREIGN KEY (execution_intent_id) REFERENCES core_execution_intents (execution_intent_id),
    UNIQUE (execution_intent_id, attempt_no)
);

CREATE INDEX IF NOT EXISTS ix_exec_send_attempts_intent_attempt
    ON core_execution_send_attempts (execution_intent_id, attempt_no);

CREATE INDEX IF NOT EXISTS ix_exec_send_attempts_status_started
    ON core_execution_send_attempts (transport_status, started_at DESC);
