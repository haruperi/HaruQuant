"""
Script to simulate user settings updates.

This script allows updating user settings via command line arguments,
supporting complex JSON objects for credentials and preferences.
"""

import argparse
import json
import os
import sys

# Add parent directory to path to allow imports from apps
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../..")))

from apps.utils.logger import logger  # noqa: E402
from apps.sqlite.users import UserManager  # noqa: E402


def update_settings(username, **kwargs):
    """Update user settings in the database."""
    db_path = "data/database/haruquant.db"

    # Initialize UserManager
    user_manager = UserManager()
    user_manager.db_path = db_path

    try:
        print(f"Attempting to update settings for user: {username}")

        # 1. Resolve User ID
        user = user_manager.get_user(username=username)
        if not user:
            print(f"Error: User '{username}' not found.")
            return False

        user_id = user["id"]

        # 2. Filter out None values
        settings_to_update = {k: v for k, v in kwargs.items() if v is not None}

        if not settings_to_update:
            print("No settings provided to update.")
            return False

        # 3. Update Settings
        print(f"Updating settings: {settings_to_update}")
        success = user_manager.update_user_settings(user_id, settings_to_update)

        if success:
            print("Settings updated successfully!")

            # Verify update
            updated_settings = user_manager.get_user_settings(user_id)
            if updated_settings:
                print("Current Settings:")
                for key, val in updated_settings.items():
                    if key in settings_to_update:
                        print(f"  {key}: {val}")
            else:
                print("Could not retrieve updated settings.")

            return True
        else:
            print("Failed to update settings.")
            return False

    except Exception as e:
        print(f"An unexpected error occurred: {e}")
        logger.exception("Settings update failed")
        return False


def parse_json_arg(arg_value, arg_name):
    """
    Parse a JSON string argument.

    Args:
        arg_value: The JSON string to parse
        arg_name: The name of the argument for error messaging

    Returns:
        The parsed JSON object or None if arg_value is None
    """
    if not arg_value:
        return None
    try:
        return json.loads(arg_value)
    except json.JSONDecodeError as e:
        print(f"Error parsing {arg_name}: {e}")
        sys.exit(1)


def main():
    """Parse arguments and update settings."""
    parser = argparse.ArgumentParser(description="Simulate User Settings Update")
    parser.add_argument("--username", help="Username", required=True)
    parser.add_argument("--theme", help="UI Theme (e.g., dark, light, system)")
    parser.add_argument("--language", help="Language code (e.g., en, ja)")
    parser.add_argument("--timezone", help="Timezone string")
    parser.add_argument("--log-verbosity", help="Log verbosity (debug, info, warning)")
    parser.add_argument("--performance-mode", help="Performance mode")
    parser.add_argument(
        "--broker-credentials", help="Broker credentials as JSON string"
    )
    parser.add_argument(
        "--trading-preferences", help="Trading preferences as JSON string"
    )
    parser.add_argument("--notifications", help="Notifications settings as JSON string")
    parser.add_argument("--alert-triggers", help="Alert triggers as JSON string")

    args = parser.parse_args()

    # Parse JSON fields
    broker_credentials = parse_json_arg(args.broker_credentials, "broker credentials")
    trading_preferences = parse_json_arg(
        args.trading_preferences, "trading preferences"
    )
    notifications = parse_json_arg(args.notifications, "notifications")
    alert_triggers = parse_json_arg(args.alert_triggers, "alert triggers")

    update_settings(
        username=args.username,
        theme=args.theme,
        language=args.language,
        timezone=args.timezone,
        log_verbosity=args.log_verbosity,
        performance_mode=args.performance_mode,
        broker_credentials=broker_credentials,
        trading_preferences=trading_preferences,
        notifications=notifications,
        alert_triggers=alert_triggers,
    )


if __name__ == "__main__":
    main()

