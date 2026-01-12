"""Broker routes."""

import json
from typing import Annotated, Any, Dict, Optional, Union, cast

from fastapi import APIRouter, Header

from apps.api.auth_utils import verify_token
from apps.api.models import BrokerStatusResponse
from apps.logger import logger
from apps.mt5.client import MT5Client
from apps.sqlite.database_operations import DatabaseManager

router = APIRouter()
db_manager = DatabaseManager()

# Global client instance
client = MT5Client()


def _parse_credentials(credentials: Union[str, Dict[str, Any], None]) -> Dict[str, Any]:
    """Parse broker credentials from various formats."""
    if not credentials:
        return {}

    if isinstance(credentials, dict):
        return credentials

    if isinstance(credentials, str):
        try:
            return cast(Dict[str, Any], json.loads(credentials))
        except json.JSONDecodeError:
            logger.error("Failed to parse broker credentials JSON")
            return {}

    return {}


def _update_mt5_connection(user_id: int) -> None:
    """Update and reconnect MT5 client if user credentials differ."""
    global client
    try:
        # Use the helper method which handles the nested accounts list logic correctly
        creds = db_manager.get_mt5_credentials(user_id) or {}

        login = creds.get("login")
        password = creds.get("password")
        server = creds.get("server")
        path = creds.get("path", "")

        # Check if we have valid credentials to use
        if login and password and server:
            # Convert login to int if string
            try:
                login_int = int(login)
            except (ValueError, TypeError):
                login_int = 0

            # Update Client if credentials changed or not connected
            # We compare current client state with DB credentials
            credentials_changed = (
                client.account_login != login_int or client.account_server != server
            )

            if credentials_changed or not client.is_connected():
                if credentials_changed:
                    logger.info(f"Updating MT5 client credentials for user {user_id}")
                    # If connection details changed, simple re-init might work,
                    # but explicit update is safer
                    client.account_login = login_int
                    client.account_password = password
                    client.account_server = server
                    if path:
                        client.path = path

                    # Force re-initialization
                    client.shutdown()

                logger.info("Connecting to MT5...")
                client.initialize()

    except Exception as e:
        logger.error(f"Error fetching/applying user settings: {e}")


@router.get("/", response_model=BrokerStatusResponse)
async def get_broker_status(authorization: Annotated[Optional[str], Header()] = None):
    """
    Get current broker connection status and account info.

    Authenticated endpoint:
    1. Verifies user token.
    2. Fetches user settings (broker credentials).
    3. Initializes MT5 connection with those credentials if needed.
    """
    global client

    # 1. Authenticate User
    user_id = None
    if authorization and authorization.startswith("Bearer "):
        token = authorization.replace("Bearer ", "")
        user_id = verify_token(token, db_manager)

    # If not authenticated, we can return disconnected or attempt default/global connection
    # But for invalid "login" error fix, we really need the user's credentials.
    # We will proceed if we have a user_id to try and connect.

    if user_id:
        _update_mt5_connection(user_id)

    # 4. Return Status
    try:
        if not client.is_connected() and client.account_login and client.account_server:
            # Last ditch attempt to initialize if it was already configured but dropped
            client.initialize()

        if not client.is_connected():
            return BrokerStatusResponse(
                status="Disconnected",
                broker_name="None",
                equity=0.0,
                balance=0.0,
                margin_level=0.0,
                free_margin=0.0,
            )

        account_info = client.get_account_info()
        if not account_info:
            return BrokerStatusResponse(
                status="Connected",
                broker_name=client.account_server or "Unknown",
                equity=0.0,
                balance=0.0,
                margin_level=0.0,
                free_margin=0.0,
            )

        return BrokerStatusResponse(
            status="Connected",
            broker_name=client.account_server or "Unknown Broker",
            equity=float(account_info.get("equity", 0.0)),
            balance=float(account_info.get("balance", 0.0)),
            margin_level=float(account_info.get("margin_level", 0.0)),
            free_margin=float(account_info.get("margin_free", 0.0)),
        )

    except Exception as e:
        logger.error(f"Error getting broker status: {e}")
        return BrokerStatusResponse(
            status="Error",
            broker_name="Connection Error",
            equity=0.0,
            balance=0.0,
            margin_level=0.0,
            free_margin=0.0,
        )
