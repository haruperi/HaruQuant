-- Phase 4 - Agentic Firm database tables and audit persistence.
--
-- This migration is additive. Existing canonical tables such as
-- core_trade_proposals, risk_risk_decisions, core_execution_intents, and
-- core_execution_receipts remain the source of truth. Compatibility views are
-- created for Phase 4 names where the data already exists.

CREATE TABLE IF NOT EXISTS agent_tasks (
    task_id TEXT PRIMARY KEY,
    parent_task_id TEXT NULL,
    workflow_id TEXT NULL,
    title TEXT NOT NULL,
    description TEXT NOT NULL,
    owner_agent TEXT NOT NULL,
    status TEXT NOT NULL CHECK (
        status IN ('pending', 'assigned', 'running', 'blocked', 'completed', 'failed', 'cancelled')
    ),
    priority INTEGER NOT NULL DEFAULT 3 CHECK (priority BETWEEN 0 AND 5),
    expected_output_contract TEXT NULL,
    required_tools_json TEXT NOT NULL DEFAULT '[]' CHECK (json_valid(required_tools_json)),
    input_refs_json TEXT NOT NULL DEFAULT '[]' CHECK (json_valid(input_refs_json)),
    metadata_json TEXT NOT NULL DEFAULT '{}' CHECK (json_valid(metadata_json)),
    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    due_at TEXT NULL,
    FOREIGN KEY (parent_task_id) REFERENCES agent_tasks (task_id),
    FOREIGN KEY (workflow_id) REFERENCES core_workflows (workflow_id)
);

CREATE INDEX IF NOT EXISTS ix_agent_tasks_workflow_status_updated
    ON agent_tasks (workflow_id, status, updated_at DESC);
CREATE INDEX IF NOT EXISTS ix_agent_tasks_owner_status_due
    ON agent_tasks (owner_agent, status, due_at);
CREATE INDEX IF NOT EXISTS ix_agent_tasks_parent_created
    ON agent_tasks (parent_task_id, created_at);

CREATE TABLE IF NOT EXISTS agent_task_events (
    event_id INTEGER PRIMARY KEY AUTOINCREMENT,
    task_id TEXT NOT NULL,
    event_type TEXT NOT NULL,
    from_status TEXT NULL,
    to_status TEXT NULL,
    actor_type TEXT NOT NULL,
    actor_id TEXT NOT NULL,
    event_payload_json TEXT NOT NULL DEFAULT '{}' CHECK (json_valid(event_payload_json)),
    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (task_id) REFERENCES agent_tasks (task_id)
);

CREATE INDEX IF NOT EXISTS ix_agent_task_events_task_created
    ON agent_task_events (task_id, created_at);

CREATE TABLE IF NOT EXISTS agent_tool_calls (
    tool_call_id TEXT PRIMARY KEY,
    task_id TEXT NOT NULL,
    requesting_agent TEXT NOT NULL,
    tool_name TEXT NOT NULL,
    status TEXT NOT NULL CHECK (
        status IN ('planned', 'approved', 'blocked', 'running', 'succeeded', 'failed')
    ),
    risk_level TEXT NOT NULL DEFAULT 'read_only',
    requires_human_approval INTEGER NOT NULL DEFAULT 0 CHECK (requires_human_approval IN (0, 1)),
    requires_risk_governor INTEGER NOT NULL DEFAULT 0 CHECK (requires_risk_governor IN (0, 1)),
    arguments_json TEXT NOT NULL DEFAULT '{}' CHECK (json_valid(arguments_json)),
    result_json TEXT NULL CHECK (result_json IS NULL OR json_valid(result_json)),
    error_message TEXT NULL,
    started_at TEXT NULL,
    completed_at TEXT NULL,
    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (task_id) REFERENCES agent_tasks (task_id)
);

CREATE INDEX IF NOT EXISTS ix_agent_tool_calls_task_created
    ON agent_tool_calls (task_id, created_at);
CREATE INDEX IF NOT EXISTS ix_agent_tool_calls_agent_status
    ON agent_tool_calls (requesting_agent, status, created_at DESC);

CREATE TABLE IF NOT EXISTS agent_observations (
    observation_id TEXT PRIMARY KEY,
    task_id TEXT NOT NULL,
    agent_name TEXT NOT NULL,
    observation_type TEXT NOT NULL,
    summary TEXT NOT NULL,
    data_json TEXT NOT NULL DEFAULT '{}' CHECK (json_valid(data_json)),
    evidence_refs_json TEXT NOT NULL DEFAULT '[]' CHECK (json_valid(evidence_refs_json)),
    confidence REAL NOT NULL DEFAULT 1.0 CHECK (confidence >= 0.0 AND confidence <= 1.0),
    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (task_id) REFERENCES agent_tasks (task_id)
);

CREATE INDEX IF NOT EXISTS ix_agent_observations_task_created
    ON agent_observations (task_id, created_at);
CREATE INDEX IF NOT EXISTS ix_agent_observations_agent_created
    ON agent_observations (agent_name, created_at DESC);

CREATE TABLE IF NOT EXISTS agent_decisions (
    decision_id TEXT PRIMARY KEY,
    task_id TEXT NOT NULL,
    agent_name TEXT NOT NULL,
    decision_type TEXT NOT NULL CHECK (
        decision_type IN ('approve', 'reject', 'revise', 'escalate', 'block', 'report')
    ),
    decision TEXT NOT NULL,
    rationale TEXT NOT NULL,
    evidence_refs_json TEXT NOT NULL DEFAULT '[]' CHECK (json_valid(evidence_refs_json)),
    requires_board_approval INTEGER NOT NULL DEFAULT 0 CHECK (requires_board_approval IN (0, 1)),
    requires_risk_governor INTEGER NOT NULL DEFAULT 0 CHECK (requires_risk_governor IN (0, 1)),
    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (task_id) REFERENCES agent_tasks (task_id)
);

CREATE INDEX IF NOT EXISTS ix_agent_decisions_task_created
    ON agent_decisions (task_id, created_at);
CREATE INDEX IF NOT EXISTS ix_agent_decisions_agent_type_created
    ON agent_decisions (agent_name, decision_type, created_at DESC);

CREATE TABLE IF NOT EXISTS evidence_refs (
    evidence_id TEXT PRIMARY KEY,
    evidence_type TEXT NOT NULL,
    workflow_id TEXT NULL,
    task_id TEXT NULL,
    source_table TEXT NULL,
    source_ref_id TEXT NULL,
    uri TEXT NULL,
    content_hash TEXT NULL,
    summary TEXT NULL,
    source_agent TEXT NULL,
    metadata_json TEXT NOT NULL DEFAULT '{}' CHECK (json_valid(metadata_json)),
    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (workflow_id) REFERENCES core_workflows (workflow_id),
    FOREIGN KEY (task_id) REFERENCES agent_tasks (task_id)
);

CREATE INDEX IF NOT EXISTS ix_evidence_refs_workflow_created
    ON evidence_refs (workflow_id, created_at DESC);
CREATE INDEX IF NOT EXISTS ix_evidence_refs_task_created
    ON evidence_refs (task_id, created_at DESC);
CREATE INDEX IF NOT EXISTS ix_evidence_refs_source
    ON evidence_refs (source_table, source_ref_id);

CREATE TABLE IF NOT EXISTS research_reports (
    research_report_id TEXT PRIMARY KEY,
    workflow_id TEXT NULL,
    task_id TEXT NULL,
    research_question TEXT NOT NULL,
    report_json TEXT NOT NULL CHECK (json_valid(report_json)),
    confidence REAL NOT NULL DEFAULT 0.0 CHECK (confidence >= 0.0 AND confidence <= 1.0),
    evidence_refs_json TEXT NOT NULL DEFAULT '[]' CHECK (json_valid(evidence_refs_json)),
    created_by_agent TEXT NOT NULL,
    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (workflow_id) REFERENCES core_workflows (workflow_id),
    FOREIGN KEY (task_id) REFERENCES agent_tasks (task_id)
);

CREATE INDEX IF NOT EXISTS ix_research_reports_workflow_created
    ON research_reports (workflow_id, created_at DESC);

CREATE TABLE IF NOT EXISTS strategy_specs (
    strategy_spec_id TEXT PRIMARY KEY,
    workflow_id TEXT NULL,
    task_id TEXT NULL,
    strategy_id TEXT NULL,
    strategy_name TEXT NOT NULL,
    version TEXT NOT NULL,
    market TEXT NOT NULL,
    symbol TEXT NOT NULL,
    timeframe TEXT NOT NULL,
    spec_json TEXT NOT NULL CHECK (json_valid(spec_json)),
    evidence_refs_json TEXT NOT NULL DEFAULT '[]' CHECK (json_valid(evidence_refs_json)),
    created_by_agent TEXT NOT NULL,
    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (workflow_id) REFERENCES core_workflows (workflow_id),
    FOREIGN KEY (task_id) REFERENCES agent_tasks (task_id)
);

CREATE INDEX IF NOT EXISTS ix_strategy_specs_strategy_version
    ON strategy_specs (strategy_id, version);
CREATE INDEX IF NOT EXISTS ix_strategy_specs_symbol_timeframe
    ON strategy_specs (symbol, timeframe, created_at DESC);

CREATE TABLE IF NOT EXISTS strategy_reviews (
    strategy_review_id TEXT PRIMARY KEY,
    strategy_spec_id TEXT NULL,
    strategy_id TEXT NULL,
    reviewer_agent TEXT NOT NULL,
    verdict TEXT NOT NULL CHECK (verdict IN ('approve', 'revise', 'reject')),
    review_json TEXT NOT NULL CHECK (json_valid(review_json)),
    evidence_refs_json TEXT NOT NULL DEFAULT '[]' CHECK (json_valid(evidence_refs_json)),
    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (strategy_spec_id) REFERENCES strategy_specs (strategy_spec_id)
);

CREATE INDEX IF NOT EXISTS ix_strategy_reviews_strategy_created
    ON strategy_reviews (strategy_id, created_at DESC);
CREATE INDEX IF NOT EXISTS ix_strategy_reviews_verdict_created
    ON strategy_reviews (verdict, created_at DESC);

CREATE TABLE IF NOT EXISTS backtest_run_refs (
    backtest_run_ref_id TEXT PRIMARY KEY,
    workflow_id TEXT NULL,
    strategy_id TEXT NOT NULL,
    strategy_spec_id TEXT NULL,
    backtest_id TEXT NULL,
    result_ref TEXT NOT NULL,
    summary_json TEXT NOT NULL DEFAULT '{}' CHECK (json_valid(summary_json)),
    evidence_refs_json TEXT NOT NULL DEFAULT '[]' CHECK (json_valid(evidence_refs_json)),
    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (workflow_id) REFERENCES core_workflows (workflow_id),
    FOREIGN KEY (strategy_spec_id) REFERENCES strategy_specs (strategy_spec_id)
);

CREATE INDEX IF NOT EXISTS ix_backtest_run_refs_strategy_created
    ON backtest_run_refs (strategy_id, created_at DESC);

CREATE TABLE IF NOT EXISTS robustness_run_refs (
    robustness_run_ref_id TEXT PRIMARY KEY,
    workflow_id TEXT NULL,
    strategy_id TEXT NOT NULL,
    strategy_spec_id TEXT NULL,
    robustness_type TEXT NOT NULL,
    result_ref TEXT NOT NULL,
    summary_json TEXT NOT NULL DEFAULT '{}' CHECK (json_valid(summary_json)),
    evidence_refs_json TEXT NOT NULL DEFAULT '[]' CHECK (json_valid(evidence_refs_json)),
    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (workflow_id) REFERENCES core_workflows (workflow_id),
    FOREIGN KEY (strategy_spec_id) REFERENCES strategy_specs (strategy_spec_id)
);

CREATE INDEX IF NOT EXISTS ix_robustness_run_refs_strategy_created
    ON robustness_run_refs (strategy_id, created_at DESC);

CREATE TABLE IF NOT EXISTS risk_review_refs (
    risk_review_ref_id TEXT PRIMARY KEY,
    workflow_id TEXT NULL,
    strategy_id TEXT NULL,
    proposal_id TEXT NULL,
    reviewer_agent TEXT NOT NULL,
    verdict TEXT NOT NULL,
    review_ref TEXT NOT NULL,
    evidence_refs_json TEXT NOT NULL DEFAULT '[]' CHECK (json_valid(evidence_refs_json)),
    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (workflow_id) REFERENCES core_workflows (workflow_id)
);

CREATE INDEX IF NOT EXISTS ix_risk_review_refs_strategy_created
    ON risk_review_refs (strategy_id, created_at DESC);
CREATE INDEX IF NOT EXISTS ix_risk_review_refs_proposal_created
    ON risk_review_refs (proposal_id, created_at DESC);

CREATE TABLE IF NOT EXISTS paper_trade_refs (
    paper_trade_ref_id TEXT PRIMARY KEY,
    workflow_id TEXT NULL,
    strategy_id TEXT NOT NULL,
    proposal_id TEXT NULL,
    execution_ref TEXT NOT NULL,
    result_json TEXT NOT NULL DEFAULT '{}' CHECK (json_valid(result_json)),
    evidence_refs_json TEXT NOT NULL DEFAULT '[]' CHECK (json_valid(evidence_refs_json)),
    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (workflow_id) REFERENCES core_workflows (workflow_id)
);

CREATE INDEX IF NOT EXISTS ix_paper_trade_refs_strategy_created
    ON paper_trade_refs (strategy_id, created_at DESC);

CREATE TABLE IF NOT EXISTS live_trade_refs (
    live_trade_ref_id TEXT PRIMARY KEY,
    workflow_id TEXT NULL,
    strategy_id TEXT NOT NULL,
    proposal_id TEXT NULL,
    execution_intent_id TEXT NULL,
    execution_receipt_id TEXT NULL,
    broker_ref TEXT NULL,
    result_json TEXT NOT NULL DEFAULT '{}' CHECK (json_valid(result_json)),
    evidence_refs_json TEXT NOT NULL DEFAULT '[]' CHECK (json_valid(evidence_refs_json)),
    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (workflow_id) REFERENCES core_workflows (workflow_id),
    FOREIGN KEY (execution_intent_id) REFERENCES core_execution_intents (execution_intent_id),
    FOREIGN KEY (execution_receipt_id) REFERENCES core_execution_receipts (receipt_id)
);

CREATE INDEX IF NOT EXISTS ix_live_trade_refs_strategy_created
    ON live_trade_refs (strategy_id, created_at DESC);
CREATE INDEX IF NOT EXISTS ix_live_trade_refs_execution
    ON live_trade_refs (execution_intent_id, execution_receipt_id);

CREATE TABLE IF NOT EXISTS strategy_lifecycle (
    strategy_id TEXT PRIMARY KEY,
    current_state TEXT NOT NULL,
    lifecycle_version TEXT NOT NULL DEFAULT '1.0.0',
    active_strategy_version_id TEXT NULL,
    evidence_bundle_id TEXT NULL,
    updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    metadata_json TEXT NOT NULL DEFAULT '{}' CHECK (json_valid(metadata_json))
);

CREATE TABLE IF NOT EXISTS strategy_versions (
    strategy_version_id TEXT PRIMARY KEY,
    strategy_id TEXT NOT NULL,
    version TEXT NOT NULL,
    code_ref TEXT NULL,
    code_hash TEXT NULL,
    spec_ref TEXT NULL,
    parameter_hash TEXT NULL,
    created_by_agent TEXT NOT NULL,
    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    metadata_json TEXT NOT NULL DEFAULT '{}' CHECK (json_valid(metadata_json)),
    UNIQUE (strategy_id, version)
);

CREATE INDEX IF NOT EXISTS ix_strategy_versions_strategy_created
    ON strategy_versions (strategy_id, created_at DESC);

CREATE TABLE IF NOT EXISTS strategy_status_history (
    status_history_id INTEGER PRIMARY KEY AUTOINCREMENT,
    strategy_id TEXT NOT NULL,
    from_state TEXT NULL,
    to_state TEXT NOT NULL,
    reason TEXT NOT NULL,
    actor_type TEXT NOT NULL,
    actor_id TEXT NOT NULL,
    evidence_refs_json TEXT NOT NULL DEFAULT '[]' CHECK (json_valid(evidence_refs_json)),
    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS ix_strategy_status_history_strategy_created
    ON strategy_status_history (strategy_id, created_at DESC);

CREATE TABLE IF NOT EXISTS strategy_promotion_requests (
    promotion_request_id TEXT PRIMARY KEY,
    strategy_id TEXT NOT NULL,
    from_state TEXT NOT NULL,
    to_state TEXT NOT NULL,
    requested_by_agent TEXT NOT NULL,
    rationale TEXT NOT NULL,
    evidence_refs_json TEXT NOT NULL DEFAULT '[]' CHECK (json_valid(evidence_refs_json)),
    status TEXT NOT NULL CHECK (status IN ('pending', 'approved', 'rejected', 'cancelled')),
    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    decided_at TEXT NULL,
    decision_ref TEXT NULL
);

CREATE INDEX IF NOT EXISTS ix_strategy_promotion_requests_status_created
    ON strategy_promotion_requests (status, created_at DESC);
CREATE INDEX IF NOT EXISTS ix_strategy_promotion_requests_strategy_created
    ON strategy_promotion_requests (strategy_id, created_at DESC);

CREATE TABLE IF NOT EXISTS strategy_retirement_records (
    retirement_id TEXT PRIMARY KEY,
    strategy_id TEXT NOT NULL,
    retired_from_state TEXT NOT NULL,
    reason TEXT NOT NULL,
    retired_by_actor_type TEXT NOT NULL,
    retired_by_actor_id TEXT NOT NULL,
    evidence_refs_json TEXT NOT NULL DEFAULT '[]' CHECK (json_valid(evidence_refs_json)),
    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS ix_strategy_retirement_records_strategy_created
    ON strategy_retirement_records (strategy_id, created_at DESC);

CREATE VIEW IF NOT EXISTS trade_proposals AS
SELECT
    proposal_id,
    workflow_id,
    hypothesis_id AS strategy_id,
    symbol,
    direction AS side,
    candidate_price_logic_json AS entry_logic_json,
    proposed_size_json AS requested_size_json,
    operating_envelope_json,
    readiness_state,
    state,
    created_at,
    updated_at
FROM core_trade_proposals;

CREATE VIEW IF NOT EXISTS risk_approvals AS
SELECT
    risk_decision_id AS approval_id,
    proposal_id,
    workflow_id,
    approval_token,
    freshness_expiry AS expires_at,
    decision,
    rationale_text AS reasons,
    created_at
FROM risk_risk_decisions
WHERE decision IN ('APPROVE', 'APPROVE_WITH_LIMITS');

CREATE VIEW IF NOT EXISTS risk_rejections AS
SELECT
    risk_decision_id AS rejection_id,
    proposal_id,
    workflow_id,
    decision,
    rationale_text AS reasons,
    created_at
FROM risk_risk_decisions
WHERE decision IN ('REJECT', 'FORCE_EXIT');

CREATE VIEW IF NOT EXISTS execution_requests AS
SELECT
    execution_intent_id AS execution_request_id,
    workflow_id,
    proposal_id,
    risk_decision_id AS risk_approval_id,
    action_type,
    symbol,
    side,
    order_type,
    size_json,
    price_params_json,
    sl_tp_params_json,
    status,
    expiry_at,
    created_at,
    updated_at
FROM core_execution_intents;

CREATE VIEW IF NOT EXISTS execution_results AS
SELECT
    receipt_id AS execution_result_id,
    execution_intent_id AS execution_request_id,
    broker,
    broker_order_id,
    broker_deal_id,
    receipt_status AS status,
    fill_price,
    fill_qty,
    spread_points,
    slippage_points,
    broker_message,
    received_at AS created_at
FROM core_execution_receipts;

CREATE VIEW IF NOT EXISTS execution_audit AS
SELECT
    CAST(send_attempt_id AS TEXT) AS audit_id,
    execution_intent_id AS execution_request_id,
    'send_attempt' AS audit_type,
    transport_status AS status,
    submitted_payload_hash AS input_hash,
    broker_request_ref AS output_ref,
    error_message,
    started_at AS created_at,
    finished_at
FROM core_execution_send_attempts
UNION ALL
SELECT
    receipt_id AS audit_id,
    execution_intent_id AS execution_request_id,
    'receipt' AS audit_type,
    receipt_status AS status,
    raw_receipt_ref AS input_hash,
    broker_order_id AS output_ref,
    broker_message AS error_message,
    received_at AS created_at,
    received_at AS finished_at
FROM core_execution_receipts;

CREATE TABLE IF NOT EXISTS audit_log (
    audit_id TEXT PRIMARY KEY,
    actor_name TEXT NOT NULL,
    agent_name TEXT NULL,
    tool_name TEXT NULL,
    action_type TEXT NOT NULL,
    target_type TEXT NULL,
    target_ref_id TEXT NULL,
    input_hash TEXT NOT NULL,
    output_hash TEXT NULL,
    evidence_refs_json TEXT NOT NULL DEFAULT '[]' CHECK (json_valid(evidence_refs_json)),
    request_id TEXT NULL,
    parent_task_id TEXT NULL,
    workflow_id TEXT NULL,
    metadata_json TEXT NOT NULL DEFAULT '{}' CHECK (json_valid(metadata_json)),
    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (parent_task_id) REFERENCES agent_tasks (task_id),
    FOREIGN KEY (workflow_id) REFERENCES core_workflows (workflow_id)
);

CREATE INDEX IF NOT EXISTS ix_audit_log_workflow_created
    ON audit_log (workflow_id, created_at);
CREATE INDEX IF NOT EXISTS ix_audit_log_actor_created
    ON audit_log (actor_name, created_at DESC);
CREATE INDEX IF NOT EXISTS ix_audit_log_target
    ON audit_log (target_type, target_ref_id);
CREATE INDEX IF NOT EXISTS ix_audit_log_request
    ON audit_log (request_id);

CREATE TRIGGER IF NOT EXISTS trg_audit_log_no_update
BEFORE UPDATE ON audit_log
BEGIN
    SELECT RAISE(ABORT, 'audit_log is append-only');
END;

CREATE TRIGGER IF NOT EXISTS trg_audit_log_no_delete
BEFORE DELETE ON audit_log
BEGIN
    SELECT RAISE(ABORT, 'audit_log is append-only');
END;
