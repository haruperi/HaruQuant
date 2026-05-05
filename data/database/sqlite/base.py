"""Base database connection and error handling classes."""

import sqlite3
from pathlib import Path
from typing import Optional

from haruquant.utils import logger


class UserAlreadyExistsError(Exception):
    """Raised when attempting to create a user that already exists."""


class DatabaseBase:
    """Base class for database connection management."""

    def __init__(self, db_path: Optional[str] = None) -> None:
        """Initialize with optional database path."""
        if db_path:
            self.db_path = db_path
        else:
            self.db_path = self._get_default_db_path()

        # Enable WAL mode for better concurrent access.
        try:
            conn = sqlite3.connect(self.db_path)
            conn.execute("PRAGMA journal_mode=WAL")
            conn.close()
            logger.debug("Database exists. WAL mode enabled successfully.")
        except Exception:
            logger.debug("Database doesn't exist yet or failed to enable WAL mode.")

    def _get_default_db_path(self) -> str:
        # __file__ is data/database/sqlite/base.py.
        # Walk back to the repository root before appending data/database.
        project_root = Path(__file__).resolve().parents[3]
        db_dir = project_root / "data" / "database"
        db_dir.mkdir(parents=True, exist_ok=True)
        return str(db_dir / "haruquant.db")
