"""Base database connection and error handling classes."""

import os
import sqlite3
from typing import Optional

from apps.utils.logger import logger


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

        # Enable WAL mode for better concurrent access
        try:
            conn = sqlite3.connect(self.db_path)
            conn.execute("PRAGMA journal_mode=WAL")
            conn.close()
            logger.debug("Database exists. WAL mode enabled successfully.")
        except Exception:
            # Only log error if file really doesn't exist or permissions fail, but maybe debug too
            # if we expect it to fail on first run before init.
            # But let's keep error as is or debug?
            # Given it logs "Database doesn't exist yet", it might be intended.
            # I will just change the success log to debug.
            logger.debug("Database doesn't exist yet or failed to enable WAL mode.")

    def _get_default_db_path(self) -> str:
        # Get project root (assuming apps/sqlite structure)
        current_dir = os.path.dirname(os.path.abspath(__file__))
        project_root = os.path.abspath(os.path.join(current_dir, "../../"))
        db_dir = os.path.join(project_root, "backend", "data", "database")
        # Ensure directory exists
        os.makedirs(db_dir, exist_ok=True)
        return os.path.join(db_dir, "haruquant.db")

