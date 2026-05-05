"""Strategy catalog facade for legacy storage plus agentic governance."""

from __future__ import annotations

from dataclasses import dataclass
from hashlib import sha256
import json
from pathlib import Path
import tempfile
from typing import TYPE_CHECKING, Any, Dict, List, Optional

from services.utils.logger import logger

from .storage import StrategyStorage, storage as default_storage

if TYPE_CHECKING:
    from backend.data.database import GovernanceRepository
    from backend.data.database.repositories.governance_repository import StrategyRecord
    from backend.data.database.sqlite.database_operations import DatabaseManager


def canonical_json_hash(payload: Any) -> str:
    """Return a deterministic SHA-256 hash for JSON-like payloads."""
    encoded = json.dumps(payload or {}, sort_keys=True, separators=(",", ":"), default=str)
    return sha256(encoded.encode("utf-8")).hexdigest()


def code_hash(code: str) -> str:
    """Return a SHA-256 hash for strategy source code."""
    return sha256((code or "").encode("utf-8")).hexdigest()


def governance_strategy_id(user_id: int, strategy_id: int) -> str:
    """Return the stable agentic governance identifier for a strategy."""
    return f"strategy:{user_id}:{strategy_id}"


@dataclass(frozen=True)
class StrategyCatalogCreateRequest:
    name: str
    code: str
    description: Optional[str] = None
    category: Optional[str] = None
    parameters: Optional[Dict[str, Any]] = None
    parameter_types: Optional[Dict[str, str]] = None
    symbol: Optional[str] = None
    timeframe: Optional[str] = None
    strategy_type: Optional[str] = None
    money_management: Optional[Dict[str, Any]] = None
    variables: Optional[Dict[str, Any]] = None
    variable_types: Optional[Dict[str, str]] = None


@dataclass(frozen=True)
class StrategyCatalogUpdateRequest:
    name: Optional[str] = None
    description: Optional[str] = None
    status: Optional[str] = None
    category: Optional[str] = None
    code: Optional[str] = None
    parameters: Optional[Dict[str, Any]] = None
    parameter_types: Optional[Dict[str, str]] = None
    symbol: Optional[str] = None
    timeframe: Optional[str] = None
    strategy_type: Optional[str] = None
    money_management: Optional[Dict[str, Any]] = None
    variables: Optional[Dict[str, Any]] = None
    variable_types: Optional[Dict[str, str]] = None
    changelog: Optional[str] = None


class StrategyCatalogService:
    """Coordinate strategy DB rows, filesystem artifacts, and governance rows."""

    def __init__(
        self,
        db_manager: Optional["DatabaseManager"] = None,
        strategy_storage: StrategyStorage = default_storage,
        governance_repository: Optional["GovernanceRepository"] = None,
    ) -> None:
        if db_manager is None:
            from backend.data.database.sqlite.database_operations import DatabaseManager

            db_manager = DatabaseManager()
        self.db = db_manager
        self.storage = strategy_storage
        if governance_repository is None:
            from backend.data.database import GovernanceRepository

            governance_repository = GovernanceRepository(self.db.db_path)
        self.governance = governance_repository

    def create_strategy(
        self,
        request: StrategyCatalogCreateRequest,
        *,
        user_id: int,
    ) -> Dict[str, Any]:
        if not request.name.strip():
            raise ValueError("Strategy name is required.")
        if not request.code:
            raise ValueError("Strategy code is required.")

        strategy_id = self.db.create_strategy(
            user_id=user_id,
            name=request.name,
            description=request.description,
            category=request.category,
            status="inactive",
            is_public=False,
        )
        username = self._username_for(user_id)
        family = self._strategy_family(request.category)
        gov_id = governance_strategy_id(user_id, strategy_id)

        version = "1.0.0"
        metadata = self._metadata_from_create(request)
        file_path = self.storage.save_strategy(
            user_id=user_id,
            strategy_id=strategy_id,
            version=version,
            code=request.code,
            parameters=request.parameters or {},
            username=username,
            strategy_name=request.name,
            metadata=metadata,
        )
        self.db.create_strategy_version(
            strategy_id=strategy_id,
            version=version,
            file_path=file_path,
            parameters=request.parameters or {},
            changelog="Initial version",
            created_by=user_id,
        )

        artifact_root = self.storage.get_strategy_artifact_root(
            user_id=user_id,
            strategy_id=strategy_id,
            username=username,
            strategy_name=request.name,
        )
        self._update_catalog_fields(
            strategy_id,
            governance_strategy_id=gov_id,
            artifact_root=artifact_root,
            strategy_family=family,
        )
        governance = self._upsert_governance(
            strategy_id=strategy_id,
            user_id=user_id,
            strategy_name=request.name,
            strategy_family=family,
            code=request.code,
            parameters=request.parameters or {},
        )

        strategy = self.get_strategy(strategy_id, user_id=user_id)
        strategy.update(self._governance_projection(governance))
        return strategy

    def list_strategies(
        self,
        *,
        user_id: int,
        status: Optional[str] = None,
        category: Optional[str] = None,
        include_shared: bool = False,
    ) -> List[Dict[str, Any]]:
        rows = self.db.get_user_strategies(
            user_id=user_id,
            status=status,
            category=category,
            include_shared=include_shared,
        )
        return [self._enrich_with_governance(row) for row in rows]

    def get_strategy(self, strategy_id: int, *, user_id: Optional[int] = None) -> Dict[str, Any]:
        strategy = self.db.get_strategy(strategy_id)
        if not strategy:
            raise LookupError(f"Strategy {strategy_id} not found")
        self._assert_owner(strategy, user_id)
        return self._enrich_with_governance(strategy)

    def update_strategy(
        self,
        strategy_id: int,
        request: StrategyCatalogUpdateRequest,
        *,
        user_id: int,
    ) -> Dict[str, Any]:
        current = self.get_strategy(strategy_id, user_id=user_id)
        update_fields: Dict[str, Any] = {}
        if request.name:
            update_fields["name"] = request.name
        if request.description is not None:
            update_fields["description"] = request.description
        if request.status:
            update_fields["status"] = request.status
        if request.category:
            update_fields["category"] = request.category
            update_fields["strategy_family"] = self._strategy_family(request.category)
        if update_fields:
            self.db.update_strategy(strategy_id, **update_fields)

        new_code = request.code
        parameters = request.parameters if request.parameters is not None else {}
        if new_code:
            strategy_name = request.name or str(current["name"])
            self.create_strategy_version(
                strategy_id=strategy_id,
                code=new_code,
                parameters=parameters,
                user_id=user_id,
                strategy_name=strategy_name,
                metadata=self._metadata_from_update(request, strategy_name),
                changelog=request.changelog or "Updated via editor",
            )

        updated = self.get_strategy(strategy_id, user_id=user_id)
        if new_code:
            self._upsert_governance(
                strategy_id=strategy_id,
                user_id=user_id,
                strategy_name=str(updated["name"]),
                strategy_family=self._strategy_family(updated.get("strategy_family") or updated.get("category")),
                code=new_code,
                parameters=parameters,
            )
            updated = self.get_strategy(strategy_id, user_id=user_id)
        return updated

    def create_strategy_version(
        self,
        *,
        strategy_id: int,
        code: str,
        parameters: Optional[Dict[str, Any]],
        user_id: int,
        strategy_name: str,
        metadata: Dict[str, Any],
        changelog: Optional[str],
        major_bump: bool = False,
    ) -> str:
        username = self._username_for(user_id)
        db_versions = self.db.get_strategy_versions(strategy_id)
        new_version = self._next_version(db_versions, major_bump=major_bump)
        file_path = self.storage.save_strategy(
            user_id=user_id,
            strategy_id=strategy_id,
            version=new_version,
            code=code,
            parameters=parameters or {},
            username=username,
            strategy_name=strategy_name,
            metadata=metadata,
        )
        self.db.create_strategy_version(
            strategy_id=strategy_id,
            version=new_version,
            file_path=file_path,
            parameters=parameters or {},
            changelog=changelog,
            created_by=user_id,
        )
        artifact_root = self.storage.get_strategy_artifact_root(
            user_id=user_id,
            strategy_id=strategy_id,
            username=username,
            strategy_name=strategy_name,
        )
        self._update_catalog_fields(strategy_id, artifact_root=artifact_root)
        return new_version

    def delete_strategy(self, strategy_id: int, *, user_id: int) -> None:
        strategy = self.get_strategy(strategy_id, user_id=user_id)
        username = self._username_for(user_id)
        success = self.db.delete_strategy(strategy_id)
        if not success:
            raise LookupError(f"Strategy {strategy_id} not found")
        self.storage.delete_strategy(
            user_id=user_id,
            strategy_id=strategy_id,
            username=username,
            strategy_name=str(strategy["name"]),
        )

    def list_versions(self, strategy_id: int) -> List[Dict[str, Any]]:
        return self.db.get_strategy_versions(strategy_id)

    def get_version_code(
        self,
        *,
        strategy_id: int,
        version_id: int,
        user_id: int,
        baseline_source_lookup: Optional[Any] = None,
    ) -> Dict[str, Any]:
        version = self.db.get_strategy_version(version_id)
        if version is None:
            raise LookupError(f"Strategy version {version_id} not found")
        strategy = self.get_strategy(strategy_id, user_id=user_id)

        code: Optional[str] = None
        file_path = version.get("file_path")
        if file_path and Path(str(file_path)).exists():
            code = Path(str(file_path)).read_text(encoding="utf-8")
            metadata = self._load_metadata_from_file_path(Path(str(file_path)))
        else:
            username = self._username_for(user_id)
            metadata = {}
            try:
                code = self.storage.load_strategy_code(
                    user_id=user_id,
                    strategy_id=strategy_id,
                    version=str(version["version"]),
                    username=username,
                    strategy_name=str(strategy["name"]),
                )
                metadata = self.storage.load_strategy_metadata(
                    user_id=user_id,
                    strategy_id=strategy_id,
                    version=str(version["version"]),
                    username=username,
                    strategy_name=str(strategy["name"]),
                )
            except FileNotFoundError:
                if baseline_source_lookup:
                    code = baseline_source_lookup(str(strategy["name"]))
                if code is None:
                    raise FileNotFoundError(
                        f"Strategy code not found for strategy {strategy_id} version {version_id}"
                    )

        return {
            "version_id": version_id,
            "version": version["version"],
            "code": code,
            "parameters": version.get("parameters") or {},
            "symbol": metadata.get("symbol"),
            "timeframe": metadata.get("timeframe"),
            "type": metadata.get("type"),
            "parameterTypes": metadata.get("parameterTypes"),
            "moneyManagement": metadata.get("moneyManagement"),
            "variables": metadata.get("variables"),
            "variableTypes": metadata.get("variableTypes"),
        }

    def rollback_version(self, *, strategy_id: int, version_id: int, user_id: int) -> None:
        self.get_strategy(strategy_id, user_id=user_id)
        version = self.db.get_strategy_version(version_id)
        if version is None or int(version["strategy_id"]) != strategy_id:
            raise LookupError(f"Strategy version {version_id} not found for strategy {strategy_id}")
        self.db.update_strategy(strategy_id, active_version_id=version_id)

    def export_strategy(self, *, strategy_id: int, user_id: int) -> str:
        strategy = self.get_strategy(strategy_id, user_id=user_id)
        active_version = strategy.get("active_version")
        if not active_version:
            raise LookupError(f"Strategy {strategy_id} has no active version")
        username = self._username_for(user_id)
        export_path = str(
            Path(tempfile.gettempdir())
            / f"strategy_{strategy_id}_v{active_version}.zip"
        )
        return self.storage.export_strategy(
            user_id=user_id,
            strategy_id=strategy_id,
            version=str(active_version),
            export_path=export_path,
            username=username,
            strategy_name=str(strategy["name"]),
        )

    def import_strategy(
        self,
        *,
        strategy_id: int,
        import_path: str,
        original_filename: str,
        user_id: int,
    ) -> str:
        strategy = self.get_strategy(strategy_id, user_id=user_id)
        username = self._username_for(user_id)
        db_versions = self.db.get_strategy_versions(strategy_id)
        new_version = self._next_version(db_versions, major_bump=True)
        strategy_name = str(strategy["name"])
        file_path = self.storage.import_strategy(
            user_id=user_id,
            strategy_id=strategy_id,
            version=new_version,
            import_path=import_path,
            username=username,
            strategy_name=strategy_name,
        )
        metadata = self.storage.load_strategy_metadata(
            user_id=user_id,
            strategy_id=strategy_id,
            version=new_version,
            username=username,
            strategy_name=strategy_name,
        )
        parameters = metadata.get("parameters", {})
        self.db.create_strategy_version(
            strategy_id=strategy_id,
            version=new_version,
            file_path=file_path,
            parameters=parameters,
            changelog=f"Imported from {original_filename}",
            created_by=user_id,
        )
        imported_code = Path(file_path).read_text(encoding="utf-8")
        self._upsert_governance(
            strategy_id=strategy_id,
            user_id=user_id,
            strategy_name=strategy_name,
            strategy_family=self._strategy_family(strategy.get("strategy_family") or strategy.get("category")),
            code=imported_code,
            parameters=parameters,
        )
        return new_version

    def validate_strategy_code(self, code: str) -> None:
        compile(code, "<strategy>", "exec")

    def _upsert_governance(
        self,
        *,
        strategy_id: int,
        user_id: int,
        strategy_name: str,
        strategy_family: str,
        code: str,
        parameters: Optional[Dict[str, Any]],
    ) -> "StrategyRecord":
        from services.strategy.governance import StrategyLifecycleState

        gov_id = governance_strategy_id(user_id, strategy_id)
        return self.governance.upsert_strategy(
            strategy_id=gov_id,
            strategy_name=strategy_name,
            strategy_family=strategy_family,
            current_lifecycle_state=StrategyLifecycleState.RESEARCH.value,
            code_hash=code_hash(code),
            parameter_hash=canonical_json_hash(parameters or {}),
            owner_id=str(user_id),
        )

    def _enrich_with_governance(self, strategy: Dict[str, Any]) -> Dict[str, Any]:
        enriched = dict(strategy)
        gov_id = enriched.get("governance_strategy_id")
        if not gov_id:
            gov_id = governance_strategy_id(int(enriched["user_id"]), int(enriched["id"]))
            enriched["governance_strategy_id"] = gov_id
        governance = self.governance.get_strategy(str(gov_id))
        if governance:
            enriched.update(self._governance_projection(governance))
        return enriched

    def _governance_projection(self, governance: "StrategyRecord") -> Dict[str, Any]:
        return {
            "governance_strategy_id": governance.strategy_id,
            "lifecycle_state": governance.current_lifecycle_state,
            "code_hash": governance.code_hash,
            "parameter_hash": governance.parameter_hash,
            "strategy_family": governance.strategy_family,
        }

    def _username_for(self, user_id: int) -> str:
        user = self.db.get_user(user_id=user_id)
        username = (user.get("username") if user else None) or f"user_{user_id}"
        return str(username)

    def _assert_owner(self, strategy: Dict[str, Any], user_id: Optional[int]) -> None:
        if user_id is not None and int(strategy["user_id"]) != int(user_id):
            raise PermissionError(f"User {user_id} does not own strategy {strategy['id']}")

    def _strategy_family(self, value: Optional[Any]) -> str:
        text = str(value or "").strip()
        return text or "custom"

    def _update_catalog_fields(self, strategy_id: int, **fields: Any) -> None:
        clean = {key: value for key, value in fields.items() if value is not None}
        if clean:
            self.db.update_strategy(strategy_id, **clean)

    def _metadata_from_create(self, request: StrategyCatalogCreateRequest) -> Dict[str, Any]:
        return {
            "name": request.name,
            "description": request.description,
            "symbol": request.symbol,
            "timeframe": request.timeframe,
            "type": request.strategy_type,
            "parameterTypes": request.parameter_types,
            "moneyManagement": request.money_management,
            "variables": request.variables,
            "variableTypes": request.variable_types,
        }

    def _metadata_from_update(
        self,
        request: StrategyCatalogUpdateRequest,
        strategy_name: str,
    ) -> Dict[str, Any]:
        return {
            "name": request.name or strategy_name,
            "description": request.description,
            "symbol": request.symbol,
            "timeframe": request.timeframe,
            "type": request.strategy_type,
            "parameterTypes": request.parameter_types,
            "moneyManagement": request.money_management,
            "variables": request.variables,
            "variableTypes": request.variable_types,
            "changelog": request.changelog,
        }

    def _load_metadata_from_file_path(self, strategy_file: Path) -> Dict[str, Any]:
        metadata_file = strategy_file.parent / "metadata.json"
        if not metadata_file.exists():
            return {}
        return json.loads(metadata_file.read_text(encoding="utf-8"))

    def _next_version(
        self,
        versions: List[Dict[str, Any]],
        *,
        major_bump: bool = False,
    ) -> str:
        if not versions:
            return "1.0.0"
        last_version = str(versions[0]["version"])
        major, minor, patch = (int(part) for part in last_version.split("."))
        if major_bump:
            return f"{major + 1}.0.0"
        return f"{major}.{minor}.{patch + 1}"
