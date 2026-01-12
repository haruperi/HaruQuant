"""Compatibility wrapper for legacy DatabaseManager import."""

from . import SQLiteDatabase, UserAlreadyExistsError

DatabaseManager = SQLiteDatabase

__all__ = ["DatabaseManager", "UserAlreadyExistsError"]
