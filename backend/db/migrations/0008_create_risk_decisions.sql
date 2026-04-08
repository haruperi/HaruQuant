CREATE TABLE IF NOT EXISTS risk_risk_decisions (
    risk_decision_id TEXT PRIMARY KEY,
    risk_request_id TEXT NOT NULL,
    proposal_id TEXT NOT NULL,
    workflow_id TEXT NOT NULL,
    decision TEXT NOT NULL CHECK (
        decision IN ('APPROVE', 'APPROVE_WITH_LIMITS', 'REJECT', 'FORCE_EXIT')
    ),
    rationale_text TEXT NOT NULL,
    risk_metrics_snapshot_json TEXT NOT NULL CHECK (json_valid(risk_metrics_snapshot_json)),
    freshness_expiry TEXT NOT NULL,
    policy_version_id TEXT NOT NULL,
    formula_version TEXT NOT NULL,
    provenance_bundle_id TEXT NULL,
    approval_token TEXT NULL,
    freshness_status TEXT NOT NULL DEFAULT 'fresh',
    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (risk_request_id) REFERENCES risk_risk_assessment_requests (risk_request_id),
    FOREIGN KEY (proposal_id) REFERENCES core_trade_proposals (proposal_id),
    FOREIGN KEY (workflow_id) REFERENCES core_workflows (workflow_id)
);

CREATE UNIQUE INDEX IF NOT EXISTS uq_risk_decisions_approval_token
    ON risk_risk_decisions (approval_token)
    WHERE approval_token IS NOT NULL;

CREATE INDEX IF NOT EXISTS ix_risk_decisions_proposal_created
    ON risk_risk_decisions (proposal_id, created_at DESC);

CREATE INDEX IF NOT EXISTS ix_risk_decisions_decision_created
    ON risk_risk_decisions (decision, created_at DESC);

CREATE INDEX IF NOT EXISTS ix_risk_decisions_freshness_expiry
    ON risk_risk_decisions (freshness_expiry);
