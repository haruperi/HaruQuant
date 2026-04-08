CREATE TABLE IF NOT EXISTS research_evidence_bundles (
    evidence_bundle_id TEXT PRIMARY KEY,
    workflow_id TEXT NULL,
    bundle_type TEXT NOT NULL,
    summary TEXT NOT NULL,
    content_ref TEXT NULL,
    content_hash TEXT NOT NULL,
    freshness_status TEXT NOT NULL,
    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (workflow_id) REFERENCES core_workflows (workflow_id)
);

CREATE INDEX IF NOT EXISTS ix_evidence_bundles_workflow_created
    ON research_evidence_bundles (workflow_id, created_at DESC);
CREATE INDEX IF NOT EXISTS ix_evidence_bundles_type_created
    ON research_evidence_bundles (bundle_type, created_at DESC);

CREATE TABLE IF NOT EXISTS audit_trajectory_logs (
    log_id TEXT PRIMARY KEY,
    workflow_id TEXT NOT NULL,
    correlation_id TEXT NOT NULL,
    agent_name TEXT NOT NULL,
    phase TEXT NOT NULL,
    iteration_no INTEGER NOT NULL,
    input_schema TEXT NOT NULL,
    input_hash TEXT NOT NULL,
    output_schema TEXT NOT NULL,
    output_hash TEXT NOT NULL,
    tool_calls_json TEXT NOT NULL DEFAULT '[]' CHECK (json_valid(tool_calls_json)),
    observation_payload_ref TEXT NULL,
    evaluation_output_ref TEXT NULL,
    latency_ms INTEGER NOT NULL,
    token_usage_json TEXT NULL CHECK (token_usage_json IS NULL OR json_valid(token_usage_json)),
    final_state TEXT NOT NULL,
    signature TEXT NULL,
    artifact_ref TEXT NULL,
    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (workflow_id) REFERENCES core_workflows (workflow_id)
);

CREATE INDEX IF NOT EXISTS ix_trajectory_logs_workflow_created
    ON audit_trajectory_logs (workflow_id, created_at);
CREATE INDEX IF NOT EXISTS ix_trajectory_logs_correlation
    ON audit_trajectory_logs (correlation_id);
CREATE INDEX IF NOT EXISTS ix_trajectory_logs_agent_created
    ON audit_trajectory_logs (agent_name, created_at DESC);

CREATE TABLE IF NOT EXISTS audit_replay_bundles (
    replay_bundle_id TEXT PRIMARY KEY,
    workflow_id TEXT NOT NULL,
    bundle_hash TEXT NOT NULL,
    object_store_uri TEXT NOT NULL,
    completeness_status TEXT NOT NULL,
    export_profile TEXT NULL,
    integrity_manifest_ref TEXT NULL,
    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (workflow_id) REFERENCES core_workflows (workflow_id)
);

CREATE INDEX IF NOT EXISTS ix_replay_bundles_workflow_created
    ON audit_replay_bundles (workflow_id, created_at DESC);
CREATE INDEX IF NOT EXISTS ix_replay_bundles_hash
    ON audit_replay_bundles (bundle_hash);

CREATE TABLE IF NOT EXISTS audit_legal_holds (
    legal_hold_id INTEGER PRIMARY KEY AUTOINCREMENT,
    target_type TEXT NOT NULL,
    target_ref_id TEXT NOT NULL,
    hold_reason TEXT NOT NULL,
    placed_by_actor_id TEXT NOT NULL,
    placed_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    released_at TEXT NULL
);

CREATE INDEX IF NOT EXISTS ix_legal_holds_target
    ON audit_legal_holds (target_type, target_ref_id);
CREATE INDEX IF NOT EXISTS ix_legal_holds_released
    ON audit_legal_holds (released_at);
