from __future__ import annotations

import sqlite3

from backend.data.database import apply_pending_migrations, default_migrations_dir


def test_ai_chat_conversation_tables_are_created(tmp_path) -> None:
    database_path = tmp_path / "agentic.db"

    apply_pending_migrations(database_path, default_migrations_dir())

    with sqlite3.connect(database_path) as connection:
        table_names = {
            row[0]
            for row in connection.execute(
                """
                SELECT name
                FROM sqlite_master
                WHERE type = 'table'
                """
            ).fetchall()
        }

    assert "ai_chat_threads" in table_names
    assert "ai_chat_messages" in table_names
    assert "ai_chat_memory_summaries" in table_names
    assert "ai_chat_pinned_facts" in table_names
