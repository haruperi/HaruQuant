CREATE TABLE IF NOT EXISTS core_workflow_transitions (
    transition_id INTEGER PRIMARY KEY AUTOINCREMENT,
    workflow_id TEXT NOT NULL,
    from_state TEXT NOT NULL,
    to_state TEXT NOT NULL,
    phase_name TEXT NULL,
    transition_reason TEXT NULL,
    actor_type TEXT NOT NULL,
    actor_id TEXT NOT NULL,
    correlation_id TEXT NOT NULL,
    causation_id TEXT NULL,
    occurred_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    metadata_json TEXT NOT NULL DEFAULT '{}' CHECK (json_valid(metadata_json)),
    FOREIGN KEY (workflow_id) REFERENCES core_workflows (workflow_id)
);

CREATE INDEX IF NOT EXISTS ix_core_workflow_transitions_workflow_occurred
    ON core_workflow_transitions (workflow_id, occurred_at);

CREATE INDEX IF NOT EXISTS ix_core_workflow_transitions_correlation
    ON core_workflow_transitions (correlation_id);

CREATE INDEX IF NOT EXISTS ix_core_workflow_transitions_to_state_occurred
    ON core_workflow_transitions (to_state, occurred_at DESC);
