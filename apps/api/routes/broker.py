"""Broker routes."""

from fastapi import APIRouter

from apps.api.models import BrokerStatusResponse
from apps.logger import logger
from apps.mt5.client import MT5Client

router = APIRouter()


# Global client instance
# We strictly initialize ONCE at module level.
# The endpoint will then check status and reconnect only if needed.
# Note: MT5Client() __init__ automatically calls initialize(), so this will try to connect on startup.
client = MT5Client()


@router.get("/", response_model=BrokerStatusResponse)
async def get_broker_status():
    """
    Get current broker connection status and account info.

    Uses a singleton client to avoid re-initializing on every request.
    """
    global client

    try:
        # 1. Check if connected
        if not client.is_connected():
            logger.info("Broker disconnected, attempting to reconnect...")
            # Attempt to reconnect/initialize
            if not client.initialize():
                # Failed to connect
                return BrokerStatusResponse(
                    status="Disconnected",
                    broker_name="None",
                    equity=0.0,
                    balance=0.0,
                    margin_level=0.0,
                    free_margin=0.0,
                )

        # 2. If we are here, we should be connected or at least initialized enough to try fetching info
        account_info = client.get_account_info()

        if not account_info:
            # Double check connection if info fetch failed
            if not client.is_connected():
                return BrokerStatusResponse(
                    status="Disconnected",
                    broker_name="None",
                    equity=0.0,
                    balance=0.0,
                    margin_level=0.0,
                    free_margin=0.0,
                )

            return BrokerStatusResponse(
                status="Connected",
                broker_name="Unknown (Error fetching info)",
                equity=0.0,
                balance=0.0,
                margin_level=0.0,
                free_margin=0.0,
            )

        return BrokerStatusResponse(
            status="Connected",
            broker_name=client.account_server or "Unknown Broker",
            equity=account_info.get("equity", 0.0),
            balance=account_info.get("balance", 0.0),
            margin_level=account_info.get("margin_level", 0.0),
            free_margin=account_info.get("margin_free", 0.0),
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
    finally:
        # We might NOT want to shutdown here if we want to keep the connection 'alive'
        # for other requests, but for a simple stateless API request/response
        # that instantiates its own client, we should probably clean up
        # OR rely on the underlying library to handle persistent connections.
        # Given the `MT5Client` class, `initialize` calls `mt5.initialize`, which is global.
        # Calling shutdown() would kill the connection for everyone.
        # So we probably SHOULD NOT call shutdown() if we expect other parts of the app to use it concurrently,
        # OR if we want it to remain ready.
        # However, if we don't 'shutdown', we leave it running.
        # For now, let's leave it running as checking status shouldn't kill the link.
        pass
