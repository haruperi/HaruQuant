CREATE TABLE IF NOT EXISTS gov_kill_switch_events (
    kill_event_id INTEGER PRIMARY KEY AUTOINCREMENT,
    previous_state TEXT NOT NULL,
    new_state TEXT NOT NULL,
    trigger_type TEXT NOT NULL,
    reason_code TEXT NOT NULL,
    actor_type TEXT NOT NULL,
    actor_id TEXT NOT NULL,
    workflow_id TEXT NULL,
    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    metadata_json TEXT NOT NULL DEFAULT '{}' CHECK (json_valid(metadata_json)),
    FOREIGN KEY (workflow_id) REFERENCES core_workflows (workflow_id)
);

CREATE INDEX IF NOT EXISTS ix_kill_switch_events_new_state_created
    ON gov_kill_switch_events (new_state, created_at DESC);
CREATE INDEX IF NOT EXISTS ix_kill_switch_events_created
    ON gov_kill_switch_events (created_at DESC);

CREATE TABLE IF NOT EXISTS gov_approvals (
    approval_id TEXT PRIMARY KEY,
    action_type TEXT NOT NULL,
    target_ref_type TEXT NOT NULL,
    target_ref_id TEXT NOT NULL,
    required_count INTEGER NOT NULL,
    state TEXT NOT NULL,
    compliance_profile_id TEXT NULL,
    expires_at TEXT NULL,
    created_by_actor_type TEXT NOT NULL,
    created_by_actor_id TEXT NOT NULL,
    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    decided_at TEXT NULL,
    metadata_json TEXT NOT NULL DEFAULT '{}' CHECK (json_valid(metadata_json))
);

CREATE INDEX IF NOT EXISTS ix_approvals_state_created
    ON gov_approvals (state, created_at DESC);
CREATE INDEX IF NOT EXISTS ix_approvals_target
    ON gov_approvals (target_ref_type, target_ref_id);
CREATE INDEX IF NOT EXISTS ix_approvals_expires
    ON gov_approvals (expires_at);

CREATE TABLE IF NOT EXISTS gov_approval_votes (
    vote_id INTEGER PRIMARY KEY AUTOINCREMENT,
    approval_id TEXT NOT NULL,
    approver_role TEXT NOT NULL,
    approver_id TEXT NOT NULL,
    decision TEXT NOT NULL,
    reason_code TEXT NULL,
    rationale TEXT NULL,
    voted_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (approval_id) REFERENCES gov_approvals (approval_id),
    UNIQUE (approval_id, approver_id)
);

CREATE INDEX IF NOT EXISTS ix_approval_votes_approval_voted
    ON gov_approval_votes (approval_id, voted_at);
CREATE INDEX IF NOT EXISTS ix_approval_votes_approver_voted
    ON gov_approval_votes (approver_id, voted_at DESC);

CREATE TABLE IF NOT EXISTS gov_override_requests (
    override_request_id TEXT PRIMARY KEY,
    original_decision_ref TEXT NOT NULL,
    original_action_ref TEXT NOT NULL,
    requested_action_json TEXT NOT NULL CHECK (json_valid(requested_action_json)),
    reason_code TEXT NOT NULL,
    rationale TEXT NOT NULL,
    requested_expiry TEXT NULL,
    required_roles_json TEXT NOT NULL DEFAULT '[]' CHECK (json_valid(required_roles_json)),
    state TEXT NOT NULL,
    created_by_actor_id TEXT NOT NULL,
    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS ix_override_requests_state_created
    ON gov_override_requests (state, created_at DESC);

CREATE TABLE IF NOT EXISTS gov_override_decisions (
    override_decision_id TEXT PRIMARY KEY,
    override_request_id TEXT NOT NULL,
    decision TEXT NOT NULL,
    effective_until TEXT NULL,
    downstream_execution_ref TEXT NULL,
    audit_ref TEXT NULL,
    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (override_request_id) REFERENCES gov_override_requests (override_request_id)
);

CREATE INDEX IF NOT EXISTS ix_override_decisions_request
    ON gov_override_decisions (override_request_id);
CREATE INDEX IF NOT EXISTS ix_override_decisions_decision_created
    ON gov_override_decisions (decision, created_at DESC);

CREATE TABLE IF NOT EXISTS gov_policies (
    policy_version_id TEXT PRIMARY KEY,
    policy_type TEXT NOT NULL,
    version TEXT NOT NULL,
    content_hash TEXT NOT NULL,
    content_ref TEXT NULL,
    effective_from TEXT NOT NULL,
    effective_to TEXT NULL,
    status TEXT NOT NULL,
    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    created_by TEXT NOT NULL,
    UNIQUE (policy_type, version)
);

CREATE INDEX IF NOT EXISTS ix_policies_type_status_effective
    ON gov_policies (policy_type, status, effective_from DESC);
CREATE INDEX IF NOT EXISTS ix_policies_effective_window
    ON gov_policies (effective_from, effective_to);

CREATE TABLE IF NOT EXISTS gov_compliance_profiles (
    compliance_profile_id TEXT PRIMARY KEY,
    name TEXT NOT NULL,
    version TEXT NOT NULL,
    profile_json TEXT NOT NULL CHECK (json_valid(profile_json)),
    active_flag INTEGER NOT NULL DEFAULT 0 CHECK (active_flag IN (0, 1)),
    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    UNIQUE (name, version)
);

CREATE INDEX IF NOT EXISTS ix_compliance_profiles_name_active
    ON gov_compliance_profiles (name, active_flag);

CREATE TABLE IF NOT EXISTS gov_strategy_registry (
    strategy_id TEXT PRIMARY KEY,
    strategy_name TEXT NOT NULL,
    strategy_family TEXT NOT NULL,
    current_lifecycle_state TEXT NOT NULL,
    code_hash TEXT NOT NULL,
    parameter_hash TEXT NOT NULL,
    owner_id TEXT NULL,
    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS ix_strategy_registry_state_updated
    ON gov_strategy_registry (current_lifecycle_state, updated_at DESC);
CREATE INDEX IF NOT EXISTS ix_strategy_registry_family_updated
    ON gov_strategy_registry (strategy_family, updated_at DESC);

CREATE TABLE IF NOT EXISTS gov_strategy_promotions (
    promotion_id TEXT PRIMARY KEY,
    strategy_id TEXT NOT NULL,
    from_state TEXT NOT NULL,
    to_state TEXT NOT NULL,
    evidence_bundle_id TEXT NOT NULL,
    approver_1_id TEXT NOT NULL,
    approver_2_id TEXT NULL,
    effective_at TEXT NOT NULL,
    rationale TEXT NULL,
    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (strategy_id) REFERENCES gov_strategy_registry (strategy_id)
);

CREATE INDEX IF NOT EXISTS ix_strategy_promotions_strategy_effective
    ON gov_strategy_promotions (strategy_id, effective_at DESC);
CREATE INDEX IF NOT EXISTS ix_strategy_promotions_to_state_effective
    ON gov_strategy_promotions (to_state, effective_at DESC);
