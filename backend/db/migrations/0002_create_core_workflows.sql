CREATE TABLE IF NOT EXISTS core_workflows (
    workflow_id TEXT PRIMARY KEY,
    workflow_type TEXT NOT NULL,
    environment TEXT NOT NULL CHECK (environment IN ('dev', 'test', 'paper', 'staging', 'prod')),
    operating_mode TEXT NOT NULL CHECK (
        operating_mode IN ('MODE-000', 'MODE-001', 'MODE-002', 'MODE-003', 'MODE-004')
    ),
    state TEXT NOT NULL CHECK (
        state IN (
            'CREATED',
            'REASONING',
            'PLANNING',
            'ACTING',
            'OBSERVING',
            'EVALUATING',
            'REFINING',
            'COMPLETED',
            'FAILED',
            'CANCELLED',
            'BLOCKED_BY_RISK',
            'BLOCKED_BY_POLICY',
            'TIMED_OUT',
            'RECONCILING'
        )
    ),
    objective TEXT NOT NULL,
    scope_json TEXT NOT NULL DEFAULT '{}' CHECK (json_valid(scope_json)),
    initiator_type TEXT NOT NULL,
    initiator_id TEXT NOT NULL,
    timeout_policy_json TEXT NOT NULL DEFAULT '{}' CHECK (json_valid(timeout_policy_json)),
    stop_conditions_json TEXT NOT NULL DEFAULT '[]' CHECK (json_valid(stop_conditions_json)),
    current_step_id TEXT NULL,
    version_no INTEGER NOT NULL DEFAULT 1,
    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    completed_at TEXT NULL,
    terminal_reason TEXT NULL
);

CREATE INDEX IF NOT EXISTS ix_core_workflows_state_updated
    ON core_workflows (state, updated_at DESC);

CREATE INDEX IF NOT EXISTS ix_core_workflows_type_created
    ON core_workflows (workflow_type, created_at DESC);

CREATE INDEX IF NOT EXISTS ix_core_workflows_env_mode_created
    ON core_workflows (environment, operating_mode, created_at DESC);
