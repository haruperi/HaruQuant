"""Strategy routes for managing trading strategies."""

import os
import tempfile
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, File, HTTPException, UploadFile, status
from fastapi.responses import FileResponse
from pydantic import BaseModel

from backend.common.logger import logger
from backend.db.sqlite.database_operations import DatabaseManager
from backend.services.strategy import storage

router = APIRouter()
db_manager = DatabaseManager()

IMPORT_FILE = File(...)


# Pydantic models for request/response
class StrategyCreateRequest(BaseModel):
    """Request payload for creating a strategy."""

    name: str
    description: Optional[str] = None
    category: Optional[str] = None
    code: str
    parameters: Optional[Dict[str, Any]] = None
    parameterTypes: Optional[Dict[str, str]] = None
    symbol: Optional[str] = None
    timeframe: Optional[str] = None
    type: Optional[str] = None
    moneyManagement: Optional[Dict[str, Any]] = None
    variables: Optional[Dict[str, Any]] = None
    variableTypes: Optional[Dict[str, str]] = None


class StrategyUpdateRequest(BaseModel):
    """Request payload for updating a strategy."""

    name: Optional[str] = None
    description: Optional[str] = None
    status: Optional[str] = None
    category: Optional[str] = None
    code: Optional[str] = None
    parameters: Optional[Dict[str, Any]] = None
    parameterTypes: Optional[Dict[str, str]] = None
    symbol: Optional[str] = None
    timeframe: Optional[str] = None
    type: Optional[str] = None
    moneyManagement: Optional[Dict[str, Any]] = None
    variables: Optional[Dict[str, Any]] = None
    variableTypes: Optional[Dict[str, str]] = None
    changelog: Optional[str] = None


class StrategyResponse(BaseModel):
    """Response model for strategy metadata."""

    id: int
    user_id: int
    name: str
    description: Optional[str]
    status: str
    category: Optional[str]
    is_public: bool
    active_version: Optional[str]
    active_version_id: Optional[int]
    created_at: str
    updated_at: str


class VersionResponse(BaseModel):
    """Response model for strategy versions."""

    id: int
    strategy_id: int
    version: str
    parameters: Dict[str, Any]
    changelog: Optional[str]
    created_at: str


class PerformanceSummaryRequest(BaseModel):
    """Request payload for summarizing performance."""

    trades: List[Dict[str, Any]]
    initial_balance: float = 10000.0


def _build_strategy_update_fields(request: StrategyUpdateRequest) -> Dict[str, Any]:
    update_fields: Dict[str, Any] = {}
    if request.name:
        update_fields["name"] = request.name
    if request.description is not None:
        update_fields["description"] = request.description
    if request.status:
        update_fields["status"] = request.status
    if request.category:
        update_fields["category"] = request.category
    return update_fields


def _next_strategy_version(db_versions: List[Dict[str, Any]]) -> str:
    if not db_versions:
        return "1.0.0"

    last_version = db_versions[0]["version"]
    major, minor, patch = map(int, last_version.split("."))
    return f"{major}.{minor}.{patch + 1}"


def _create_strategy_version(
    strategy_id: int,
    request: StrategyUpdateRequest,
    user_id: int,
    username: str,
    strategy_name: str,
):
    db_versions = db_manager.get_strategy_versions(strategy_id)
    new_version = _next_strategy_version(db_versions)

    file_path = storage.save_strategy(
        user_id=user_id,
        strategy_id=strategy_id,
        version=new_version,
        code=request.code or "",
        parameters=request.parameters or {},
        username=username,
        strategy_name=strategy_name,
        metadata={
            "name": request.name or strategy_name,
            "description": request.description,
            "symbol": request.symbol,
            "timeframe": request.timeframe,
            "type": request.type,
            "parameterTypes": request.parameterTypes,
            "moneyManagement": request.moneyManagement,
            "variables": request.variables,
            "variableTypes": request.variableTypes,
            "changelog": request.changelog or f"Updated to v{new_version}",
        },
    )

    db_manager.create_strategy_version(
        strategy_id=strategy_id,
        version=new_version,
        file_path=file_path,
        parameters=request.parameters,
        changelog=request.changelog,
        created_by=user_id,
    )

    return new_version


def _load_strategy_class(
    user_id: int, strategy_id: int, version_id: int
) -> tuple[Dict[str, Any], Any]:
    version = db_manager.get_strategy_version(version_id)
    strategy = db_manager.get_strategy(strategy_id)
    if version is None:
        raise ValueError(f"Strategy version {version_id} not found")
    if strategy is None:
        raise ValueError(f"Strategy {strategy_id} not found")

    user = db_manager.get_user(user_id=user_id)
    username = (user.get("username") if user else "") or ""
    strategy_name = (strategy.get("name") if strategy else "") or ""

    strategy_class = storage.load_strategy_class(
        user_id=user_id,
        strategy_id=strategy_id,
        version=version["version"],
        username=username,
        strategy_name=strategy_name,
    )

    return version, strategy_class


# Template endpoints
@router.get("/templates/{template_name}")
async def get_strategy_template(template_name: str) -> Dict[str, str]:
    """
    Get a strategy template by name.

    Available templates:
    - empty: Empty strategy template with TODO comments
    - trend_following: EMA crossover trend following strategy
    """
    try:
        # Map template names to files
        template_map = {
            "empty": "template_strategy.py",
            "trend_following": "../../../backend/data/strategies/trend_following.py",
        }

        if template_name not in template_map:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Template '{template_name}' not found. Available: {list(template_map.keys())}",
            )

        # Get template file path
        current_dir = os.path.dirname(os.path.abspath(__file__))
        project_root = os.path.abspath(os.path.join(current_dir, "../../.."))
        template_file = os.path.join(
            project_root, "apps", "strategy", "templates", template_map[template_name]
        )

        # Read template content
        if not os.path.exists(template_file):
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Template file not found: {template_file}",
            )

        with open(template_file, "r", encoding="utf-8") as f:
            code = f.read()

        logger.info(f"Serving template: {template_name}")

        return {
            "template_name": template_name,
            "code": code,
            "description": f"{template_name.replace('_', ' ').title()} Strategy Template",
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error loading template '{template_name}': {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to load template: {str(e)}",
        )


# Strategy CRUD endpoints
@router.post("/", response_model=StrategyResponse, status_code=status.HTTP_201_CREATED)
async def create_strategy(
    request: StrategyCreateRequest, user_id: int = 1
) -> StrategyResponse:
    """
    Create a new strategy.

    Note: In production, user_id would come from authentication token.
    For now, defaulting to user_id=1 for testing.
    """
    try:
        logger.info(f"Creating strategy: {request.name} for user {user_id}")

        # Create strategy in database
        strategy_id = db_manager.create_strategy(
            user_id=user_id,
            name=request.name,
            description=request.description,
            category=request.category,
            status="inactive",
            is_public=False,
        )

        # Get username for descriptive folder naming
        user = db_manager.get_user(user_id=user_id)
        username = user.get("username", "") if user else ""

        # Save strategy code to file (version 1.0.0)
        version = "1.0.0"
        file_path = storage.save_strategy(
            user_id=user_id,
            strategy_id=strategy_id,
            version=version,
            code=request.code,
            parameters=request.parameters,
            username=username,
            strategy_name=request.name,
            metadata={
                "name": request.name,
                "description": request.description,
                "symbol": request.symbol,
                "timeframe": request.timeframe,
                "type": request.type,
                "parameterTypes": request.parameterTypes,
                "moneyManagement": request.moneyManagement,
                "variables": request.variables,
                "variableTypes": request.variableTypes,
            },
        )

        # Create version record
        _ = db_manager.create_strategy_version(
            strategy_id=strategy_id,
            version=version,
            file_path=file_path,
            parameters=request.parameters,
            changelog="Initial version",
            created_by=user_id,
        )

        # Get created strategy
        strategy = db_manager.get_strategy(strategy_id)
        if strategy is None:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to load created strategy",
            )

        logger.info(f"Strategy created successfully: ID={strategy_id}")

        return StrategyResponse(**strategy)

    except Exception as e:
        logger.error(f"Error creating strategy: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to create strategy: {str(e)}",
        )


@router.get("/", response_model=List[StrategyResponse])
async def list_strategies(
    user_id: int = 1,
    strategy_status: Optional[str] = None,
    category: Optional[str] = None,
    include_shared: bool = False,
) -> List[StrategyResponse]:
    """List all strategies for a user."""
    try:
        strategies = db_manager.get_user_strategies(
            user_id=user_id,
            status=strategy_status,
            category=category,
            include_shared=include_shared,
        )

        return [StrategyResponse(**s) for s in strategies]

    except Exception as e:
        logger.error(f"Error listing strategies: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to list strategies: {str(e)}",
        )


@router.get("/{strategy_id}", response_model=StrategyResponse)
async def get_strategy(strategy_id: int) -> StrategyResponse:
    """Get a specific strategy."""
    try:
        strategy = db_manager.get_strategy(strategy_id)

        if not strategy:
            logger.warning(f"Strategy {strategy_id} not found")
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Strategy {strategy_id} not found",
            )

        return StrategyResponse(**strategy)

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting strategy: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get strategy: {str(e)}",
        )


@router.put("/{strategy_id}", response_model=StrategyResponse)
async def update_strategy(
    strategy_id: int, request: StrategyUpdateRequest, user_id: int = 1
) -> StrategyResponse:
    """
    Update a strategy.

    If code is provided, creates a new version.
    """
    try:
        # Get current strategy
        strategy = db_manager.get_strategy(strategy_id)
        if not strategy:
            logger.warning(f"Strategy {strategy_id} not found")
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Strategy {strategy_id} not found",
            )

        update_fields = _build_strategy_update_fields(request)
        if update_fields:
            db_manager.update_strategy(strategy_id, **update_fields)

        if request.code:
            user = db_manager.get_user(user_id=user_id)
            username = user.get("username", "") if user else ""
            strategy_name = request.name or strategy["name"]
            new_version = _create_strategy_version(
                strategy_id=strategy_id,
                request=request,
                user_id=user_id,
                username=username,
                strategy_name=strategy_name,
            )
            logger.info(
                f"New version created: {new_version} for strategy {strategy_id}"
            )

        # Get updated strategy
        updated_strategy = db_manager.get_strategy(strategy_id)
        if updated_strategy is None:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to load updated strategy",
            )

        return StrategyResponse(**updated_strategy)

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error updating strategy: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to update strategy: {str(e)}",
        )


@router.delete("/{strategy_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_strategy(strategy_id: int, user_id: int = 1) -> None:
    """Delete a strategy and all its versions."""
    try:
        # Get strategy info before deleting from database
        strategy = db_manager.get_strategy(strategy_id)

        if not strategy:
            logger.warning(f"Strategy {strategy_id} not found")
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Strategy {strategy_id} not found",
            )

        # Get username for folder path
        user = db_manager.get_user(user_id=user_id)
        username = user.get("username", "") if user else ""
        strategy_name = strategy.get("name", "") if strategy else ""

        # Delete from database
        success = db_manager.delete_strategy(strategy_id)

        if not success:
            logger.warning(f"Failed to delete strategy {strategy_id} from database")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Failed to delete strategy {strategy_id}",
            )

        # Delete files with username and strategy name for new folder structure
        storage.delete_strategy(
            user_id, strategy_id, username=username, strategy_name=strategy_name
        )

        logger.info(f"Strategy {strategy_id} deleted successfully")

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error deleting strategy: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to delete strategy: {str(e)}",
        )


# Version endpoints
@router.get("/{strategy_id}/versions", response_model=List[VersionResponse])
async def list_versions(strategy_id: int) -> List[VersionResponse]:
    """List all versions of a strategy."""
    try:
        versions = db_manager.get_strategy_versions(strategy_id)
        return [VersionResponse(**v) for v in versions]

    except Exception as e:
        logger.error(f"Error listing versions: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to list versions: {str(e)}",
        )


@router.get("/{strategy_id}/versions/{version_id}/code")
async def get_version_code(
    strategy_id: int, version_id: int, user_id: int = 1
) -> Dict[str, Any]:
    """Get the code for a specific version."""
    try:
        # Get version info
        version = db_manager.get_strategy_version(version_id)

        if not version:
            logger.warning(f"Version {version_id} not found")
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Version {version_id} not found",
            )

        # Get strategy info for name
        strategy = db_manager.get_strategy(strategy_id)
        strategy_name = strategy.get("name", "") if strategy else ""

        # Get user info for username
        user = db_manager.get_user(user_id=user_id)
        username = user.get("username", "") if user else ""

        # Load code and metadata from file
        code = storage.load_strategy_code(
            user_id, strategy_id, version["version"], username, strategy_name
        )
        metadata = (
            storage.load_strategy_metadata(
                user_id, strategy_id, version["version"], username, strategy_name
            )
            or {}
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

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting version code: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get version code: {str(e)}",
        )


@router.post("/{strategy_id}/versions/{version_id}/rollback")
async def rollback_version(strategy_id: int, version_id: int) -> Dict[str, str]:
    """Rollback to a specific version (make it the active version)."""
    try:
        # Update strategy's active version
        db_manager.update_strategy(strategy_id, active_version_id=version_id)

        logger.info(f"Strategy {strategy_id} rolled back to version {version_id}")

        return {"message": "Version rolled back successfully"}

    except Exception as e:
        logger.error(f"Error rolling back version: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to rollback version: {str(e)}",
        )


# Export/Import endpoints
@router.post("/{strategy_id}/export")
async def export_strategy(strategy_id: int, user_id: int = 1) -> FileResponse:
    """Export strategy as a zip file."""
    try:
        strategy = db_manager.get_strategy(strategy_id)

        if not strategy or not strategy["active_version"]:
            logger.warning(f"Strategy {strategy_id} or active version not found")
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Strategy {strategy_id} or active version not found",
            )

        # Create temp file for export
        temp_dir = tempfile.gettempdir()
        export_path = os.path.join(
            temp_dir, f"strategy_{strategy_id}_v{strategy['active_version']}.zip"
        )
        logger.debug(
            f"Exporting strategy {strategy_id} v{strategy['active_version']} to {export_path}"
        )

        # Get username for folder path
        user = db_manager.get_user(user_id=user_id)
        username = user.get("username", "") if user else ""

        # Export strategy
        zip_path = storage.export_strategy(
            user_id=user_id,
            strategy_id=strategy_id,
            version=strategy["active_version"],
            export_path=export_path,
            username=username,
            strategy_name=strategy["name"],
        )

        return FileResponse(
            zip_path, media_type="application/zip", filename=os.path.basename(zip_path)
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error exporting strategy: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to export strategy: {str(e)}",
        )


@router.post("/{strategy_id}/import")
async def import_strategy(
    strategy_id: int, file: UploadFile = IMPORT_FILE, user_id: int = 1
) -> Dict[str, str]:
    """Import strategy from a zip file."""
    try:
        # Save uploaded file to temp location
        temp_dir = tempfile.gettempdir()
        import_path = os.path.join(temp_dir, file.filename or "unknown.zip")

        with open(import_path, "wb") as f:
            content = await file.read()
            f.write(content)

        # Get strategy info for name
        strategy = db_manager.get_strategy(strategy_id)
        if not strategy:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Strategy {strategy_id} not found",
            )
        strategy_name = strategy.get("name", "")

        # Get user info for username
        user = db_manager.get_user(user_id=user_id)
        username = user.get("username", "") if user else ""

        # Determine next version
        versions = storage.list_versions(username=username, strategy_name=strategy_name)

        if versions:
            last_version = versions[0]
            major = int(last_version.split(".")[0])
            new_version = f"{major + 1}.0.0"  # Major version bump for imports
            logger.debug(
                f"Importing as new version {new_version} (previous: {last_version})"
            )
        else:
            new_version = "1.0.0"
            logger.debug(f"Importing as initial version {new_version}")

        # Import strategy
        file_path = storage.import_strategy(
            user_id=user_id,
            strategy_id=strategy_id,
            version=new_version,
            import_path=import_path,
            username=username,
            strategy_name=strategy_name,
        )

        # Load metadata if exists
        metadata = storage.load_strategy_metadata(
            user_id,
            strategy_id,
            new_version,
            username=username,
            strategy_name=strategy_name,
        )

        # Create version record
        db_manager.create_strategy_version(
            strategy_id=strategy_id,
            version=new_version,
            file_path=file_path,
            parameters=metadata.get("parameters", {}),
            changelog=f"Imported from {file.filename}",
            created_by=user_id,
        )
        logger.info(f"Strategy version created from import: {file.filename}")

        # Clean up temp file
        os.remove(import_path)

        logger.info(f"Strategy imported: version {new_version}")

        return {"message": "Strategy imported successfully", "version": new_version}

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error importing strategy: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to import strategy: {str(e)}",
        )

