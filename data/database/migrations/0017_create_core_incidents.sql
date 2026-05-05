CREATE TABLE IF NOT EXISTS core_incidents (
    incident_id TEXT PRIMARY KEY,
    severity TEXT NOT NULL,
    state TEXT NOT NULL CHECK (state IN ('OPEN', 'ACKNOWLEDGED', 'RESOLVED', 'CLOSED')),
    alert_type TEXT NOT NULL,
    source TEXT NOT NULL,
    summary TEXT NOT NULL,
    opened_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    resolved_at TEXT NULL,
    recommended_action TEXT NULL,
    metadata_json TEXT NOT NULL DEFAULT '{}' CHECK (json_valid(metadata_json))
);

CREATE INDEX IF NOT EXISTS ix_incidents_state_opened
    ON core_incidents (state, opened_at DESC);

CREATE INDEX IF NOT EXISTS ix_incidents_severity_opened
    ON core_incidents (severity, opened_at DESC);
