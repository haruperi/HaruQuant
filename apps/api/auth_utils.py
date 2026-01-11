"""Authentication utility functions."""

import json
import secrets
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any, Dict, Optional, cast

from apps.sqlite.database_operations import DatabaseManager
from apps.utils.security import verify_password

# File-based token storage for persistence across server reloads
TOKEN_STORAGE_FILE = Path("data/tokens.json")


def _load_tokens() -> Dict[str, Dict[str, Any]]:
    """Load tokens from file."""
    if not TOKEN_STORAGE_FILE.exists():
        return {}

    try:
        with open(TOKEN_STORAGE_FILE, "r") as f:
            tokens = cast(Dict[str, Dict[str, Any]], json.load(f))
            # Convert string dates back to datetime
            for token_data in tokens.values():
                token_data["created_at"] = datetime.fromisoformat(
                    token_data["created_at"]
                )
                token_data["expires_at"] = datetime.fromisoformat(
                    token_data["expires_at"]
                )
            return tokens
    except Exception:
        return {}


def _save_tokens(tokens: dict) -> None:
    """Save tokens to file."""
    # Ensure directory exists
    TOKEN_STORAGE_FILE.parent.mkdir(parents=True, exist_ok=True)

    # Convert datetime to string for JSON serialization
    serializable_tokens = {}
    for token, data in tokens.items():
        serializable_tokens[token] = {
            "user_id": data["user_id"],
            "created_at": data["created_at"].isoformat(),
            "expires_at": data["expires_at"].isoformat(),
        }

    with open(TOKEN_STORAGE_FILE, "w") as f:
        json.dump(serializable_tokens, f, indent=2)


def generate_token(user_id: int) -> str:
    """
    Generate a secure random token for user authentication.

    Token expires after 24 hours (extended for development).

    Args:
        user_id: The user's ID

    Returns:
        A secure random token
    """
    token = secrets.token_urlsafe(32)
    tokens = _load_tokens()
    tokens[token] = {
        "user_id": user_id,
        "created_at": datetime.now(),
        "expires_at": datetime.now() + timedelta(hours=24),  # Extended to 24 hours
    }
    _save_tokens(tokens)
    return token


def verify_token(token: str) -> Optional[int]:
    """
    Verify a token and return the associated user ID.

    Args:
        token: The token to verify

    Returns:
        The user ID if token is valid, None otherwise
    """
    tokens = _load_tokens()
    token_data = tokens.get(token)
    if not token_data:
        return None

    if datetime.now() > token_data["expires_at"]:
        # Token expired, remove it
        del tokens[token]
        _save_tokens(tokens)
        return None

    user_id = token_data.get("user_id")
    if user_id is None:
        return None
    if isinstance(user_id, int):
        return user_id
    try:
        return int(user_id)
    except (TypeError, ValueError):
        return None


def invalidate_token(token: str) -> None:
    """
    Invalidate a token (logout).

    Args:
        token: The token to invalidate
    """
    tokens = _load_tokens()
    if token in tokens:
        del tokens[token]
        _save_tokens(tokens)


def authenticate_user(
    username: str, password: str, db_manager: DatabaseManager
) -> dict:
    """
    Authenticate a user with username and password.

    Args:
        username: The username
        password: The password
        db_manager: DatabaseManager instance

    Returns:
        Dict with status and user data:
        - {"status": "success", "user": {...}} if authentication successful
        - {"status": "not_verified", "user": {...}} if user not verified
        - {"status": "inactive", "user": None} if user is inactive
        - {"status": "invalid", "user": None} if credentials are invalid
    """
    # Get user by username
    user_row = db_manager.get_user(username=username)

    if not user_row:
        return {"status": "invalid", "user": None}

    # Verify password
    if not verify_password(password, user_row["hashed_password"]):
        return {"status": "invalid", "user": None}

    # Check if user is active
    if not user_row["is_active"]:
        return {"status": "inactive", "user": None}

    # Check if user is verified
    if not user_row["is_verified"]:
        # Return user data but with not_verified status
        return {
            "status": "not_verified",
            "user": {
                "id": user_row["id"],
                "email": user_row["email"],
                "username": user_row["username"],
                "full_name": user_row["full_name"],
                "is_active": bool(user_row["is_active"]),
                "is_verified": bool(user_row["is_verified"]),
            },
        }

    # Update last login
    db_manager.update_user(user_id=user_row["id"], last_login=datetime.now())

    # Return user data with success status
    return {
        "status": "success",
        "user": {
            "id": user_row["id"],
            "email": user_row["email"],
            "username": user_row["username"],
            "full_name": user_row["full_name"],
            "is_active": bool(user_row["is_active"]),
            "is_verified": bool(user_row["is_verified"]),
        },
    }
