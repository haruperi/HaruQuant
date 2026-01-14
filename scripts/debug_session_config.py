"""Debug helper for live session configuration building."""

import logging
import sys
from unittest.mock import MagicMock

# Mock MT5 before imports
sys.modules["MetaTrader5"] = MagicMock()

# Setup Logging
logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)


def debug_session(session_id=1):
    """Inspect session config and attempt engine initialization."""
    print(f"Debugging Session {session_id}...")

    from apps.live.session import LiveTradingSession
    from apps.sqlite.database_operations import DatabaseManager

    db = DatabaseManager()

    # Check if session exists
    session_data = db.get_live_session(session_id)
    if not session_data:
        print(f"Session {session_id} not found!")
        return

    print("Session Data:", dict(session_data))

    # Fetch strategies directly to inspect raw DB output
    strategies = db.get_session_strategies(session_id)
    print(f"Found {len(strategies)} strategies.")
    for i, s in enumerate(strategies):
        print(f"Strategy {i} raw keys:", list(s.keys()))
        print(f"Strategy {i} raw content:", dict(s))

    # Try to build config using LiveTradingSession logic
    dummy_client = MagicMock()
    dummy_client.is_connected.return_value = True
    session = LiveTradingSession(session_id, dummy_client, db)

    try:
        print("\nAttempting _build_engine_config...")
        config = session._build_engine_config(session_data)
        print("Config generated successfully.")

        # FORCE VALID STRATEGY TYPE FOR TESTING
        for s in config["strategies"]:
            s["strategy_type"] = "TrendFollowing"

        print("\nAttempting MultiStrategyEngine initialization...")
        from apps.live.engine import MultiStrategyEngine

        # Initialize engine
        engine = MultiStrategyEngine(config=config, client=dummy_client)

        # Mock methods called during initialize
        engine.portfolio_manager = MagicMock()
        dummy_client.get_symbol_info.return_value = MagicMock(
            lots_min=lambda: 0.01, lots_max=lambda: 100.0, lots_step=lambda: 0.01
        )

        # Call initialize
        result = engine.initialize()
        print(f"\nEngine initialize result: {result}")

        if not result:
            print("Engine initialization FAILED (returned False)")
        else:
            print("Engine initialization SUCCEEDED")

    except Exception as e:
        print("\nCRITICAL FAILURE during execution:")
        print(e)
        import traceback

        traceback.print_exc()


if __name__ == "__main__":
    debug_session(1)
