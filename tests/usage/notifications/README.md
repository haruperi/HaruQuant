# Database-Backed Notifications for Live Trading

This guide explains how to configure and use database-backed notifications with Telegram support.

## Overview

The notification system now supports loading credentials directly from the database `user_settings` table. This provides:

- **Centralized Configuration**: Store all notification settings in one place
- **Multi-Channel Support**: Email, Telegram, and SMS
- **User-Specific Settings**: Each user can have different notification preferences
- **Easy Management**: Update credentials without changing code or config files

## Database Structure

Notification credentials are stored in the `notifications` column of the `user_settings` table as JSON:

```json
{
  "email": {
    "enabled": true,
    "smtp_host": "smtp.gmail.com",
    "smtp_port": 587,
    "smtp_user": "your_email@gmail.com",
    "smtp_password": "your_app_password",
    "recipients": ["recipient1@example.com"],
    "use_tls": true
  },
  "telegram": {
    "enabled": true,
    "bot_token": "123456:ABC-DEF1234ghIkl-zyx57W2v1u123ew11",
    "chat_ids": ["123456789", "987654321"],
    "parse_mode": "HTML",
    "disable_web_page_preview": true,
    "disable_notification": false
  },
  "sms": {
    "enabled": false,
    "account_sid": "ACxxxxxxxxxxxxxxxxxxxxx",
    "auth_token": "your_auth_token",
    "from_number": "+1234567890",
    "recipients": ["+1234567891"]
  }
}
```

## Setup Instructions

### Method 1: Interactive Setup Script

Run the interactive setup script:

```bash
python tests/usage/notifications/setup_notifications.py
```

This will guide you through:
1. Entering your user ID
2. Configuring email settings
3. Configuring Telegram settings
4. Configuring SMS settings (optional)
5. Saving to database

### Method 2: Manual SQL Update

```sql
UPDATE user_settings
SET notifications = '{"email": {...}, "telegram": {...}}'
WHERE user_id = 1;
```

### Method 3: Python Code

```python
from apps.sqlite import SQLiteDatabase

db = SQLiteDatabase(db_path="data/database/haruquant.db")

notifications = {
    "email": {
        "enabled": True,
        "smtp_host": "smtp.gmail.com",
        "smtp_port": 587,
        "smtp_user": "your_email@gmail.com",
        "smtp_password": "your_app_password",
        "recipients": ["recipient@example.com"],
        "use_tls": True,
    },
    "telegram": {
        "enabled": True,
        "bot_token": "YOUR_BOT_TOKEN",
        "chat_ids": ["YOUR_CHAT_ID"],
        "parse_mode": "HTML",
    }
}

db.update_user_settings(user_id=1, settings={"notifications": notifications})
```

## Telegram Setup

### Step 1: Create a Bot

1. Open Telegram and search for `@BotFather`
2. Send `/newbot` command
3. Follow the prompts to name your bot
4. Save the bot token (e.g., `123456:ABC-DEF1234ghIkl-zyx57W2v1u123ew11`)

### Step 2: Get Your Chat ID

**Option A: Using a Bot**
1. Search for `@userinfobot` on Telegram
2. Start a chat and it will show your chat ID

**Option B: Using API**
1. Send a message to your bot
2. Visit: `https://api.telegram.org/bot<YOUR_BOT_TOKEN>/getUpdates`
3. Find your chat ID in the response:
   ```json
   {
     "update_id": 123456789,
     "message": {
       "chat": {
         "id": 123456789,  // <-- This is your chat ID
         "first_name": "Your Name",
         "type": "private"
       }
     }
   }
   ```

### Step 3: Test Your Bot

```bash
curl -X POST "https://api.telegram.org/bot<YOUR_BOT_TOKEN>/sendMessage" \
  -d "chat_id=<YOUR_CHAT_ID>" \
  -d "text=Hello from HaruQuant!"
```

## Usage in Live Trading

### Loading from Database

```python
from apps.live.notification_adapter import LiveTradingNotifier

# Create notifier from database
notifier = LiveTradingNotifier.from_database(
    user_id=1,
    db_path="data/database/haruquant.db"
)

# Use in live trading
notifier.notify_startup(symbol="EURUSD", timeframe="M15", volume=0.01)

notifier.notify_signal(
    signal={
        "signal": "buy",
        "time": "2024-01-01 10:00:00",
        "reason": "RSI oversold",
        "entry_price": 1.0850,
        "symbol": "EURUSD",
    },
    executed=True
)
```

### Integration with Multi-Strategy Engine

Update your engine initialization to load from database:

```python
# In engine.py, replace the notifier initialization:

# OLD CODE:
notif_config = self.config["notifications"]
self.notifier = LiveTradingNotifier(
    notif_config.get("enable_email", False),
    notif_config.get("smtp_host", ""),
    notif_config.get("smtp_port", 587),
    notif_config.get("smtp_user", ""),
    notif_config.get("smtp_password", ""),
    notif_config.get("recipients", []),
)

# NEW CODE:
user_id = self.config.get("user_id", 1)  # Add user_id to your config
self.notifier = LiveTradingNotifier.from_database(
    user_id=user_id,
    db_path="data/database/haruquant.db"
)
```

### Configuration File Update

Add user_id to your multi-strategy config JSON:

```json
{
  "user_id": 1,
  "mt5": {...},
  "strategies": [...],
  "portfolio": {...}
}
```

## Testing

### Test Database Credentials

```bash
python tests/usage/notifications/test_database_notifications.py
```

This will:
1. Load credentials from database
2. Show configuration summary
3. Test connections
4. Optionally send test notifications

### Manual Test

```python
from apps.live.notification_adapter import LiveTradingNotifier

# Load from database
notifier = LiveTradingNotifier.from_database(user_id=1)

# Test connection
if notifier.test_connection():
    print("✓ Connection successful!")

# Send test notification
notifier.notify_signal(
    signal={
        "signal": "buy",
        "time": "2024-01-01 10:00:00",
        "reason": "Test notification",
        "entry_price": 1.0850,
        "symbol": "EURUSD",
    },
    executed=True
)
```

## Available Methods

The `LiveTradingNotifier` supports all the same methods whether loaded from database or config:

- `notify_startup(symbol, timeframe, volume)` - System startup
- `notify_shutdown(reason)` - System shutdown
- `notify_signal(signal, executed, error)` - Trading signals
- `notify_safety_violation(reason)` - Safety checks
- `notify_connection_error(error)` - Connection errors
- `notify_daily_summary(trades, profit, positions)` - Daily summaries
- `test_connection()` - Test all enabled services

## Notification Channels

When credentials are loaded from the database, the notifier will automatically use all enabled channels:

- **Email Only**: If only email is configured
- **Telegram Only**: If only Telegram is configured
- **Both**: If both are configured, notifications go to both channels
- **None**: If no credentials, notifier is disabled

## Security Considerations

1. **Database Security**: The database contains sensitive credentials
   - Use file permissions to protect: `chmod 600 data/database/haruquant.db`
   - Consider encrypting the database
   - Never commit the database to version control

2. **Telegram Bot Token**: Keep your bot token secret
   - Don't share it publicly
   - Regenerate if compromised via @BotFather

3. **Email Passwords**: Use app-specific passwords
   - Gmail: https://myaccount.google.com/apppasswords
   - Never use your main account password

## Troubleshooting

### Telegram Not Receiving Messages

1. **Check bot token**: Verify it's correct in database
2. **Check chat ID**: Make sure you've messaged the bot first
3. **Test manually**:
   ```bash
   curl -X POST "https://api.telegram.org/bot<TOKEN>/sendMessage" \
     -d "chat_id=<CHAT_ID>" \
     -d "text=Test"
   ```

### Email Not Sending

1. **Check SMTP settings**: Verify host, port, credentials
2. **Gmail**: Enable "Less secure app access" or use app password
3. **Test connection**: Use `notifier.test_connection()`

### No Notifications Sent

1. **Check if enabled**: `notifier.enabled` should be `True`
2. **Check database**: Verify credentials are in database
3. **Check logs**: Look for errors in application logs

## Examples

### Example 1: Email Only

```json
{
  "email": {
    "enabled": true,
    "smtp_host": "smtp.gmail.com",
    "smtp_port": 587,
    "smtp_user": "trader@gmail.com",
    "smtp_password": "app_password_here",
    "recipients": ["alerts@example.com"],
    "use_tls": true
  },
  "telegram": {"enabled": false},
  "sms": {"enabled": false}
}
```

### Example 2: Telegram Only

```json
{
  "email": {"enabled": false},
  "telegram": {
    "enabled": true,
    "bot_token": "123456:ABC-DEF1234ghIkl-zyx57W2v1u123ew11",
    "chat_ids": ["123456789"],
    "parse_mode": "HTML"
  },
  "sms": {"enabled": false}
}
```

### Example 3: Both Email and Telegram

```json
{
  "email": {
    "enabled": true,
    "smtp_host": "smtp.gmail.com",
    "smtp_port": 587,
    "smtp_user": "trader@gmail.com",
    "smtp_password": "app_password_here",
    "recipients": ["alerts@example.com"],
    "use_tls": true
  },
  "telegram": {
    "enabled": true,
    "bot_token": "123456:ABC-DEF1234ghIkl-zyx57W2v1u123ew11",
    "chat_ids": ["123456789"],
    "parse_mode": "HTML"
  },
  "sms": {"enabled": false}
}
```

## API Reference

### Database Methods

```python
from apps.sqlite import SQLiteDatabase

db = SQLiteDatabase(db_path="data/database/haruquant.db")

# Get all notification settings
settings = db.get_notification_settings(user_id=1)

# Get email credentials only
email = db.get_email_credentials(user_id=1)

# Get Telegram credentials only
telegram = db.get_telegram_credentials(user_id=1)

# Update notification settings
db.update_user_settings(user_id=1, settings={"notifications": {...}})
```

### Notifier Methods

```python
from apps.live.notification_adapter import LiveTradingNotifier

# Create from database
notifier = LiveTradingNotifier.from_database(user_id=1)

# Create from config (backward compatible)
notifier = LiveTradingNotifier(
    enabled=True,
    smtp_host="smtp.gmail.com",
    smtp_port=587,
    smtp_user="user@gmail.com",
    smtp_password="password",
    recipients=["alerts@example.com"]
)
```

## Migration Guide

If you're currently using config file notifications, here's how to migrate:

1. **Extract credentials from config**:
   ```python
   # From your config.json
   notifications = {
       "email": {
           "enabled": config["notifications"]["enable_email"],
           "smtp_host": config["notifications"]["smtp_host"],
           # ... etc
       }
   }
   ```

2. **Save to database**:
   ```python
   db.update_user_settings(user_id=1, settings={"notifications": notifications})
   ```

3. **Update code**:
   ```python
   # Old
   notifier = LiveTradingNotifier(config["enable_email"], ...)

   # New
   notifier = LiveTradingNotifier.from_database(user_id=1)
   ```

4. **Remove from config file** (optional):
   - You can now remove notification settings from config files
   - Everything is in the database

## Support

For issues or questions:
1. Check the logs for error messages
2. Run the test script to diagnose issues
3. Verify database structure matches expected format
4. Test credentials manually (curl for Telegram, SMTP test for email)
