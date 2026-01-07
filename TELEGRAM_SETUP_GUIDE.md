# Quick Setup Guide: Telegram Notifications for Live Trading

Follow these steps to get Telegram notifications working with your live trading system.

## Current Status

✅ **Code Updated**: The engine now supports database-based notifications
⚠️ **Setup Required**: You need to configure your Telegram credentials in the database

## Step-by-Step Setup

### Step 1: Create a Telegram Bot (5 minutes)

1. Open Telegram and search for `@BotFather`
2. Send the command: `/newbot`
3. Follow the prompts:
   - Choose a name for your bot (e.g., "HaruQuant Alerts")
   - Choose a username (must end in 'bot', e.g., "haruquant_alerts_bot")
4. **Save the bot token** that BotFather gives you
   - It looks like: `123456789:ABCdefGHIjklMNOpqrsTUVwxyz`

### Step 2: Get Your Chat ID (2 minutes)

**Option A - Using @userinfobot (Easiest):**
1. Search for `@userinfobot` in Telegram
2. Start a chat - it will immediately show your chat ID
3. **Save this number** (e.g., `123456789`)

**Option B - Using API:**
1. Send any message to your bot (the one you just created)
2. Open this URL in your browser (replace `<BOT_TOKEN>` with your actual token):
   ```
   https://api.telegram.org/bot<BOT_TOKEN>/getUpdates
   ```
3. Look for `"chat":{"id":123456789}` in the response
4. **Save this ID number**

### Step 3: Store Credentials in Database (2 minutes)

**Option A - Interactive Setup (Recommended):**
```bash
# Run the setup script
venv\Scripts\python.exe tests\usage\notifications\setup_notifications.py

# When prompted:
# - Enter your user ID (probably 1)
# - Choose 'y' for Telegram notifications
# - Enter your bot token
# - Enter your chat ID
# - Press Enter to use default settings
```

**Option B - Quick Python Script:**
```python
from apps.sqlite import SQLiteDatabase

db = SQLiteDatabase(db_path="data/database/haruquant.db")

notifications = {
    "email": {"enabled": False},  # Keep email disabled if you don't need it
    "telegram": {
        "enabled": True,
        "bot_token": "YOUR_BOT_TOKEN_HERE",
        "chat_ids": ["YOUR_CHAT_ID_HERE"],
        "parse_mode": "HTML"
    },
    "sms": {"enabled": False}
}

db.update_user_settings(user_id=1, settings={"notifications": notifications})
print("✓ Telegram credentials saved!")
```

**Option C - Direct SQL:**
```sql
UPDATE user_settings
SET notifications = '{
  "email": {"enabled": false},
  "telegram": {
    "enabled": true,
    "bot_token": "YOUR_BOT_TOKEN_HERE",
    "chat_ids": ["YOUR_CHAT_ID_HERE"],
    "parse_mode": "HTML"
  },
  "sms": {"enabled": false}
}'
WHERE user_id = 1;
```

### Step 4: Update Your Config File (1 minute)

**Option A - Use the new config file (Recommended):**
```bash
# Use the new config that has user_id
python apps/live/run.py config/multi_strategy_config_with_db_notifications.json
```

**Option B - Add user_id to your existing config:**

Edit `config/multi_strategy_config.json` and add these two lines at the top:
```json
{
  "user_id": 1,
  "db_path": "data/database/haruquant.db",
  "mt5": {
    ...
```

You can also **remove** the entire `"notifications"` section since it won't be used anymore.

### Step 5: Test Your Setup (2 minutes)

```bash
# Test the database credentials
venv\Scripts\python.exe tests\usage\notifications\test_database_notifications.py

# When prompted:
# - Enter your user ID (1)
# - Choose option 1 to test credentials
# - Choose 'y' to send test notifications
```

You should receive test messages in Telegram!

### Step 6: Run Live Trading

```bash
# Run with the new config
python apps/live/run.py config/multi_strategy_config_with_db_notifications.json
```

**You should see in the logs:**
```
Loading notification credentials from database for user 1
Telegram notifications enabled for user 1
✓ Notifier created: LiveTradingNotifier(enabled=True)
```

## What Notifications Will You Receive?

Once configured, you'll get Telegram messages for:

1. **System Startup** - When the trading system starts
2. **Trading Signals** - When a buy/sell signal is detected and executed
3. **Safety Violations** - When trades are blocked by safety checks
4. **Connection Errors** - When MT5 connection issues occur
5. **System Shutdown** - When the system stops

## Example Telegram Messages

**Trading Signal:**
```
🔔 Trading Alert

Symbol: EURUSD
Action: BUY
Price: 1.08500
Reason: RSI oversold + support level

Account: Live
Strategy: Auto
Risk Level: Medium

Time: 2024-01-07 10:30:15
```

**Safety Check:**
```
⚠️ System Alert

Level: WARNING
Message: Safety Check Failed
Details: Trading action blocked: Maximum daily trades reached (20/20)

Component: Safety Checker
Status: Blocked
```

## Troubleshooting

### Not receiving messages?

1. **Check you messaged the bot first**
   - Send any message to your bot
   - The bot must have your chat ID to send you messages

2. **Verify credentials in database:**
   ```python
   from apps.sqlite import SQLiteDatabase
   db = SQLiteDatabase(db_path="data/database/haruquant.db")
   telegram = db.get_telegram_credentials(user_id=1)
   print(telegram)
   ```

3. **Test manually:**
   ```bash
   curl -X POST "https://api.telegram.org/bot<YOUR_BOT_TOKEN>/sendMessage" \
     -d "chat_id=<YOUR_CHAT_ID>" \
     -d "text=Test from HaruQuant"
   ```

4. **Check the logs:**
   - Look in `logs/multi_strategy/multi_strategy.log`
   - Should see "Telegram notifications enabled for user X"

### Bot token invalid?

- Make sure you copied the entire token from BotFather
- Token should look like: `123456789:ABCdefGHIjklMNOpqrsTUVwxyz`
- No spaces or extra characters

### Wrong chat ID?

- Make sure you got YOUR chat ID, not the bot's ID
- Should be a number like `123456789`
- Try using @userinfobot to get the correct ID

## Additional Features

### Multiple Recipients

You can send to multiple Telegram users/groups:

```python
notifications = {
    "telegram": {
        "enabled": True,
        "bot_token": "YOUR_BOT_TOKEN",
        "chat_ids": ["123456789", "987654321", "-1001234567890"],  # Multiple IDs
        "parse_mode": "HTML"
    }
}
```

### Enable Email Too

You can enable both Email and Telegram:

```python
notifications = {
    "email": {
        "enabled": True,
        "smtp_host": "smtp.gmail.com",
        "smtp_port": 587,
        "smtp_user": "your_email@gmail.com",
        "smtp_password": "your_app_password",
        "recipients": ["alerts@example.com"],
        "use_tls": True
    },
    "telegram": {
        "enabled": True,
        "bot_token": "YOUR_BOT_TOKEN",
        "chat_ids": ["YOUR_CHAT_ID"],
        "parse_mode": "HTML"
    }
}
```

Both channels will receive notifications!

## Summary Checklist

- [ ] Create Telegram bot via @BotFather
- [ ] Get bot token from BotFather
- [ ] Get your chat ID (use @userinfobot)
- [ ] Run setup script OR manually update database
- [ ] Add `"user_id": 1` to your config file
- [ ] Test with test script
- [ ] Run live trading
- [ ] Verify you receive test messages

## Need Help?

Run the test script and it will show you exactly what's configured:

```bash
venv\Scripts\python.exe tests\usage\notifications\test_database_notifications.py
```

Good luck! 🚀
