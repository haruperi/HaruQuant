CREATE TABLE IF NOT EXISTS core_observations (
    observation_id TEXT PRIMARY KEY,
    workflow_id TEXT NOT NULL,
    observation_type TEXT NOT NULL,
    severity TEXT NOT NULL,
    source TEXT NOT NULL,
    payload_ref TEXT NULL,
    payload_json TEXT NULL CHECK (payload_json IS NULL OR json_valid(payload_json)),
    authority_state TEXT NOT NULL,
    freshness_status TEXT NOT NULL,
    occurred_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (workflow_id) REFERENCES core_workflows (workflow_id)
);

CREATE INDEX IF NOT EXISTS ix_observations_workflow_occurred
    ON core_observations (workflow_id, occurred_at DESC);

CREATE INDEX IF NOT EXISTS ix_observations_severity_occurred
    ON core_observations (severity, occurred_at DESC);

CREATE INDEX IF NOT EXISTS ix_observations_source_occurred
    ON core_observations (source, occurred_at DESC);
