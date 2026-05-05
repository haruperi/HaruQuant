"""
File storage system for strategy code versioning.

Handles:
- Saving strategy code to versioned files
- Loading strategy code from files
- Directory structure management
- Export/import functionality
"""

import importlib.util
import json
import shutil
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional, Type

from services.utils.logger import logger

from services.strategy.base import BaseStrategy
from services.strategy.legacy_compat import install_legacy_apps_modules


class StrategyStorage:
    """
    Manages file storage for trading strategies.

    Directory structure:
        data/strategies/
            john_doe/
                strategy_42_trend_following/
                    v1.0.0/
                        strategy.py
                        metadata.json
                    v1.0.1/
                        strategy.py
                        metadata.json
    """

    def __init__(self, base_dir: Optional[str] = None):
        """
        Initialize strategy storage.

        Args:
            base_dir: Base directory for strategies (default: data/strategies)
        """
        if base_dir:
            self.base_dir = Path(base_dir)
        else:
            # services/strategy/storage.py -> data/strategies
            project_root = Path(__file__).resolve().parents[2]
            self.base_dir = project_root / "data" / "strategies"

        # Ensure base directory exists
        self.base_dir.mkdir(parents=True, exist_ok=True)

        logger.info(f"StrategyStorage initialized at {self.base_dir}")

    def save_strategy(
        self,
        user_id: int,
        strategy_id: int,
        version: str,
        code: str,
        parameters: Optional[Dict[str, Any]] = None,
        metadata: Optional[Dict[str, Any]] = None,
        username: str = "",
        strategy_name: str = "",
    ) -> str:
        """
        Save strategy code to file.

        Args:
            user_id: User ID
            strategy_id: Strategy ID
            version: Version string (e.g., "1.0.0")
            code: Strategy Python code
            parameters: Strategy parameters
            metadata: Additional metadata
            username: Username for folder naming (required)
            strategy_name: Strategy name for folder naming (required)

        Returns:
            Path to saved strategy file
        """
        try:
            # Create version directory
            version_dir = self._get_version_dir(version, username, strategy_name, strategy_id)
            version_dir.mkdir(parents=True, exist_ok=True)

            # Save strategy code
            strategy_file = version_dir / "strategy.py"
            with open(strategy_file, "w", encoding="utf-8") as f:
                f.write(code)

            # Save metadata
            metadata_file = version_dir / "metadata.json"
            full_metadata = {
                "user_id": user_id,
                "strategy_id": strategy_id,
                "version": version,
                "parameters": parameters or {},
                "saved_at": datetime.now().isoformat(),
                **(metadata or {}),
            }

            with open(metadata_file, "w", encoding="utf-8") as f:
                json.dump(full_metadata, f, indent=2)

            logger.info(
                f"Strategy saved: user={user_id}, strategy={strategy_id}, "
                f"version={version}"
            )
            return str(strategy_file)

        except Exception as e:
            logger.error(f"Error saving strategy: {e}")
            raise

    def load_strategy_code(
        self,
        user_id: int,
        strategy_id: int,
        version: str,
        username: str = "",
        strategy_name: str = "",
    ) -> str:
        """
        Load strategy code from file.

        Args:
            user_id: User ID
            strategy_id: Strategy ID
            version: Version string
            username: Optional username for path resolution
            strategy_name: Optional strategy name for path resolution

        Returns:
            Strategy Python code
        """
        try:
            strategy_file = self._get_strategy_file(version, username, strategy_name, strategy_id)

            if not strategy_file.exists():
                raise FileNotFoundError(f"Strategy file not found: {strategy_file}")

            with open(strategy_file, "r", encoding="utf-8") as f:
                code = f.read()

            return code

        except Exception as e:
            logger.error(f"Error loading strategy code: {e}")
            raise

    def load_strategy_metadata(
        self,
        user_id: int,
        strategy_id: int,
        version: str,
        username: str = "",
        strategy_name: str = "",
    ) -> Dict[str, Any]:
        """
        Load strategy metadata from file.

        Args:
            user_id: User ID
            strategy_id: Strategy ID
            version: Version string
            username: Optional username for path resolution
            strategy_name: Optional strategy name for path resolution

        Returns:
            Metadata dictionary
        """
        try:
            metadata_file = self._get_metadata_file(version, username, strategy_name, strategy_id)

            if not metadata_file.exists():
                return {}

            with open(metadata_file, "r", encoding="utf-8") as f:
                metadata: Dict[str, Any] = json.load(f)

            return metadata

        except Exception as e:
            logger.error(f"Error loading strategy metadata: {e}")
            raise

    def load_strategy_class(
        self,
        user_id: int,
        strategy_id: int,
        version: str,
        username: str = "",
        strategy_name: str = "",
    ) -> Type[BaseStrategy]:
        """
        Load strategy class from file.

        Args:
            user_id: User ID
            strategy_id: Strategy ID
            version: Version string
            username: Optional username for path resolution
            strategy_name: Optional strategy name for path resolution

        Returns:
            Strategy class
        """
        try:
            strategy_file = self._get_strategy_file(version, username, strategy_name, strategy_id)

            if not strategy_file.exists():
                raise FileNotFoundError(f"Strategy file not found: {strategy_file}")

            # Load module dynamically
            module_name = f"strategy_{strategy_id}_v{version.replace('.', '_')}"

            spec = importlib.util.spec_from_file_location(module_name, strategy_file)
            if spec is None or spec.loader is None:
                raise ImportError(f"Could not load module spec for {strategy_file}")
            module = importlib.util.module_from_spec(spec)
            install_legacy_apps_modules()
            spec.loader.exec_module(module)

            # Find Strategy subclass in module
            strategy_class = None
            for name in dir(module):
                obj = getattr(module, name)
                if (
                    isinstance(obj, type)
                    and issubclass(obj, BaseStrategy)
                    and obj is not BaseStrategy
                ):
                    strategy_class = obj
                    break

            if strategy_class is None:
                raise ValueError(f"No BaseStrategy subclass found in {strategy_file}")

            logger.info(f"Strategy class loaded: {strategy_class.__name__}")
            return strategy_class

        except Exception as e:
            logger.error(f"Error loading strategy class: {e}")
            raise

    def delete_strategy(
        self,
        user_id: int,
        strategy_id: int,
        username: str = "",
        strategy_name: str = "",
    ) -> None:
        """
        Delete all versions of a strategy.

        Args:
            user_id: User ID
            strategy_id: Strategy ID
            username: Optional username for new folder structure
            strategy_name: Optional strategy name for new folder structure
        """
        try:
            removed = False
            for strategy_dir in self._candidate_strategy_dirs(username, strategy_name, strategy_id):
                if strategy_dir.exists():
                    shutil.rmtree(strategy_dir)
                    removed = True
                    logger.info(f"Strategy deleted: {strategy_dir}")
            if not removed:
                logger.warning(
                    "Strategy directory not found: "
                    f"user={user_id}, strategy={strategy_id}, name={strategy_name}"
                )

        except Exception as e:
            logger.error(f"Error deleting strategy: {e}")
            raise

    def delete_strategy_version(
        self,
        user_id: int,
        strategy_id: int,
        version: str,
        username: str = "",
        strategy_name: str = "",
    ) -> None:
        """
        Delete a specific version of a strategy.

        Args:
            user_id: User ID
            strategy_id: Strategy ID
            version: Version string
            username: Username for folder naming
            strategy_name: Strategy name for folder naming
        """
        try:
            version_dir = self._get_version_dir(version, username, strategy_name, strategy_id)

            if version_dir.exists():
                shutil.rmtree(version_dir)
                logger.info(
                    f"Strategy version deleted: user={user_id}, "
                    f"strategy={strategy_id}, version={version}"
                )
            else:
                logger.warning(f"Version directory not found: {version_dir}")

        except Exception as e:
            logger.error(f"Error deleting strategy version: {e}")
            raise

    def export_strategy(
        self,
        user_id: int,
        strategy_id: int,
        version: str,
        export_path: str,
        username: str = "",
        strategy_name: str = "",
    ) -> str:
        """
        Export strategy to a zip file.

        Args:
            user_id: User ID
            strategy_id: Strategy ID
            version: Version string
            export_path: Path to save exported zip
            username: Username for folder naming
            strategy_name: Strategy name for folder naming

        Returns:
            Path to exported zip file
        """
        try:
            version_dir = self._get_version_dir(version, username, strategy_name, strategy_id)

            if not version_dir.exists():
                raise FileNotFoundError(f"Strategy version not found: {version_dir}")

            # Create zip archive
            export_file = Path(export_path)
            export_file.parent.mkdir(parents=True, exist_ok=True)

            shutil.make_archive(str(export_file.with_suffix("")), "zip", version_dir)

            logger.info(f"Strategy exported to {export_path}")
            return str(export_file.with_suffix(".zip"))

        except Exception as e:
            logger.error(f"Error exporting strategy: {e}")
            raise

    def import_strategy(
        self,
        user_id: int,
        strategy_id: int,
        version: str,
        import_path: str,
        username: str = "",
        strategy_name: str = "",
    ) -> str:
        """
        Import strategy from a zip file.

        Args:
            user_id: User ID
            strategy_id: Strategy ID
            version: Version string
            import_path: Path to zip file to import
            username: Username for folder naming
            strategy_name: Strategy name for folder naming

        Returns:
            Path to imported strategy file
        """
        try:
            import_file = Path(import_path)

            if not import_file.exists():
                raise FileNotFoundError(f"Import file not found: {import_path}")

            # Create version directory
            version_dir = self._get_version_dir(version, username, strategy_name, strategy_id)
            version_dir.mkdir(parents=True, exist_ok=True)

            # Extract zip archive
            shutil.unpack_archive(import_file, version_dir, "zip")

            # Verify files exist
            strategy_file = version_dir / "strategy.py"
            if not strategy_file.exists():
                raise FileNotFoundError("strategy.py not found in import file")

            logger.info(
                f"Strategy imported: user={user_id}, strategy={strategy_id}, "
                f"version={version}"
            )
            return str(strategy_file)

        except Exception as e:
            logger.error(f"Error importing strategy: {e}")
            raise

    def list_versions(
        self,
        username: str = "",
        strategy_name: str = "",
    ) -> List[str]:
        """
        List all versions of a strategy.

        Args:
            user_id: User ID
            strategy_id: Strategy ID
            username: Username for folder naming
            strategy_name: Strategy name for folder naming

        Returns:
            List of version strings
        """
        try:
            user_dir = self._get_user_dir(username)
            sanitized_strategy = self._sanitize_name(strategy_name)
            candidate_dirs = list(user_dir.glob(f"strategy_*_{sanitized_strategy}"))
            candidate_dirs.append(self._get_legacy_strategy_dir(username, strategy_name))

            versions = []
            for strategy_dir in candidate_dirs:
                if not strategy_dir.exists():
                    continue
                for item in strategy_dir.iterdir():
                    if item.is_dir() and item.name.startswith("v"):
                        versions.append(item.name[1:])  # Remove 'v' prefix

            return sorted(set(versions), reverse=True)

        except Exception as e:
            logger.error(f"Error listing versions: {e}")
            raise

    def _sanitize_name(self, name: str) -> str:
        """
        Sanitize a name for use in filesystem paths.

        Args:
            name: Name to sanitize

        Returns:
            Sanitized name safe for filesystem use
        """
        # Convert to lowercase and replace spaces with underscores
        sanitized = name.lower().replace(" ", "_")

        # Remove any characters that aren't alphanumeric, underscore, or hyphen
        sanitized = "".join(c for c in sanitized if c.isalnum() or c in ("_", "-"))

        # Limit length to avoid filesystem issues
        max_length = 50
        if len(sanitized) > max_length:
            sanitized = sanitized[:max_length]

        return sanitized

    def _get_user_dir(self, username: str) -> Path:
        """
        Get user directory path.

        Args:
            username: Username for folder naming

        Returns:
            Path to user directory
        """
        sanitized_username = self._sanitize_name(username)
        if not sanitized_username:
            raise ValueError("Username cannot be empty")

        return self.base_dir / sanitized_username

    def _get_stable_strategy_dir(
        self,
        username: str,
        strategy_name: str,
        strategy_id: int,
    ) -> Path:
        user_dir = self._get_user_dir(username)
        sanitized_strategy = self._sanitize_name(strategy_name)

        if not sanitized_strategy:
            raise ValueError("Strategy name cannot be empty")

        return user_dir / f"strategy_{strategy_id}_{sanitized_strategy}"

    def _get_legacy_strategy_dir(
        self,
        username: str,
        strategy_name: str,
    ) -> Path:
        """
        Get strategy directory path.

        Args:
            username: Username for folder naming
            strategy_name: Strategy name for folder naming

        Returns:
            Path to strategy directory
        """
        user_dir = self._get_user_dir(username)
        sanitized_strategy = self._sanitize_name(strategy_name)

        if not sanitized_strategy:
            raise ValueError("Strategy name cannot be empty")

        return user_dir / sanitized_strategy

    def _candidate_strategy_dirs(
        self,
        username: str,
        strategy_name: str,
        strategy_id: int | None = None,
    ) -> List[Path]:
        dirs: List[Path] = []
        user_dir = self._get_user_dir(username)
        if strategy_id is not None:
            dirs.append(self._get_stable_strategy_dir(username, strategy_name, strategy_id))
            dirs.extend(sorted(user_dir.glob(f"strategy_{strategy_id}_*")))
        dirs.append(self._get_legacy_strategy_dir(username, strategy_name))
        unique_dirs: List[Path] = []
        seen: set[str] = set()
        for directory in dirs:
            key = str(directory)
            if key not in seen:
                unique_dirs.append(directory)
                seen.add(key)
        return unique_dirs

    def _get_strategy_dir(
        self,
        username: str,
        strategy_name: str,
        strategy_id: int | None = None,
    ) -> Path:
        """
        Get the preferred strategy directory path.

        Existing files are resolved from stable then legacy locations. New writes
        prefer the stable directory when strategy_id is available.
        """
        candidates = self._candidate_strategy_dirs(username, strategy_name, strategy_id)
        for candidate in candidates:
            if candidate.exists():
                return candidate
        return candidates[0]

    def _get_version_dir(
        self,
        version: str,
        username: str,
        strategy_name: str,
        strategy_id: int | None = None,
    ) -> Path:
        """
        Get version directory path.

        Args:
            version: Version string
            username: Username for folder naming
            strategy_name: Strategy name for folder naming

        Returns:
            Path to version directory
        """
        return self._get_strategy_dir(username, strategy_name, strategy_id) / f"v{version}"

    def get_strategy_path(
        self,
        user_id: int,
        strategy_id: int,
        version: str,
        username: str = "",
        strategy_name: str = "",
    ) -> str:
        """
        Get absolute path to strategy file.

        Args:
            user_id: User ID
            strategy_id: Strategy ID
            version: Version string
            username: Username for folder naming
            strategy_name: Strategy name for folder naming

        Returns:
            Absolute path to strategy.py file
        """
        return str(self._get_strategy_file(version, username, strategy_name, strategy_id).absolute())

    def _get_strategy_file(
        self,
        version: str,
        username: str,
        strategy_name: str,
        strategy_id: int | None = None,
    ) -> Path:
        """
        Get strategy file path.

        Args:
            version: Version string
            username: Username for folder naming
            strategy_name: Strategy name for folder naming

        Returns:
            Path to strategy.py file
        """
        for strategy_dir in self._candidate_strategy_dirs(username, strategy_name, strategy_id):
            strategy_file = strategy_dir / f"v{version}" / "strategy.py"
            if strategy_file.exists():
                return strategy_file
        user_dir = self._get_user_dir(username)
        if strategy_id is not None and user_dir.exists():
            for strategy_dir in user_dir.iterdir():
                metadata_file = strategy_dir / f"v{version}" / "metadata.json"
                strategy_file = strategy_dir / f"v{version}" / "strategy.py"
                if not metadata_file.exists() or not strategy_file.exists():
                    continue
                try:
                    metadata = json.loads(metadata_file.read_text(encoding="utf-8"))
                except json.JSONDecodeError:
                    continue
                if int(metadata.get("strategy_id", -1)) == int(strategy_id):
                    return strategy_file
        return self._get_version_dir(version, username, strategy_name, strategy_id) / "strategy.py"

    def _get_metadata_file(
        self,
        version: str,
        username: str,
        strategy_name: str,
        strategy_id: int | None = None,
    ) -> Path:
        """
        Get metadata file path.

        Args:
            version: Version string
            username: Username for folder naming
            strategy_name: Strategy name for folder naming

        Returns:
            Path to metadata.json file
        """
        for strategy_dir in self._candidate_strategy_dirs(username, strategy_name, strategy_id):
            metadata_file = strategy_dir / f"v{version}" / "metadata.json"
            if metadata_file.exists():
                return metadata_file
        user_dir = self._get_user_dir(username)
        if strategy_id is not None and user_dir.exists():
            for strategy_dir in user_dir.iterdir():
                metadata_file = strategy_dir / f"v{version}" / "metadata.json"
                if not metadata_file.exists():
                    continue
                try:
                    metadata = json.loads(metadata_file.read_text(encoding="utf-8"))
                except json.JSONDecodeError:
                    continue
                if int(metadata.get("strategy_id", -1)) == int(strategy_id):
                    return metadata_file
        return self._get_version_dir(version, username, strategy_name, strategy_id) / "metadata.json"

    def get_strategy_artifact_root(
        self,
        user_id: int,
        strategy_id: int,
        username: str = "",
        strategy_name: str = "",
    ) -> str:
        """Return the preferred artifact root for a strategy."""
        return str(self._get_strategy_dir(username, strategy_name, strategy_id).absolute())


# Global instance
storage = StrategyStorage()
