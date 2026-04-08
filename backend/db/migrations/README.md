# Migration Framework Baseline

This directory contains the initial database migration framework for the agentic backend.

Current baseline:
- SQLite-first migration runner
- ordered `.sql` migration files
- internal `_schema_migrations` history table
- additive, file-based migration application
- logical namespace bootstrap for single-schema SQLite deployments

This keeps the first storage step compatible with the current `sqlite3` runtime while the new backend database slice is still being introduced.

Current namespace mapping:
- `core` -> `main`
- `risk` -> `main`
- `gov` -> `main`
- `audit` -> `main`
- `research` -> `main`
- `ref` -> `main`

Migration file naming:
- `0001_description.sql`
- `0002_add_example_table.sql`

The runner applies pending files in lexical order and records:
- `version`
- `name`
- `checksum`
- `applied_at`

This is intentionally minimal. If the backend later standardizes on SQLAlchemy, this directory can be replaced or bridged to Alembic without changing the higher-level migration workflow.
