CREATE TABLE IF NOT EXISTS _logical_namespaces (
    namespace_name TEXT PRIMARY KEY,
    physical_schema TEXT NOT NULL,
    naming_mode TEXT NOT NULL,
    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
);

INSERT OR IGNORE INTO _logical_namespaces (namespace_name, physical_schema, naming_mode)
VALUES
    ('core', 'main', 'single-schema'),
    ('risk', 'main', 'single-schema'),
    ('gov', 'main', 'single-schema'),
    ('audit', 'main', 'single-schema'),
    ('research', 'main', 'single-schema'),
    ('ref', 'main', 'single-schema');
