CREATE TABLE IF NOT EXISTS core_workflow_steps (
    step_id TEXT PRIMARY KEY,
    workflow_id TEXT NOT NULL,
    step_order INTEGER NOT NULL,
    step_type TEXT NOT NULL,
    assigned_agent TEXT NULL,
    input_contract_type TEXT NULL,
    input_ref TEXT NULL,
    output_contract_type TEXT NULL,
    output_ref TEXT NULL,
    status TEXT NOT NULL,
    started_at TEXT NULL,
    completed_at TEXT NULL,
    latency_ms INTEGER NULL,
    iteration_no INTEGER NOT NULL DEFAULT 0,
    metadata_json TEXT NOT NULL DEFAULT '{}' CHECK (json_valid(metadata_json)),
    FOREIGN KEY (workflow_id) REFERENCES core_workflows (workflow_id)
);

CREATE INDEX IF NOT EXISTS ix_core_workflow_steps_workflow_order
    ON core_workflow_steps (workflow_id, step_order);

CREATE INDEX IF NOT EXISTS ix_core_workflow_steps_agent_started
    ON core_workflow_steps (assigned_agent, started_at DESC);
