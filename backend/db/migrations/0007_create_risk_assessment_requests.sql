CREATE TABLE IF NOT EXISTS risk_risk_assessment_requests (
    risk_request_id TEXT PRIMARY KEY,
    workflow_id TEXT NOT NULL,
    proposal_id TEXT NOT NULL,
    action_type TEXT NOT NULL,
    account_snapshot_ref TEXT NULL,
    portfolio_snapshot_ref TEXT NULL,
    market_snapshot_ref TEXT NULL,
    requested_freshness_json TEXT NOT NULL DEFAULT '{}' CHECK (json_valid(requested_freshness_json)),
    strategy_lifecycle_state TEXT NOT NULL,
    active_policy_bundle_json TEXT NOT NULL CHECK (json_valid(active_policy_bundle_json)),
    compliance_profile_id TEXT NULL,
    current_kill_switch_state TEXT NOT NULL,
    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (workflow_id) REFERENCES core_workflows (workflow_id),
    FOREIGN KEY (proposal_id) REFERENCES core_trade_proposals (proposal_id)
);

CREATE INDEX IF NOT EXISTS ix_risk_requests_proposal_created
    ON risk_risk_assessment_requests (proposal_id, created_at DESC);

CREATE INDEX IF NOT EXISTS ix_risk_requests_workflow_created
    ON risk_risk_assessment_requests (workflow_id, created_at DESC);
