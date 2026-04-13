"""Episodic memory — persistent store of past decisions and outcomes."""

from __future__ import annotations

import json
import os
import sqlite3

from .model import EpisodicMemory


class EpisodicMemoryStore:
    """SQLite-backed episodic memory store.

    Records past decisions, their outcomes, and lessons learned.
    Queryable by agent, outcome, or context similarity.
    """

    def __init__(self, db_path: str = "backend/data/database/sqlite/episodic_memory.db") -> None:
        self._db_path = db_path
        self._ensure_db()

    def _ensure_db(self) -> None:
        os.makedirs(os.path.dirname(self._db_path) if os.path.dirname(self._db_path) else ".", exist_ok=True)
        conn = sqlite3.connect(self._db_path)
        try:
            conn.execute("""
                CREATE TABLE IF NOT EXISTS episodic_memory (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    memory_id TEXT NOT NULL UNIQUE,
                    workflow_id TEXT NOT NULL,
                    agent_name TEXT NOT NULL,
                    goal TEXT NOT NULL,
                    decision TEXT NOT NULL,
                    outcome TEXT NOT NULL,
                    lesson TEXT,
                    metadata TEXT DEFAULT '{}',
                    created_at TEXT NOT NULL
                )
            """)
            conn.commit()
        finally:
            conn.close()

    def record(
        self,
        workflow_id: str,
        agent_name: str,
        goal: str,
        decision: str,
        outcome: str,
        lesson: str | None = None,
        metadata: dict | None = None,
    ) -> str:
        """Record an episodic memory. Returns memory_id."""
        import uuid
        from datetime import datetime, timezone
        memory_id = str(uuid.uuid4())
        conn = sqlite3.connect(self._db_path)
        try:
            conn.execute(
                """INSERT OR REPLACE INTO episodic_memory
                   (memory_id, workflow_id, agent_name, goal, decision,
                    outcome, lesson, metadata, created_at)
                   VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                (
                    memory_id, workflow_id, agent_name, goal, decision,
                    outcome, lesson, json.dumps(metadata or {}),
                    datetime.now(timezone.utc).isoformat(),
                ),
            )
            conn.commit()
        finally:
            conn.close()
        return memory_id

    def search(self, agent_name: str | None = None, outcome: str | None = None,
               limit: int = 10) -> list[EpisodicMemory]:
        """Search past decisions with optional filters."""
        conn = sqlite3.connect(self._db_path)
        conn.row_factory = sqlite3.Row
        try:
            query = "SELECT * FROM episodic_memory WHERE 1=1"
            params: list = []
            if agent_name:
                query += " AND agent_name = ?"
                params.append(agent_name)
            if outcome:
                query += " AND outcome = ?"
                params.append(outcome)
            query += " ORDER BY created_at DESC LIMIT ?"
            params.append(limit)

            rows = conn.execute(query, params).fetchall()
        finally:
            conn.close()

        return [self._row_to_memory(dict(row)) for row in rows]

    def get_lessons(self, agent_name: str | None = None,
                    outcome_filter: str = "failure") -> list[str]:
        """Get lessons learned from past experiences."""
        memories = self.search(agent_name=agent_name, outcome=outcome_filter)
        return [m.lesson for m in memories if m.lesson]

    def _row_to_memory(self, row: dict) -> EpisodicMemory:
        from datetime import datetime
        return EpisodicMemory(
            memory_id=row["memory_id"],
            workflow_id=row["workflow_id"],
            agent_name=row["agent_name"],
            goal=row["goal"],
            decision=row["decision"],
            outcome=row["outcome"],
            lesson=row["lesson"],
            metadata=json.loads(row["metadata"]),
            created_at=datetime.fromisoformat(row["created_at"]),
        )
