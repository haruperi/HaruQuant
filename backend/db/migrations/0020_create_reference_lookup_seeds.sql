CREATE TABLE IF NOT EXISTS ref_workflow_states (
    code TEXT PRIMARY KEY,
    sort_order INTEGER NOT NULL
);

CREATE TABLE IF NOT EXISTS ref_proposal_states (
    code TEXT PRIMARY KEY,
    sort_order INTEGER NOT NULL
);

CREATE TABLE IF NOT EXISTS ref_decision_types (
    code TEXT PRIMARY KEY,
    sort_order INTEGER NOT NULL
);

CREATE TABLE IF NOT EXISTS ref_approval_states (
    code TEXT PRIMARY KEY,
    sort_order INTEGER NOT NULL
);

CREATE TABLE IF NOT EXISTS ref_incident_states (
    code TEXT PRIMARY KEY,
    sort_order INTEGER NOT NULL
);

CREATE TABLE IF NOT EXISTS ref_kill_switch_states (
    code TEXT PRIMARY KEY,
    sort_order INTEGER NOT NULL
);

CREATE TABLE IF NOT EXISTS ref_operating_modes (
    code TEXT PRIMARY KEY,
    sort_order INTEGER NOT NULL,
    label TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS ref_strategy_lifecycle_states (
    code TEXT PRIMARY KEY,
    sort_order INTEGER NOT NULL
);

CREATE TABLE IF NOT EXISTS ref_severity_levels (
    code TEXT PRIMARY KEY,
    sort_order INTEGER NOT NULL
);

INSERT OR IGNORE INTO ref_workflow_states (code, sort_order) VALUES
    ('CREATED', 1),
    ('REASONING', 2),
    ('PLANNING', 3),
    ('ACTING', 4),
    ('OBSERVING', 5),
    ('EVALUATING', 6),
    ('REFINING', 7),
    ('COMPLETED', 8),
    ('FAILED', 9),
    ('CANCELLED', 10),
    ('BLOCKED_BY_RISK', 11),
    ('BLOCKED_BY_POLICY', 12),
    ('TIMED_OUT', 13),
    ('RECONCILING', 14);

INSERT OR IGNORE INTO ref_proposal_states (code, sort_order) VALUES
    ('DRAFT', 1),
    ('EVIDENCE_PENDING', 2),
    ('READY_FOR_RISK', 3),
    ('APPROVED', 4),
    ('APPROVED_WITH_LIMITS', 5),
    ('REJECTED', 6),
    ('EXPIRED', 7),
    ('EXECUTION_PENDING', 8),
    ('SENT', 9),
    ('ACKNOWLEDGED', 10),
    ('PARTIALLY_FILLED', 11),
    ('FILLED', 12),
    ('EXECUTION_FAILED', 13),
    ('CLOSED', 14);

INSERT OR IGNORE INTO ref_decision_types (code, sort_order) VALUES
    ('APPROVE', 1),
    ('APPROVE_WITH_LIMITS', 2),
    ('REJECT', 3),
    ('FORCE_EXIT', 4);

INSERT OR IGNORE INTO ref_approval_states (code, sort_order) VALUES
    ('PENDING', 1),
    ('PARTIALLY_APPROVED', 2),
    ('APPROVED', 3),
    ('REJECTED', 4),
    ('EXPIRED', 5);

INSERT OR IGNORE INTO ref_incident_states (code, sort_order) VALUES
    ('DETECTED', 1),
    ('TRIAGED', 2),
    ('ACTIVE', 3),
    ('CONTAINED', 4),
    ('RESOLVED', 5),
    ('POSTMORTEM_PENDING', 6),
    ('CLOSED', 7);

INSERT OR IGNORE INTO ref_kill_switch_states (code, sort_order) VALUES
    ('ARMED', 1),
    ('SOFT_TRIGGERED', 2),
    ('HARD_TRIGGERED', 3),
    ('RECOVERY_PENDING', 4),
    ('RECOVERY_APPROVED', 5);

INSERT OR IGNORE INTO ref_operating_modes (code, sort_order, label) VALUES
    ('MODE-000', 1, 'Research Only'),
    ('MODE-001', 2, 'Advisory'),
    ('MODE-002', 3, 'Paper Execution'),
    ('MODE-003', 4, 'Human-Approved Live'),
    ('MODE-004', 5, 'Bounded Autonomous Live');

INSERT OR IGNORE INTO ref_strategy_lifecycle_states (code, sort_order) VALUES
    ('RESEARCH', 1),
    ('BACKTEST_QUALIFIED', 2),
    ('ROBUSTNESS_QUALIFIED', 3),
    ('PAPER_APPROVED', 4),
    ('LIVE_LIMITED', 5),
    ('LIVE_PRODUCTION', 6),
    ('SUSPENDED', 7),
    ('RETIRED', 8);

INSERT OR IGNORE INTO ref_severity_levels (code, sort_order) VALUES
    ('info', 1),
    ('warning', 2),
    ('critical', 3);
