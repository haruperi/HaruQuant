"""User management module."""

import json
import secrets
import sqlite3
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional, Tuple

from apps.logger import logger
from apps.utils.security import get_encryption_key, hash_password, verify_password

from .base import UserAlreadyExistsError


class UserManager:
    """User management operations."""

    db_path: str

    def create_user(
        self,
        email: str,
        username: str,
        password: str,
        full_name: Optional[str] = None,
        is_superuser: bool = False,
        encryption_key: Optional[bytes] = None,
    ) -> int:
        """
        Create a new user and generate their encryption key.

        Args:
            email (str): User's email.
            username (str): User's username.
            password (str): User's password (will be hashed).
            full_name (str, optional): User's full name.
            is_superuser (bool): Whether user is superuser.
            encryption_key (bytes, optional): Pre-generated encryption key. If None, one will be generated.
        """
        conn = None
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()

            # 1. Hash Password
            hashed_pwd = hash_password(password)

            # 2. Insert User (including encryption key)
            if encryption_key is None:
                encryption_key = get_encryption_key()

            user_query = """
            INSERT INTO users (full_name, username, email, hashed_password, encryption_key, is_superuser)
            VALUES (?, ?, ?, ?, ?, ?)
            """
            cursor.execute(
                user_query,
                (full_name, username, email, hashed_pwd, encryption_key, is_superuser),
            )
            user_id = cursor.lastrowid
            if user_id is None:
                raise ValueError("Failed to retrieve user ID after insertion.")

            conn.commit()

            # 3. Create default settings for the user
            self.create_user_settings(int(user_id))

            logger.info(f"User '{username}' created successfully with ID {user_id}.")
            return int(user_id)

        except sqlite3.IntegrityError as e:
            logger.error(f"Integrity Error (User likely exists): {e}")
            if conn:
                conn.rollback()
            raise UserAlreadyExistsError(str(e)) from e
        except Exception as e:
            logger.error(f"Error creating user: {e}")
            if conn:
                conn.rollback()
            raise
        finally:
            if conn:
                conn.close()

    def create_user_settings(self, user_id: int) -> bool:
        """
        Create default settings for a user.

        Args:
            user_id (int): User's ID

        Returns:
            bool: True if successful, False otherwise
        """
        conn = None
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()

            query = """
            INSERT INTO user_settings (user_id)
            VALUES (?)
            """
            cursor.execute(query, (user_id,))
            conn.commit()

            logger.info(f"Default settings created for user {user_id}.")
            return True

        except sqlite3.IntegrityError as e:
            logger.error(f"Integrity Error creating settings for user {user_id}: {e}")
            if conn:
                conn.rollback()
            raise
        except Exception as e:
            logger.error(f"Error creating settings for user {user_id}: {e}")
            if conn:
                conn.rollback()
            raise
        finally:
            if conn:
                conn.close()

    def get_user(
        self,
        user_id: Optional[int] = None,
        username: Optional[str] = None,
        email: Optional[str] = None,
    ) -> Optional[Dict[str, Any]]:
        """

        Retrieve a user from the database by ID, username, or email.

        Returns a dictionary containing user details and their settings.

        Args:
            user_id (int, optional): User's ID
            username (str, optional): User's username
            email (str, optional): User's email

        Returns:
            dict: User details with a 'settings' key containing user settings, or None if not found
        """
        conn = None
        try:
            conn = sqlite3.connect(self.db_path)
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()

            query = "SELECT * FROM users WHERE "
            params: List[Any] = []

            if user_id:
                query += "id = ?"
                params.append(user_id)
            elif username:
                query += "username = ?"
                params.append(username)
            elif email:
                query += "email = ?"
                params.append(email)
            else:
                return None

            cursor.execute(query, tuple(params))
            row = cursor.fetchone()

            if not row:
                return None

            user_data = dict(row)

            return user_data

        except Exception as e:
            logger.error(f"Error getting user: {e}")
            raise
        finally:
            if conn:
                conn.close()

    def get_user_settings(self, user_id: int) -> Optional[Dict[str, Any]]:
        """
        Retrieve user settings from the database.

        Args:
            user_id (int): User's ID

        Returns:
            dict: User settings or None if not found
        """
        conn = None
        try:
            conn = sqlite3.connect(self.db_path)
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()

            query = """
            SELECT *
            FROM user_settings
            WHERE user_id = ?
            """
            cursor.execute(query, (user_id,))
            row = cursor.fetchone()

            if not row:
                return None

            result = dict(row)

            # Parse JSON fields
            json_fields = [
                "broker_credentials",
                "trading_preferences",
                "notifications",
                "alert_triggers",
            ]
            for field in json_fields:
                if result.get(field) and isinstance(result[field], str):
                    try:
                        result[field] = json.loads(result[field])
                    except json.JSONDecodeError:
                        logger.warning(
                            f"Failed to decode JSON for field {field} user {user_id}"
                        )

            return result

        except Exception as e:
            logger.error(f"Error getting user settings: {e}")
            raise
        finally:
            if conn:
                conn.close()

    def _resolve_user_id(
        self,
        user_id: Optional[int] = None,
        username: Optional[str] = None,
        email: Optional[str] = None,
    ) -> Optional[int]:
        """Resolve user ID from provided identifiers."""
        if user_id:
            return user_id

        user = self.get_user(user_id=user_id, username=username, email=email)
        if user:
            return int(user["id"])
        return None

    def _prepare_update_fields(
        self, user_id: int, **kwargs: Any
    ) -> Tuple[List[str], List[Any]]:
        """Prepare fields and values for user update."""
        update_fields: List[str] = []
        values: List[Any] = []

        # Handle password hashing specifically
        if "password" in kwargs:
            hashed_pwd = hash_password(kwargs.pop("password"))
            update_fields.append("hashed_password = ?")
            values.append(hashed_pwd)

        # Allowed simple fields
        allowed_fields = [
            "email",
            "username",
            "full_name",
            "is_active",
            "is_superuser",
            "is_verified",
            "last_login",
        ]

        for field in allowed_fields:
            if field in kwargs:
                update_fields.append(f"{field} = ?")
                values.append(kwargs[field])

        return update_fields, values

    def update_user(
        self,
        user_id: Optional[int] = None,
        username: Optional[str] = None,
        email: Optional[str] = None,
        **kwargs: Any,
    ) -> bool:
        """
        Update user details in the database.

        Args:
            user_id (int, optional): User's ID
            username (str, optional): User's username
            email (str, optional): User's email
            **kwargs: Fields to update (e.g., email, username, password, full_name, is_active)

        Returns:
            bool: True if successful, False otherwise
        """
        conn = None
        try:
            # 1. Resolve User ID
            # 1. Resolve User ID
            resolved_user_id = self._resolve_user_id(user_id, username, email)
            if not resolved_user_id:
                logger.warning("User not found for update.")
                return False
            user_id = resolved_user_id

            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()

            # 2. Build Update Query
            update_fields, values = self._prepare_update_fields(user_id, **kwargs)

            if not update_fields:
                logger.warning(f"No valid fields to update for user {user_id}")
                return False

            # Add timestamp
            update_fields.append("updated_at = CURRENT_TIMESTAMP")
            values.append(user_id)  # For WHERE clause

            # Build query safely (field names are validated against allowed_fields)
            query = "UPDATE users SET " + ", ".join(update_fields) + " WHERE id = ?"

            cursor.execute(query, values)
            conn.commit()

            logger.info(f"User {user_id} updated successfully.")
            return True

        except sqlite3.IntegrityError as e:
            logger.error(f"Integrity Error during user update: {e}")
            if conn:
                conn.rollback()
            raise
        except Exception as e:
            logger.error(f"Error updating user: {e}")
            if conn:
                conn.rollback()
            raise
        finally:
            if conn:
                conn.close()

    def update_user_settings(self, user_id: int, settings: Dict[str, Any]) -> bool:
        """
        Update user settings in the database.

        Args:
            user_id (int): User's ID
            settings (dict): Dictionary with settings to update

        Returns:
            bool: True if successful
        """
        conn = None
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()

            # Build dynamic UPDATE query based on provided settings
            update_fields: List[str] = []
            values: List[Any] = []

            allowed_fields = [
                "theme",
                "language",
                "timezone",
                "log_verbosity",
                "performance_mode",
                "broker_credentials",
                "trading_preferences",
                "notifications",
                "alert_triggers",
            ]

            for field in allowed_fields:
                if field in settings:
                    update_fields.append(f"{field} = ?")
                    val = settings[field]
                    if isinstance(val, (dict, list)):
                        val = json.dumps(val)
                    values.append(val)

            if not update_fields:
                logger.warning("No valid fields to update")
                return False

            # Add updated_at timestamp
            update_fields.append("updated_at = CURRENT_TIMESTAMP")
            values.append(user_id)

            # Build query safely (field names are validated against allowed_fields)
            query = (
                "UPDATE user_settings SET "
                + ", ".join(update_fields)
                + " WHERE user_id = ?"
            )

            cursor.execute(query, values)
            conn.commit()

            logger.info(f"User settings updated for user_id: {user_id}")
            return True

        except Exception as e:
            logger.error(f"Error updating user settings: {e}")
            if conn:
                conn.rollback()
            raise
        finally:
            if conn:
                conn.close()

    def delete_user(
        self,
        user_id: Optional[int] = None,
        username: Optional[str] = None,
        email: Optional[str] = None,
    ) -> bool:
        """
        Delete a user from the database.

        Args:
            user_id (int, optional): User's ID
            username (str, optional): User's username
            email (str, optional): User's email

        Returns:
            bool: True if successful, False otherwise
        """
        conn = None
        try:
            # 1. Resolve User ID
            # 1. Resolve User ID
            resolved_user_id = self._resolve_user_id(user_id, username, email)
            if not resolved_user_id:
                logger.warning("User not found for deletion.")
                return False
            user_id = resolved_user_id

            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()

            # Enable Foreign Key Constraints for Cascade Delete
            cursor.execute("PRAGMA foreign_keys = ON")

            # 2. Delete User
            query = "DELETE FROM users WHERE id = ?"
            cursor.execute(query, (user_id,))

            if cursor.rowcount == 0:
                logger.warning(
                    f"User {user_id} not found during deletion (rowcount 0)."
                )
                return False

            conn.commit()
            logger.info(f"User {user_id} deleted successfully.")
            return True

        except Exception as e:
            logger.error(f"Error deleting user: {e}")
            if conn:
                conn.rollback()
            raise
        finally:
            if conn:
                conn.close()

    def delete_user_settings(self, user_id: int) -> bool:
        """
        Delete settings for a user.

        Args:
            user_id (int): User's ID

        Returns:
            bool: True if successful, False otherwise
        """
        conn = None
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()

            query = "DELETE FROM user_settings WHERE user_id = ?"
            cursor.execute(query, (user_id,))

            if cursor.rowcount == 0:
                logger.warning(
                    f"Settings for user {user_id} not found during deletion."
                )
                return False

            conn.commit()
            logger.info(f"Settings deleted for user {user_id}.")
            return True

        except Exception as e:
            logger.error(f"Error deleting settings for user {user_id}: {e}")
            if conn:
                conn.rollback()
            raise
        finally:
            if conn:
                conn.close()

    def get_mt5_credentials(self, user_id: int) -> Optional[Dict[str, Any]]:
        """
        Retrieve MT5 credentials for a user.

        Args:
            user_id (int): User's ID

        Returns:
            dict: MT5 credentials if found, None otherwise
        """
        try:
            settings = self.get_user_settings(user_id)

            if not settings:
                logger.warning(f"Settings not found for user {user_id}")
                return None

            broker_creds = settings.get("broker_credentials", {})

            if not broker_creds:
                logger.warning(f"Broker credentials not found for user {user_id}")
                return None

            accounts = broker_creds.get("accounts", [])

            for acc in accounts:
                if acc.get("isDefault"):
                    try:
                        logger.info(
                            f"Default broker account for user {user_id} is {acc.get('name')}"
                        )

                        return {
                            "login": int(acc.get("login")),
                            "password": acc.get("password"),
                            "server": acc.get("server"),
                            "path": acc.get("terminalPath"),
                        }
                    except Exception as e:
                        logger.error(f"Failed get MT5 credentials. {e}")
                        return None

            logger.warning(
                f"Default broker account for user {user_id} not found in database"
            )
            return None

        except Exception as e:
            logger.error(f"Error retrieving MT5 credentials: {e}")

        return None

    def get_mt5_credentials_by_login(
        self, user_id: int, login: int
    ) -> Optional[Dict[str, Any]]:
        """
        Retrieve MT5 credentials for a specific account login.

        Args:
            user_id (int): User's ID
            login (int): The login ID of the account to retrieve

        Returns:
            dict: MT5 credentials if found, None otherwise
        """
        try:
            settings = self.get_user_settings(user_id)

            if not settings:
                return None

            broker_creds = settings.get("broker_credentials", {})
            accounts = broker_creds.get("accounts", [])

            for acc in accounts:
                # Compare as strings or ints to be safe
                if str(acc.get("login")) == str(login):
                    try:
                        return {
                            "login": int(acc.get("login")),
                            "password": acc.get("password"),
                            "server": acc.get("server"),
                            "path": acc.get("terminalPath"),
                        }
                    except Exception as e:
                        logger.error(
                            f"Failed to parse MT5 credentials for login {login}: {e}"
                        )
                        return None

            logger.warning(f"Broker account {login} for user {user_id} not found")
            return None

        except Exception as e:
            logger.error(f"Error retrieving MT5 credentials for {login}: {e}")
            return None

    def delete_user_sessions(self, user_id: int) -> bool:
        """
        Delete all active sessions for a user.

        Args:
            user_id (int): User's ID
        """
        conn = None
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            cursor.execute("DELETE FROM user_sessions WHERE user_id = ?", (user_id,))
            conn.commit()
            return True
        except Exception as e:
            logger.error(f"Error deleting sessions for user {user_id}: {e}")
            return False

    def create_session(self, user_id: int, duration_hours: int = 24) -> str:
        """
        Create a new session for a user.

        Args:
            user_id (int): User's ID
            duration_hours (int): Session duration in hours

        Returns:
            str: Session token
        """
        conn = None
        try:
            token = secrets.token_urlsafe(32)
            expire_time = datetime.now() + timedelta(hours=duration_hours)

            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()

            query = """
            INSERT INTO user_sessions (user_id, token, expire_time)
            VALUES (?, ?, ?)
            """
            cursor.execute(query, (user_id, token, expire_time))
            conn.commit()

            logger.info(f"Session created for user {user_id}")
            return token

        except Exception as e:
            logger.error(f"Error creating session for user {user_id}: {e}")
            if conn:
                conn.rollback()
            raise
        finally:
            if conn:
                conn.close()

    def login_user(self, username: str, password: str) -> Optional[str]:
        """
        Authenticate a user and create a session.

        Args:
            username (str): User's username
            password (str): User's password

        Returns:
            str: Session token if successful, None otherwise
        """
        # 1. Get user by username
        user = self.get_user(username=username)
        if not user:
            logger.warning(f"Login failed: User '{username}' not found.")
            return None

        # 2. Verify password
        if not verify_password(password, user["hashed_password"]):
            logger.warning(f"Login failed: Invalid password for user '{username}'.")
            return None

        # 3. Update last_login
        self.update_user(user_id=user["id"], last_login=datetime.now())

        # 4. Enforce single session: Delete existing sessions
        self.delete_user_sessions(user["id"])

        # 5. Create session
        return self.create_session(user["id"])
