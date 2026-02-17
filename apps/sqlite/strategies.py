"""Strategy management module."""

import contextlib
import json
import sqlite3
from typing import Any, Dict, List, Optional

from apps.utils.logger import logger


class StrategyManager:
    """Strategy management operations."""

    db_path: str

    def create_strategy(
        self,
        user_id: int,
        name: str,
        description: Optional[str] = None,
        category: Optional[str] = None,
        status: str = "inactive",
        is_public: bool = False,
    ) -> int:
        """
        Create a new strategy.

        Args:
            user_id (int): User's ID
            name (str): Strategy name
            description (str): Strategy description
            category (str): Strategy category
            status (str): Strategy status (active/inactive/testing)
            is_public (bool): Whether strategy is public

        Returns:
            int: Strategy ID
        """
        conn = None
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()

            query = """
            INSERT INTO strategies (user_id, name, description, category, status, is_public)
            VALUES (?, ?, ?, ?, ?, ?)
            """
            cursor.execute(
                query, (user_id, name, description, category, status, is_public)
            )
            strategy_id = cursor.lastrowid
            if strategy_id is None:
                raise ValueError("Failed to retrieve strategy ID after insertion.")
            conn.commit()

            logger.info(
                f"Strategy '{name}' created successfully with ID {strategy_id}."
            )
            return int(strategy_id)

        except Exception as e:
            logger.error(f"Error creating strategy: {e}")
            if conn:
                conn.rollback()
            raise
        finally:
            if conn:
                conn.close()

    def create_strategy_version(
        self,
        strategy_id: int,
        version: str,
        file_path: str,
        parameters: Optional[Dict[str, Any]] = None,
        changelog: Optional[str] = None,
        created_by: Optional[int] = None,
    ) -> int:
        """
        Create a new version of a strategy.

        Args:
            strategy_id (int): Strategy ID
            version (str): Version string (e.g., "1.0.0")
            file_path (str): Path to strategy file
            parameters (dict): Strategy parameters
            changelog (str): Version changelog
            created_by (int): User ID who created this version

        Returns:
            int: Version ID
        """
        conn = None
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()

            params_json = json.dumps(parameters) if parameters else "{}"

            query = """
            INSERT INTO strategy_versions (strategy_id, version, file_path, parameters, changelog, created_by)
            VALUES (?, ?, ?, ?, ?, ?)
            """
            cursor.execute(
                query,
                (strategy_id, version, file_path, params_json, changelog, created_by),
            )
            version_id = cursor.lastrowid
            if version_id is None:
                raise ValueError("Failed to retrieve version ID after insertion.")

            # Update strategy's active_version_id
            cursor.execute(
                """
                UPDATE strategies
                SET active_version_id = ?, updated_at = CURRENT_TIMESTAMP
                WHERE id = ?
            """,
                (version_id, strategy_id),
            )

            conn.commit()
            logger.info(
                f"Strategy version {version} created for strategy {strategy_id}."
            )
            return int(version_id)

        except Exception as e:
            logger.error(f"Error creating strategy version: {e}")
            if conn:
                conn.rollback()
            raise
        finally:
            if conn:
                conn.close()

    def get_strategy(self, strategy_id: int) -> Optional[Dict[str, Any]]:
        """
        Retrieve a strategy by ID.

        Args:
            strategy_id (int): Strategy ID

        Returns:
            dict: Strategy details or None if not found
        """
        conn = None
        try:
            conn = sqlite3.connect(self.db_path)
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()

            query = """
            SELECT s.*, sv.version as active_version, sv.file_path as active_file_path
            FROM strategies s
            LEFT JOIN strategy_versions sv ON s.active_version_id = sv.id
            WHERE s.id = ?
            """
            cursor.execute(query, (strategy_id,))
            row = cursor.fetchone()

            if not row:
                return None

            return dict(row)

        except Exception as e:
            logger.error(f"Error getting strategy: {e}")
            raise
        finally:
            if conn:
                conn.close()

    def get_user_strategies(
        self,
        user_id: int,
        status: Optional[str] = None,
        category: Optional[str] = None,
        include_shared: bool = False,
    ) -> List[Dict[str, Any]]:
        """
        Retrieve all strategies for a user.

        Args:
            user_id (int): User ID
            status (str): Filter by status
            category (str): Filter by category
            include_shared (bool): Include strategies shared with user

        Returns:
            list: List of strategy dictionaries
        """
        conn = None
        try:
            conn = sqlite3.connect(self.db_path)
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()

            query = """
            SELECT s.*, sv.version as active_version
            FROM strategies s
            LEFT JOIN strategy_versions sv ON s.active_version_id = sv.id
            WHERE s.user_id = ?
            """
            params: List[Any] = [user_id]

            if status:
                query += " AND s.status = ?"
                params.append(status)

            if category:
                query += " AND s.category = ?"
                params.append(category)

            query += " ORDER BY s.updated_at DESC"

            cursor.execute(query, params)
            rows = cursor.fetchall()

            strategies = [dict(row) for row in rows]

            # Include shared strategies if requested
            if include_shared:
                shared_query = """
                SELECT s.*, sv.version as active_version, ss.permission
                FROM strategies s
                LEFT JOIN strategy_versions sv ON s.active_version_id = sv.id
                JOIN strategy_shares ss ON s.id = ss.strategy_id
                WHERE ss.shared_with_user_id = ?
                ORDER BY s.updated_at DESC
                """
                cursor.execute(shared_query, (user_id,))
                shared_rows = cursor.fetchall()
                strategies.extend([dict(row) for row in shared_rows])

            return strategies

        except Exception as e:
            logger.error(f"Error getting user strategies: {e}")
            raise
        finally:
            if conn:
                conn.close()

    def get_strategy_versions(self, strategy_id: int) -> List[Dict[str, Any]]:
        """
        Retrieve all versions of a strategy.

        Args:
            strategy_id (int): Strategy ID

        Returns:
            list: List of version dictionaries
        """
        conn = None
        try:
            conn = sqlite3.connect(self.db_path)
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()

            query = """
            SELECT * FROM strategy_versions
            WHERE strategy_id = ?
            ORDER BY created_at DESC
            """
            cursor.execute(query, (strategy_id,))
            rows = cursor.fetchall()

            versions = []
            for row in rows:
                version_dict = dict(row)
                # Parse JSON parameters
                if version_dict.get("parameters"):
                    with contextlib.suppress(json.JSONDecodeError):
                        version_dict["parameters"] = json.loads(
                            version_dict["parameters"]
                        )
                versions.append(version_dict)

            return versions

        except Exception as e:
            logger.error(f"Error getting strategy versions: {e}")
            raise
        finally:
            if conn:
                conn.close()

    def get_strategy_version(self, version_id: int) -> Optional[Dict[str, Any]]:
        """
        Retrieve a specific strategy version.

        Args:
            version_id (int): Version ID

        Returns:
            dict: Version details or None if not found
        """
        conn = None
        try:
            conn = sqlite3.connect(self.db_path)
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()

            query = "SELECT * FROM strategy_versions WHERE id = ?"
            cursor.execute(query, (version_id,))
            row = cursor.fetchone()

            if not row:
                return None

            version_dict = dict(row)
            # Parse JSON parameters
            if version_dict.get("parameters"):
                with contextlib.suppress(json.JSONDecodeError):
                    version_dict["parameters"] = json.loads(version_dict["parameters"])

            return version_dict

        except Exception as e:
            logger.error(f"Error getting strategy version: {e}")
            raise
        finally:
            if conn:
                conn.close()

    def update_strategy(self, strategy_id: int, **kwargs: Any) -> bool:
        """
        Update a strategy.

        Args:
            strategy_id (int): Strategy ID
            **kwargs: Fields to update

        Returns:
            bool: True if successful
        """
        conn = None
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()

            update_fields: List[str] = []
            values: List[Any] = []

            allowed_fields = [
                "name",
                "description",
                "status",
                "category",
                "is_public",
                "active_version_id",
            ]

            for field in allowed_fields:
                if field in kwargs:
                    update_fields.append(f"{field} = ?")
                    values.append(kwargs[field])

            if not update_fields:
                logger.warning("No valid fields to update")
                return False

            update_fields.append("updated_at = CURRENT_TIMESTAMP")
            values.append(strategy_id)

            query = (
                "UPDATE strategies SET " + ", ".join(update_fields) + " WHERE id = ?"
            )
            cursor.execute(query, values)
            conn.commit()

            logger.info(f"Strategy {strategy_id} updated successfully.")
            return True

        except Exception as e:
            logger.error(f"Error updating strategy: {e}")
            if conn:
                conn.rollback()
            raise
        finally:
            if conn:
                conn.close()

    def delete_strategy(self, strategy_id: int) -> bool:
        """
        Delete a strategy.

        Args:
            strategy_id (int): Strategy ID

        Returns:
            bool: True if successful
        """
        conn = None
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()

            cursor.execute("PRAGMA foreign_keys = ON")
            cursor.execute("DELETE FROM strategies WHERE id = ?", (strategy_id,))

            if cursor.rowcount == 0:
                logger.warning(f"Strategy {strategy_id} not found.")
                return False

            conn.commit()
            logger.info(f"Strategy {strategy_id} deleted successfully.")
            return True

        except Exception as e:
            logger.error(f"Error deleting strategy: {e}")
            if conn:
                conn.rollback()
            raise
        finally:
            if conn:
                conn.close()

    def delete_strategy_version(self, version_id: int) -> bool:
        """
        Delete a strategy version.

        Args:
            version_id (int): Version ID

        Returns:
            bool: True if successful
        """
        conn = None
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()

            cursor.execute("PRAGMA foreign_keys = ON")
            cursor.execute("DELETE FROM strategy_versions WHERE id = ?", (version_id,))

            if cursor.rowcount == 0:
                logger.warning(f"Strategy version {version_id} not found.")
                return False

            conn.commit()
            logger.info(f"Strategy version {version_id} deleted successfully.")
            return True

        except Exception as e:
            logger.error(f"Error deleting strategy version: {e}")
            if conn:
                conn.rollback()
            raise
        finally:
            if conn:
                conn.close()

    def share_strategy(
        self, strategy_id: int, shared_with_user_id: int, permission: str = "view"
    ) -> Optional[int]:
        """
        Shares a strategy with another user.

        Args:
            strategy_id (int): Strategy ID
            shared_with_user_id (int): User ID to share with
            permission (str): Permission level (view/clone/edit)

        Returns:
            int: Share ID
        """
        conn = None
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()

            query = """
            INSERT INTO strategy_shares (strategy_id, shared_with_user_id, permission)
            VALUES (?, ?, ?)
            """
            cursor.execute(query, (strategy_id, shared_with_user_id, permission))
            share_id = cursor.lastrowid
            conn.commit()

            logger.info(
                f"Strategy {strategy_id} shared with user {shared_with_user_id}."
            )
            return share_id

        except sqlite3.IntegrityError:
            logger.warning(
                f"Strategy {strategy_id} already shared with user {shared_with_user_id}."
            )
            return None
        except Exception as e:
            logger.error(f"Error sharing strategy: {e}")
            if conn:
                conn.rollback()
            raise
        finally:
            if conn:
                conn.close()

    def unshare_strategy(self, strategy_id: int, shared_with_user_id: int) -> bool:
        """
        Remove strategy sharing.

        Args:
            strategy_id (int): Strategy ID
            shared_with_user_id (int): User ID

        Returns:
            bool: True if successful
        """
        conn = None
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()

            query = "DELETE FROM strategy_shares WHERE strategy_id = ? AND shared_with_user_id = ?"
            cursor.execute(query, (strategy_id, shared_with_user_id))
            conn.commit()

            logger.info(
                f"Strategy {strategy_id} unshared from user {shared_with_user_id}."
            )
            return True

        except Exception as e:
            logger.error(f"Error unsharing strategy: {e}")
            if conn:
                conn.rollback()
            raise
        finally:
            if conn:
                conn.close()

