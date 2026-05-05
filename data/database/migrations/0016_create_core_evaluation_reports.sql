CREATE TABLE IF NOT EXISTS core_evaluation_reports (
    evaluation_id TEXT PRIMARY KEY,
    workflow_id TEXT NULL,
    target_type TEXT NOT NULL,
    target_ref TEXT NOT NULL,
    rubric_name TEXT NOT NULL,
    rubric_scores_json TEXT NOT NULL CHECK (json_valid(rubric_scores_json)),
    overall_score REAL NOT NULL,
    verdict TEXT NOT NULL,
    issues_json TEXT NOT NULL DEFAULT '[]' CHECK (json_valid(issues_json)),
    improvement_actions_json TEXT NOT NULL DEFAULT '[]' CHECK (json_valid(improvement_actions_json)),
    evaluator_identity TEXT NOT NULL,
    evaluation_model_id TEXT NULL,
    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (workflow_id) REFERENCES core_workflows (workflow_id)
);

CREATE INDEX IF NOT EXISTS ix_evaluation_reports_workflow_created
    ON core_evaluation_reports (workflow_id, created_at DESC);

CREATE INDEX IF NOT EXISTS ix_evaluation_reports_target
    ON core_evaluation_reports (target_type, target_ref);

CREATE INDEX IF NOT EXISTS ix_evaluation_reports_rubric_created
    ON core_evaluation_reports (rubric_name, created_at DESC);
