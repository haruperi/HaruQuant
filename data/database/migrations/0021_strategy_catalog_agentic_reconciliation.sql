CREATE TABLE IF NOT EXISTS strategy_catalog_reconciliation_audit (
    audit_id INTEGER PRIMARY KEY AUTOINCREMENT,
    checked_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    applied_by TEXT NOT NULL DEFAULT 'migration',
    notes TEXT NOT NULL DEFAULT 'Conditional legacy strategies column checks run through SchemaManager/backfill tooling.'
);

