CREATE TABLE IF NOT EXISTS core_trade_proposals (
    proposal_id TEXT PRIMARY KEY,
    workflow_id TEXT NOT NULL,
    hypothesis_id TEXT NOT NULL,
    state TEXT NOT NULL CHECK (
        state IN (
            'DRAFT',
            'EVIDENCE_PENDING',
            'READY_FOR_RISK',
            'APPROVED',
            'APPROVED_WITH_LIMITS',
            'REJECTED',
            'EXPIRED',
            'EXECUTION_PENDING',
            'SENT',
            'ACKNOWLEDGED',
            'PARTIALLY_FILLED',
            'FILLED',
            'EXECUTION_FAILED',
            'CLOSED'
        )
    ),
    symbol TEXT NOT NULL,
    direction TEXT NOT NULL,
    candidate_price_logic_json TEXT NOT NULL CHECK (json_valid(candidate_price_logic_json)),
    proposed_size_json TEXT NOT NULL CHECK (json_valid(proposed_size_json)),
    operating_envelope_json TEXT NOT NULL DEFAULT '{}' CHECK (json_valid(operating_envelope_json)),
    session_restrictions_json TEXT NOT NULL DEFAULT '{}' CHECK (json_valid(session_restrictions_json)),
    expiry_at TEXT NULL,
    transformation_version TEXT NOT NULL,
    readiness_state TEXT NOT NULL,
    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (workflow_id) REFERENCES core_workflows (workflow_id),
    FOREIGN KEY (hypothesis_id) REFERENCES core_trade_hypotheses (hypothesis_id)
);

CREATE INDEX IF NOT EXISTS ix_core_trade_proposals_state_updated
    ON core_trade_proposals (state, updated_at DESC);

CREATE INDEX IF NOT EXISTS ix_core_trade_proposals_symbol_state_created
    ON core_trade_proposals (symbol, state, created_at DESC);

CREATE INDEX IF NOT EXISTS ix_core_trade_proposals_workflow_created
    ON core_trade_proposals (workflow_id, created_at DESC);
