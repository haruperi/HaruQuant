"""Authentication utility functions."""

from datetime import datetime
from haruquant.utils import logger
from typing import Optional

from fastapi import Header, HTTPException, status

from backend.data.database.sqlite.database_operations import DatabaseManager
from haruquant.utils import verify_password


def generate_token(user_id: int, db_manager: DatabaseManager) -> str:
    """
    Generate a secure random token for user authentication and store in DB.

    Token expires after 24 hours.

    Args:
        user_id: The user's ID
        db_manager: DatabaseManager instance

    Returns:
        A secure random token
    """
    # Enforce single session: Delete any existing sessions for this user
    # This ensures that if a user logs in again, their old session is invalidated
    db_manager.delete_user_sessions(user_id)

    # Use the existing create_session method which handles token generation and storage
    return db_manager.create_session(user_id, duration_hours=24)


def verify_token(token: str, db_manager: DatabaseManager) -> Optional[int]:
    """
    Verify a token and return the associated user ID.

    Args:
        token: The token to verify
        db_manager: DatabaseManager instance

    Returns:
        The user ID if token is valid, None otherwise
    """
    # 1. Get session from DB
    session = db_manager.get_session(token)

    if not session:
        return None

    # 2. Check expiration
    expire_time_str = session["expire_time"]
    try:
        # DB stores timestamp as string usually, ensure parsing
        # Format might be ISO or custom depending on sqlite setup,
        # but typically "YYYY-MM-DD HH:MM:SS" or ISO
        # Base class methods usually return strings for timestamps

        # Simple flexible parsing if needed, but lets try fromisoformat first
        # or simple comparison if they are ISO strings
        expire_time = datetime.fromisoformat(expire_time_str)
    except ValueError:
        # Fallback for standard SQL timestamp "YYYY-MM-DD HH:MM:SS"
        try:
            expire_time = datetime.strptime(expire_time_str, "%Y-%m-%d %H:%M:%S.%f")
        except ValueError:
            try:
                expire_time = datetime.strptime(expire_time_str, "%Y-%m-%d %H:%M:%S")
            except ValueError:
                # If we can't parse it, safe fail
                return None

    if datetime.now() > expire_time:
        # Token expired, delete from DB
        db_manager.delete_session(token)
        return None

    # 3. Valid session, return user_id
    return int(session["user_id"])


def invalidate_token(token: str, db_manager: DatabaseManager) -> None:
    """
    Invalidate a token (logout).

    Args:
        token: The token to invalidate
        db_manager: DatabaseManager instance
    """
    db_manager.delete_session(token)


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


def get_user_id_from_token(
    authorization: Optional[str] = Header(None),  # noqa: B008
) -> int:
    """
    Validate token and return user ID. Raises 401 if invalid.

    Args:
        token: The simple API token key, optionally prefixed with 'Bearer '

    Returns:
        int: The validated user ID

    Raises:
        HTTPException(401): If token is missing or invalid
    """
    if not authorization:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Missing authorization header",
            headers={"WWW-Authenticate": "Bearer"},
        )

    token = authorization
    # Strip 'Bearer ' prefix if present
    if token.lower().startswith("bearer "):
        token = token[7:]

    db_manager = DatabaseManager()
    user_id = verify_token(token, db_manager)

    if not user_id:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired token",
            headers={"WWW-Authenticate": "Bearer"},
        )

    return user_id
