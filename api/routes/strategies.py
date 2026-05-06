"""Strategy routes for managing trading strategies."""

import inspect
import os
import tempfile
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, File, HTTPException, UploadFile, status
from fastapi.responses import FileResponse
from pydantic import BaseModel

from haruquant.utils import logger
from data.database.sqlite.database_operations import DatabaseManager
from haruquant.strategy import storage
from haruquant.strategy import StrategyCatalogCreateRequest, StrategyCatalogService, StrategyCatalogUpdateRequest
from haruquant.strategy import EmaCrossBaselineStrategy, NaiveMomentumStrategy, RsiBaselineStrategy

import haruquant as hqt

router = APIRouter()
db_manager = DatabaseManager()
catalog = hqt.Catalog(db_manager=db_manager)

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
    governance_strategy_id: Optional[str] = None
    lifecycle_state: Optional[str] = None
    code_hash: Optional[str] = None
    parameter_hash: Optional[str] = None
    artifact_root: Optional[str] = None
    strategy_family: Optional[str] = None
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
            "trend_following": "template_strategy.py",
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
            project_root,
            "backend_retiring",
            "services",
            "strategy",
            "templates",
            template_map[template_name],
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
        strategy = catalog.create(
            hqt.StrategyCatalogCreateRequest(
                name=request.name,
                description=request.description,
                category=request.category,
                code=request.code,
                parameters=request.parameters,
                parameter_types=request.parameterTypes,
                symbol=request.symbol,
                timeframe=request.timeframe,
                strategy_type=request.type,
                money_management=request.moneyManagement,
                variables=request.variables,
                variable_types=request.variableTypes,
            ),
            user_id=user_id,
        )
        logger.info(f"Strategy created successfully: ID={strategy['id']}")
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
        strategies = catalog.list(
            user_id=user_id,
            status=strategy_status,
            category=category,
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
        strategy = catalog.get(strategy_id)

        return StrategyResponse(**strategy)

    except LookupError as e:
        logger.warning(str(e))
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e),
        ) from e
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
        updated_strategy = catalog.update(
            strategy_id,
            hqt.StrategyCatalogUpdateRequest(
                name=request.name,
                description=request.description,
                status=request.status,
                category=request.category,
                code=request.code,
                parameters=request.parameters,
                parameter_types=request.parameterTypes,
                symbol=request.symbol,
                timeframe=request.timeframe,
                strategy_type=request.type,
                money_management=request.moneyManagement,
                variables=request.variables,
                variable_types=request.variableTypes,
                changelog=request.changelog,
            ),
            user_id=user_id,
        )

        return StrategyResponse(**updated_strategy)

    except LookupError as e:
        logger.warning(str(e))
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e),
        ) from e
    except PermissionError as e:
        logger.warning(str(e))
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=str(e),
        ) from e
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
        catalog.delete(strategy_id, user_id=user_id)

        logger.info(f"Strategy {strategy_id} deleted successfully")

    except LookupError as e:
        logger.warning(str(e))
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e),
        ) from e
    except PermissionError as e:
        logger.warning(str(e))
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=str(e),
        ) from e
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
        versions = catalog.list_versions(strategy_id)
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
        return catalog.get_version_code(
            strategy_id=strategy_id,
            version_id=version_id,
            user_id=user_id,
        )

    except LookupError as e:
        logger.warning(str(e))
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e),
        ) from e
    except FileNotFoundError as e:
        logger.warning(str(e))
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e),
        ) from e
    except PermissionError as e:
        logger.warning(str(e))
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=str(e),
        ) from e
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting version code: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get version code: {str(e)}",
        )


@router.post("/{strategy_id}/versions/{version_id}/rollback")
async def rollback_version(
    strategy_id: int, version_id: int, user_id: int = 1
) -> Dict[str, str]:
    """Rollback to a specific version (make it the active version)."""
    try:
        catalog.rollback(
            strategy_id=strategy_id,
            version_id=version_id,
            user_id=user_id,
        )

        logger.info(f"Strategy {strategy_id} rolled back to version {version_id}")

        return {"message": "Version rolled back successfully"}

    except LookupError as e:
        logger.warning(str(e))
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e),
        ) from e
    except PermissionError as e:
        logger.warning(str(e))
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=str(e),
        ) from e
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
        zip_path = catalog.export(strategy_id=strategy_id, user_id=user_id)
        return FileResponse(
            zip_path, media_type="application/zip", filename=os.path.basename(zip_path)
        )

    except LookupError as e:
        logger.warning(str(e))
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e),
        ) from e
    except PermissionError as e:
        logger.warning(str(e))
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=str(e),
        ) from e
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

        new_version = catalog.import_zip(
            strategy_id=strategy_id,
            import_path=import_path,
            filename=file.filename or "unknown.zip",
            user_id=user_id,
        )
        logger.info(f"Strategy version created from import: {file.filename}")

        # Clean up temp file
        os.remove(import_path)

        logger.info(f"Strategy imported: version {new_version}")

        return {"message": "Strategy imported successfully", "version": new_version}

    except LookupError as e:
        logger.warning(str(e))
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e),
        ) from e
    except PermissionError as e:
        logger.warning(str(e))
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=str(e),
        ) from e
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error importing strategy: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to import strategy: {str(e)}",
        )

