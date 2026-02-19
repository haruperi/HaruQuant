"""
Test notification loading from database.

This script demonstrates how to load and test notification credentials from the database.
"""

import sys
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent.parent.parent.parent
sys.path.insert(0, str(project_root))

from apps.live.notification_adapter import LiveTradingNotifier
from apps.sqlite import SQLiteDatabase


def test_database_credentials():
    """Test loading notification credentials from database."""
    print("=" * 70)
    print("TESTING NOTIFICATION CREDENTIALS FROM DATABASE")
    print("=" * 70)

    # Get user ID
    user_id = int(input("\nEnter user ID to test: "))

    # Connect to database
    db_path = "data/database/haruquant.db"
    db = SQLiteDatabase(db_path=db_path)

    # Check if user exists
    user = db.get_user(user_id=user_id)
    if not user:
        print(f"\n✗ Error: User with ID {user_id} not found!")
        return

    print(f"\n✓ Testing notifications for user: {user['username']}")

    # Display stored credentials (without passwords)
    print("\n" + "-" * 70)
    print("STORED NOTIFICATION SETTINGS")
    print("-" * 70)

    email_creds = db.get_email_credentials(user_id)
    if email_creds:
        print("\n✓ Email Configuration Found:")
        print(f"  - SMTP Host: {email_creds['smtp_host']}")
        print(f"  - SMTP Port: {email_creds['smtp_port']}")
        print(f"  - SMTP User: {email_creds['smtp_user']}")
        print(f"  - Recipients: {', '.join(email_creds['recipients'])}")
        print(f"  - Use TLS: {email_creds.get('use_tls', True)}")
    else:
        print("\n✗ No email configuration found")

    telegram_creds = db.get_telegram_credentials(user_id)
    if telegram_creds:
        print("\n✓ Telegram Configuration Found:")
        print(f"  - Bot Token: {telegram_creds['bot_token'][:20]}...")
        print(f"  - Chat IDs: {', '.join(telegram_creds['chat_ids'])}")
        print(f"  - Parse Mode: {telegram_creds['parse_mode']}")
    else:
        print("\n✗ No Telegram configuration found")

    # Create notifier from database
    print("\n" + "-" * 70)
    print("CREATING NOTIFIER FROM DATABASE")
    print("-" * 70)

    try:
        notifier = LiveTradingNotifier.from_database(user_id=user_id, db_path=db_path)
        print(f"\n✓ Notifier created: {notifier}")

        if not notifier.enabled:
            print("\n⚠ Warning: Notifier is disabled (no valid credentials found)")
            return

        # Test connections
        print("\n" + "-" * 70)
        print("TESTING CONNECTIONS")
        print("-" * 70)

        test_result = notifier.test_connection()
        if test_result:
            print("\n✓ Connection test passed!")
        else:
            print("\n✗ Connection test failed")

        # Send test notifications
        print("\n" + "-" * 70)
        print("SENDING TEST NOTIFICATIONS")
        print("-" * 70)

        send_tests = input("\nSend test notifications? (y/n): ").lower() == "y"

        if send_tests:
            print("\n1. Testing startup notification...")
            notifier.notify_startup(
                symbol="EURUSD", timeframe="M15", volume=0.01
            )

            print("2. Testing trading signal...")
            notifier.notify_signal(
                signal={
                    "signal": "buy",
                    "time": "2024-01-01 10:00:00",
                    "reason": "Test signal from database",
                    "entry_price": 1.0850,
                    "symbol": "EURUSD",
                },
                executed=True,
            )

            print("3. Testing system alert...")
            notifier.notify_safety_violation("Test safety violation")

            print("\n✓ Test notifications sent! Check your email/Telegram.")

    except Exception as e:
        print(f"\n✗ Error creating notifier: {e}")
        import traceback

        traceback.print_exc()


def show_notification_structure():
    """Show the expected JSON structure for notifications."""
    print("\n" + "=" * 70)
    print("EXPECTED DATABASE STRUCTURE")
    print("=" * 70)

    structure = """
The 'notifications' column in 'user_settings' should contain JSON like:

{
  "email": {
    "enabled": true,
    "smtp_host": "smtp.gmail.com",
    "smtp_port": 587,
    "smtp_user": "your_email@gmail.com",
    "smtp_password": "your_app_password",
    "recipients": ["recipient1@example.com", "recipient2@example.com"],
    "use_tls": true
  },
  "telegram": {
    "enabled": true,
    "bot_token": "YOUR_BOT_TOKEN",
    "chat_ids": ["CHAT_ID_1", "CHAT_ID_2"],
    "parse_mode": "HTML",
    "disable_web_page_preview": true,
    "disable_notification": false
  },
  "sms": {
    "enabled": false,
    "account_sid": "YOUR_TWILIO_SID",
    "auth_token": "YOUR_TWILIO_TOKEN",
    "from_number": "+1234567890",
    "recipients": ["+1234567891", "+1234567892"]
  }
}

To set this up:
1. Run: python tests/usage/notifications/setup_notifications.py
   OR
2. Use SQL:
   UPDATE user_settings
   SET notifications = '<json_above>'
   WHERE user_id = <your_user_id>;
"""

    print(structure)


def main():
    """Main function."""
    print("\n" + "=" * 70)
    print("NOTIFICATION DATABASE INTEGRATION TEST")
    print("=" * 70)

    print("\nOptions:")
    print("1. Test notification credentials from database")
    print("2. Show expected database structure")
    print("3. Exit")

    choice = input("\nSelect option (1-3): ")

    if choice == "1":
        test_database_credentials()
    elif choice == "2":
        show_notification_structure()
    else:
        print("\nExiting...")


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n\nTest cancelled by user.")
    except Exception as e:
        print(f"\n✗ Error: {e}")
        import traceback

        traceback.print_exc()
