"""
Quick setup example for notification credentials.

This script provides a quick way to set up example notification credentials
for testing purposes.
"""

import json
import sys
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent.parent.parent.parent
sys.path.insert(0, str(project_root))

from apps.sqlite import SQLiteDatabase


def setup_example_credentials(user_id: int):
    """
    Set up example notification credentials for a user.

    Note: Replace with real credentials before using in production!
    """
    print("=" * 70)
    print("QUICK NOTIFICATION SETUP - EXAMPLE CREDENTIALS")
    print("=" * 70)
    print("\n⚠ WARNING: This sets up EXAMPLE credentials!")
    print("Replace these with your real credentials before use.\n")

    # Connect to database
    db_path = "data/database/haruquant.db"
    db = SQLiteDatabase(db_path=db_path)

    # Check if user exists
    user = db.get_user(user_id=user_id)
    if not user:
        print(f"\n✗ Error: User with ID {user_id} not found!")
        print("\nCreate a user first:")
        print("  python tests/usage/sqlite/usage_init.py")
        return False

    print(f"Setting up for user: {user['username']}")

    # Example notification configuration
    notifications = {
        "email": {
            "enabled": False,  # Set to True and add real credentials
            "smtp_host": "smtp.gmail.com",
            "smtp_port": 587,
            "smtp_user": "your_email@gmail.com",
            "smtp_password": "your_app_password_here",
            "recipients": ["recipient@example.com"],
            "use_tls": True,
        },
        "telegram": {
            "enabled": False,  # Set to True and add real credentials
            "bot_token": "123456:ABC-DEF1234ghIkl-zyx57W2v1u123ew11",
            "chat_ids": ["123456789"],
            "parse_mode": "HTML",
            "disable_web_page_preview": True,
            "disable_notification": False,
        },
        "sms": {
            "enabled": False,  # Set to True and add real credentials
            "account_sid": "ACxxxxxxxxxxxxxxxxxxxxx",
            "auth_token": "your_auth_token_here",
            "from_number": "+1234567890",
            "recipients": ["+1234567891"],
        },
    }

    # Update database
    try:
        success = db.update_user_settings(
            user_id=user_id, settings={"notifications": notifications}
        )

        if success:
            print("\n✓ Example credentials saved to database!")
            print("\nNext steps:")
            print("1. Update the credentials with your real values")
            print("2. Enable the channels you want to use (set enabled: true)")
            print("3. Run: python tests/usage/notifications/setup_notifications.py")
            print("   OR update directly in database")
            print()
            print("Example SQL to enable and update Telegram:")
            print(
                f"""
UPDATE user_settings
SET notifications = json_set(
    notifications,
    '$.telegram.enabled', true,
    '$.telegram.bot_token', 'YOUR_REAL_BOT_TOKEN',
    '$.telegram.chat_ids', json_array('YOUR_CHAT_ID')
)
WHERE user_id = {user_id};
            """
            )

            print("\nStored structure:")
            print(json.dumps(notifications, indent=2))

            return True

        else:
            print("\n✗ Failed to save credentials")
            return False

    except Exception as e:
        print(f"\n✗ Error: {e}")
        import traceback

        traceback.print_exc()
        return False


def show_manual_setup():
    """Show manual setup instructions."""
    print("\n" + "=" * 70)
    print("MANUAL SETUP INSTRUCTIONS")
    print("=" * 70)

    instructions = """
To manually set up notification credentials:

1. **Get Your Telegram Bot Token:**
   - Open Telegram, search for @BotFather
   - Send: /newbot
   - Follow prompts and save the bot token

2. **Get Your Telegram Chat ID:**
   - Send a message to your bot
   - Visit: https://api.telegram.org/bot<BOT_TOKEN>/getUpdates
   - Find your chat ID in the response

3. **Update Database:**

   Option A - Using SQL:
   ```sql
   UPDATE user_settings
   SET notifications = '{
     "email": {
       "enabled": true,
       "smtp_host": "smtp.gmail.com",
       "smtp_port": 587,
       "smtp_user": "your_email@gmail.com",
       "smtp_password": "your_app_password",
       "recipients": ["alerts@example.com"],
       "use_tls": true
     },
     "telegram": {
       "enabled": true,
       "bot_token": "YOUR_BOT_TOKEN",
       "chat_ids": ["YOUR_CHAT_ID"],
       "parse_mode": "HTML"
     },
     "sms": {
       "enabled": false
     }
   }'
   WHERE user_id = 1;
   ```

   Option B - Using Python:
   ```python
   from apps.sqlite import SQLiteDatabase

   db = SQLiteDatabase(db_path="data/database/haruquant.db")

   notifications = {
       "email": {...},
       "telegram": {...}
   }

   db.update_user_settings(user_id=1, settings={"notifications": notifications})
   ```

   Option C - Use Interactive Script:
   ```bash
   python tests/usage/notifications/setup_notifications.py
   ```

4. **Test Your Setup:**
   ```bash
   python tests/usage/notifications/test_database_notifications.py
   ```
"""

    print(instructions)


def main():
    """Main function."""
    print("\n" + "=" * 70)
    print("NOTIFICATION QUICK SETUP")
    print("=" * 70)

    print("\nThis script helps you set up notification credentials.")
    print("\nOptions:")
    print("1. Set up example credentials (needs manual update)")
    print("2. Show manual setup instructions")
    print("3. Exit")

    choice = input("\nSelect option (1-3): ")

    if choice == "1":
        user_id = int(input("\nEnter user ID: "))
        success = setup_example_credentials(user_id)

        if success:
            print("\n" + "=" * 70)
            print("TESTING")
            print("=" * 70)
            test = input("\nTest the setup now? (y/n): ").lower() == "y"

            if test:
                print("\nNote: Tests will fail until you add real credentials!")
                print("Update the database first, then run:")
                print("  python tests/usage/notifications/test_database_notifications.py")

    elif choice == "2":
        show_manual_setup()
    else:
        print("\nExiting...")


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n\nSetup cancelled by user.")
    except Exception as e:
        print(f"\n✗ Error: {e}")
        import traceback

        traceback.print_exc()
