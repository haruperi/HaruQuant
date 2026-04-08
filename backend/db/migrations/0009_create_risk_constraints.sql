CREATE TABLE IF NOT EXISTS risk_risk_constraints (
    constraint_id INTEGER PRIMARY KEY AUTOINCREMENT,
    risk_decision_id TEXT NOT NULL,
    constraint_type TEXT NOT NULL,
    constraint_value_json TEXT NOT NULL CHECK (json_valid(constraint_value_json)),
    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (risk_decision_id) REFERENCES risk_risk_decisions (risk_decision_id)
);

CREATE INDEX IF NOT EXISTS ix_risk_constraints_decision
    ON risk_risk_constraints (risk_decision_id);

CREATE INDEX IF NOT EXISTS ix_risk_constraints_type
    ON risk_risk_constraints (constraint_type);
