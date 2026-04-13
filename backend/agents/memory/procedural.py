"""Procedural memory — learned patterns and tool usage preferences."""

from __future__ import annotations

import json
import os
import sqlite3

from .model import ProceduralMemory


class ProceduralMemoryStore:
    """SQLite-backed procedural memory store.

    Stores learned workflow patterns, tool usage preferences,
    and procedural shortcuts with success rate tracking.
    """

    def __init__(self, db_path: str = "backend/data/database/sqlite/procedural_memory.db") -> None:
        self._db_path = db_path
        self._ensure_db()

    def _ensure_db(self) -> None:
        os.makedirs(os.path.dirname(self._db_path) if os.path.dirname(self._db_path) else ".", exist_ok=True)
        conn = sqlite3.connect(self._db_path)
        try:
            conn.execute("""
                CREATE TABLE IF NOT EXISTS procedural_memory (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    memory_id TEXT NOT NULL UNIQUE,
                    pattern_name TEXT NOT NULL,
                    description TEXT NOT NULL,
                    steps TEXT DEFAULT '[]',
                    success_rate REAL DEFAULT 0.0,
                    usage_count INTEGER DEFAULT 0,
                    last_used TEXT NOT NULL
                )
            """)
            conn.commit()
        finally:
            conn.close()

    def store(
        self,
        pattern_name: str,
        description: str,
        steps: list[str] | None = None,
    ) -> str:
        """Store a procedural memory pattern. Returns memory_id."""
        import uuid
        from datetime import datetime, timezone
        memory_id = str(uuid.uuid4())
        conn = sqlite3.connect(self._db_path)
        try:
            conn.execute(
                """INSERT OR REPLACE INTO procedural_memory
                   (memory_id, pattern_name, description, steps,
                    success_rate, usage_count, last_used)
                   VALUES (?, ?, ?, ?, 0.0, 0, ?)""",
                (
                    memory_id, pattern_name, description,
                    json.dumps(steps or []),
                    datetime.now(timezone.utc).isoformat(),
                ),
            )
            conn.commit()
        finally:
            conn.close()
        return memory_id

    def record_usage(self, memory_id: str, success: bool) -> None:
        """Record a usage event, updating success rate."""
        conn = sqlite3.connect(self._db_path)
        try:
            row = conn.execute(
                "SELECT usage_count, success_rate FROM procedural_memory WHERE memory_id = ?",
                (memory_id,),
            ).fetchone()
            if row:
                old_count, old_rate = row
                new_count = old_count + 1
                new_rate = (old_rate * old_count + (1.0 if success else 0.0)) / new_count
                from datetime import datetime, timezone
                conn.execute(
                    "UPDATE procedural_memory SET usage_count = ?, success_rate = ?, last_used = ? WHERE memory_id = ?",
                    (new_count, new_rate, datetime.now(timezone.utc).isoformat(), memory_id),
                )
                conn.commit()
        finally:
            conn.close()

    def get_patterns(self, min_usage: int = 0, min_success_rate: float = 0.0) -> list[ProceduralMemory]:
        """Get stored patterns with optional filtering."""
        conn = sqlite3.connect(self._db_path)
        conn.row_factory = sqlite3.Row
        try:
            rows = conn.execute(
                "SELECT * FROM procedural_memory WHERE usage_count >= ? AND success_rate >= ?",
                (min_usage, min_success_rate),
            ).fetchall()
        finally:
            conn.close()
        return [self._row_to_memory(dict(row)) for row in rows]

    def _row_to_memory(self, row: dict) -> ProceduralMemory:
        from datetime import datetime
        return ProceduralMemory(
            memory_id=row["memory_id"],
            pattern_name=row["pattern_name"],
            description=row["description"],
            steps=json.loads(row["steps"]),
            success_rate=row["success_rate"],
            usage_count=row["usage_count"],
            last_used=datetime.fromisoformat(row["last_used"]),
        )
