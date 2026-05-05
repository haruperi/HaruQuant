"""Authentication routes."""

from typing import Annotated, Optional

from fastapi import APIRouter, Header, HTTPException, status

from backend_retiring.api.auth_utils import authenticate_user, generate_token
from backend_retiring.api.models import AuthResponse, LoginRequest, RegisterRequest, UserResponse
from haruquant.utils import logger
from data.database.sqlite.database_operations import DatabaseManager, UserAlreadyExistsError

router = APIRouter()

# Initialize database manager
db_manager = DatabaseManager()


@router.post(
    "/register", response_model=UserResponse, status_code=status.HTTP_201_CREATED
)
async def register(request: RegisterRequest):
    """
    Register a new user.

    Creates a new user account with the provided information.
    """
    try:
        # Log the registration attempt
        logger.info(
            f"Registration attempt for username: {request.username}, email: {request.email}"
        )

        # Create user in database
        user_id = db_manager.create_user(
            email=request.email,
            username=request.username,
            password=request.password,
            full_name=request.full_name,
            is_superuser=False,
        )

        if user_id is None:
            logger.error(
                f"User creation failed: No user_id returned for {request.username}"
            )
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="User registration failed: could not create user.",
            )

        # Log successful registration
        logger.info(f"User registered successfully: {request.username} (ID: {user_id})")

        # Return user data
        return UserResponse(
            id=user_id,
            email=request.email,
            username=request.username,
            full_name=request.full_name,
            is_active=True,
            is_verified=False,
        )

    except UserAlreadyExistsError as e:
        error_msg = str(e)
        if "email" in error_msg.lower():
            logger.warning(
                f"Registration failed - email already exists: {request.email}"
            )
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Email already registered",
            )
        elif "username" in error_msg.lower():
            logger.warning(
                f"Registration failed - username already exists: {request.username}"
            )
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST, detail="Username already taken"
            )
        else:
            logger.error(f"Registration failed with integrity error: {e}")
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Registration failed. User might already exist.",
            )
    except Exception as e:
        logger.error(f"Registration error for {request.username}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="An error occurred during registration",
        )


@router.post("/login", response_model=AuthResponse)
async def login(request: LoginRequest):
    """
    Authenticate a user and return an access token.

    Validates username and password, then generates an access token.
    Requires user to be verified (is_verified=1) to login.
    """
    try:
        # Log the login attempt
        logger.info(f"Login attempt for username: {request.username}")

        # Authenticate user
        auth_result = authenticate_user(request.username, request.password, db_manager)

        # Handle different authentication statuses
        if auth_result["status"] == "invalid":
            logger.warning(
                f"Failed login attempt for username: {request.username} - Invalid credentials"
            )
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid username or password",
                headers={"WWW-Authenticate": "Bearer"},
            )

        elif auth_result["status"] == "inactive":
            logger.warning(
                f"Failed login attempt for username: {request.username} - Account inactive"
            )
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Your account has been deactivated. Please contact the administrator.",
            )

        elif auth_result["status"] == "not_verified":
            logger.warning(
                f"Failed login attempt for username: {request.username} - Account not verified"
            )
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Your account is not verified. Please contact the administrator to verify your account.",
            )

        elif auth_result["status"] == "success":
            user_data = auth_result["user"]

            # Generate token
            token = generate_token(user_data["id"], db_manager)

            # Log successful login
            logger.info(
                f"User logged in successfully: {request.username} (ID: {user_data['id']})"
            )

            # Return token and user data
            return AuthResponse(  # nosec B106 - OAuth2 token type, not a password
                access_token=token, token_type="bearer", user=UserResponse(**user_data)
            )

        else:
            # Unknown status
            logger.error(f"Unknown authentication status: {auth_result['status']}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="An error occurred during login",
            )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Login error for {request.username}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="An error occurred during login",
        )


@router.post("/logout")
async def logout(authorization: Annotated[Optional[str], Header()] = None):
    """
    Logout the current user.

    Invalidates the session token in the database.
    """
    if not authorization or not authorization.startswith("Bearer "):
        # If no token provided, just return success (already logged out effectively)
        return {"message": "Logged out successfully"}

    token = authorization.replace("Bearer ", "")

    # Invalidate token in DB
    from backend_retiring.api.auth_utils import invalidate_token

    invalidate_token(token, db_manager)

    logger.info("Logout request received and session invalidated")
    return {"message": "Logged out successfully"}

