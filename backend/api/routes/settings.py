"""Settings routes."""

from fastapi import APIRouter, Header, HTTPException, status

from backend.api.auth_utils import verify_token
from backend.api.models import UpdateUserSettingsRequest, UserSettingsResponse
from services.utils.logger import logger
from backend.data.database.sqlite.database_operations import DatabaseManager

router = APIRouter()

# Initialize database manager
db_manager = DatabaseManager()
AUTH_HEADER = Header(None)


def get_user_id_from_token(authorization: str) -> int:
    """
    Extract and verify user ID from authorization token.

    Args:
        authorization: Authorization header value

    Returns:
        User ID if token is valid

    Raises:
        HTTPException: If token is invalid or missing
    """
    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Missing or invalid authorization header",
            headers={"WWW-Authenticate": "Bearer"},
        )

    token = authorization.replace("Bearer ", "")
    user_id = verify_token(token, db_manager)

    if not user_id:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired token",
            headers={"WWW-Authenticate": "Bearer"},
        )

    return user_id


async def _get_settings(authorization: str = AUTH_HEADER):
    """
    Get user settings.

    Requires authentication via Bearer token.
    """
    try:
        # Verify token and get user ID
        user_id = get_user_id_from_token(authorization)

        # Get settings from database
        settings = db_manager.get_user_settings(user_id)

        if not settings:
            logger.warning(f"Settings not found for user_id: {user_id}")
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND, detail="Settings not found"
            )

        logger.info(f"Settings retrieved for user_id: {user_id}")
        return UserSettingsResponse(**settings)

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting settings: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="An error occurred while retrieving settings",
        )


@router.get("/", response_model=UserSettingsResponse)
async def get_settings(authorization: str = AUTH_HEADER):
    """Get settings (slash route)."""
    return await _get_settings(authorization)


@router.get("", response_model=UserSettingsResponse)
async def get_settings_no_slash(authorization: str = AUTH_HEADER):
    """Get settings (no-slash route)."""
    return await _get_settings(authorization)


@router.put("/", response_model=UserSettingsResponse)
async def update_settings(
    request: UpdateUserSettingsRequest, authorization: str = AUTH_HEADER
):
    """
    Update user settings.

    Requires authentication via Bearer token.
    Only provided fields will be updated.
    """
    try:
        # Verify token and get user ID
        user_id = get_user_id_from_token(authorization)

        # Build settings dict from request (only include non-None values)
        settings_update = {}
        for field, value in request.dict(exclude_unset=True).items():
            if value is not None:
                settings_update[field] = value

        if not settings_update:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST, detail="No settings to update"
            )

        # Update settings
        success = db_manager.update_user_settings(user_id, settings_update)

        if not success:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to update settings",
            )

        # Return updated settings
        updated_settings = db_manager.get_user_settings(user_id)
        logger.info(f"Settings updated for user_id: {user_id}")

        if updated_settings is None:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to load updated settings",
            )

        return UserSettingsResponse(**updated_settings)

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error updating settings: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="An error occurred while updating settings",
        )

