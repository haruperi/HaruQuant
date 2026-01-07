"""
Setup notification credentials in the database.

This script helps you configure email and Telegram notifications for a user.
"""

import json
import sys
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent.parent.parent.parent
sys.path.insert(0, str(project_root))

from apps.sqlite import SQLiteDatabase


def setup_email_notifications(db: SQLiteDatabase, user_id: int):
    """Setup email notifications for a user."""
    print("\n" + "=" * 60)
    print("EMAIL NOTIFICATION SETUP")
    print("=" * 60)

    enabled = input("Enable email notifications? (y/n): ").lower() == "y"

    if not enabled:
        print("Email notifications disabled.")
        return {"enabled": False}

    print("\nEnter SMTP details:")
    smtp_host = input("SMTP Host (e.g., smtp.gmail.com): ")
    smtp_port = int(input("SMTP Port (default 587): ") or "587")
    smtp_user = input("SMTP Username/Email: ")
    smtp_password = input("SMTP Password/App Password: ")

    recipients_input = input("Recipients (comma-separated): ")
    recipients = [r.strip() for r in recipients_input.split(",")]

    use_tls = input("Use TLS? (y/n, default y): ").lower() != "n"

    return {
        "enabled": True,
        "smtp_host": smtp_host,
        "smtp_port": smtp_port,
        "smtp_user": smtp_user,
        "smtp_password": smtp_password,
        "recipients": recipients,
        "use_tls": use_tls,
    }


def setup_telegram_notifications(db: SQLiteDatabase, user_id: int):
    """Setup Telegram notifications for a user."""
    print("\n" + "=" * 60)
    print("TELEGRAM NOTIFICATION SETUP")
    print("=" * 60)

    enabled = input("Enable Telegram notifications? (y/n): ").lower() == "y"

    if not enabled:
        print("Telegram notifications disabled.")
        return {"enabled": False}

    print("\nHow to get your Telegram credentials:")
    print("1. Create a bot via @BotFather on Telegram")
    print("2. Get your bot token from @BotFather")
    print("3. Send a message to your bot")
    print("4. Visit: https://api.telegram.org/bot<YOUR_BOT_TOKEN>/getUpdates")
    print("5. Find your chat ID in the response")
    print()

    bot_token = input("Bot Token: ")
    chat_ids_input = input("Chat IDs (comma-separated): ")
    chat_ids = [cid.strip() for cid in chat_ids_input.split(",")]

    parse_mode = input("Parse Mode (HTML/Markdown/MarkdownV2, default HTML): ") or "HTML"

    return {
        "enabled": True,
        "bot_token": bot_token,
        "chat_ids": chat_ids,
        "parse_mode": parse_mode,
        "disable_web_page_preview": True,
        "disable_notification": False,
    }


def setup_sms_notifications(db: SQLiteDatabase, user_id: int):
    """Setup SMS notifications for a user."""
    print("\n" + "=" * 60)
    print("SMS NOTIFICATION SETUP (Twilio)")
    print("=" * 60)

    enabled = input("Enable SMS notifications? (y/n): ").lower() == "y"

    if not enabled:
        print("SMS notifications disabled.")
        return {"enabled": False}

    print("\nEnter Twilio credentials:")
    account_sid = input("Account SID: ")
    auth_token = input("Auth Token: ")
    from_number = input("From Number (e.g., +1234567890): ")

    recipients_input = input("Recipients (comma-separated, E.164 format): ")
    recipients = [r.strip() for r in recipients_input.split(",")]

    return {
        "enabled": True,
        "account_sid": account_sid,
        "auth_token": auth_token,
        "from_number": from_number,
        "recipients": recipients,
    }


def main():
    """Main setup function."""
    print("=" * 60)
    print("NOTIFICATION CREDENTIALS SETUP")
    print("=" * 60)

    # Get user ID
    user_id = int(input("\nEnter user ID: "))

    # Connect to database
    db_path = "data/database/haruquant.db"
    db = SQLiteDatabase(db_path=db_path)

    # Check if user exists
    user = db.get_user(user_id=user_id)
    if not user:
        print(f"\nError: User with ID {user_id} not found!")
        return

    print(f"\nSetting up notifications for user: {user['username']}")

    # Setup each notification channel
    email_config = setup_email_notifications(db, user_id)
    telegram_config = setup_telegram_notifications(db, user_id)
    sms_config = setup_sms_notifications(db, user_id)

    # Build notifications JSON
    notifications = {
        "email": email_config,
        "telegram": telegram_config,
        "sms": sms_config,
    }

    # Update database
    print("\n" + "=" * 60)
    print("SAVING CONFIGURATION")
    print("=" * 60)

    try:
        success = db.update_user_settings(
            user_id=user_id, settings={"notifications": notifications}
        )

        if success:
            print("\n✓ Notification credentials saved successfully!")
            print(f"\nConfiguration summary:")
            print(f"  - Email: {'Enabled' if email_config['enabled'] else 'Disabled'}")
            print(
                f"  - Telegram: {'Enabled' if telegram_config['enabled'] else 'Disabled'}"
            )
            print(f"  - SMS: {'Enabled' if sms_config['enabled'] else 'Disabled'}")

            # Show JSON for reference
            print(f"\nStored JSON:")
            print(json.dumps(notifications, indent=2))

        else:
            print("\n✗ Failed to save notification credentials")

    except Exception as e:
        print(f"\n✗ Error saving credentials: {e}")


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n\nSetup cancelled by user.")
    except Exception as e:
        print(f"\n✗ Error: {e}")
        import traceback

        traceback.print_exc()
