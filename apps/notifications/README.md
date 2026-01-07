# Notification Service Module

A comprehensive notification service for HaruPyQuant trading platform that provides multi-channel alerts through Email, Telegram, and SMS.

## Features

- **Multi-Channel Support**: Send notifications via Email, Telegram, and SMS
- **Unified Interface**: Single API for managing all notification services
- **Template System**: Pre-defined templates for common trading alerts
- **Rate Limiting**: Built-in rate limiting to prevent spam
- **Retry Logic**: Automatic retry with exponential backoff
- **Statistics Tracking**: Monitor notification delivery success/failure rates
- **Flexible Configuration**: Support for environment variables, INI files, and JSON configuration
- **Rich Formatting**: HTML emails, Telegram rich text, formatted SMS
- **Service Management**: Enable/disable individual services dynamically

## Architecture

The module is organized into the following components:

### Core Components

| File | Purpose |
|------|---------|
| `base.py` | Abstract base classes, data structures, and rate limiting |
| `manager.py` | Unified notification manager and orchestration |
| `config.py` | Configuration management and validation |
| `templates.py` | Pre-defined notification templates |
| `email.py` | Email notification service (SMTP) |
| `telegram.py` | Telegram bot notification service |
| `sms.py` | SMS notification service (Twilio) |

### Key Classes

- **NotificationManager**: Main interface for sending notifications
- **EmailNotifier**: SMTP email notifications
- **TelegramNotifier**: Telegram bot messages
- **SMSNotifier**: SMS messages via Twilio
- **NotificationTemplate**: Template rendering system
- **NotificationConfig**: Configuration management
- **BaseNotifier**: Abstract base class for all notifiers
- **RateLimiter**: Rate limiting implementation

## Installation

### Requirements

```bash
pip install requests  # For Telegram and SMS services
```

### Optional Dependencies

For email notifications:
```bash
# Built-in smtplib is used (no additional dependencies)
```

For SMS notifications (Twilio):
```bash
pip install twilio  # Optional, direct API calls used by default
```

## Configuration

### Method 1: From INI File

Create a `config.ini` file:

```ini
[NOTIFICATIONS]
enable_all = true
default_levels = WARNING,ERROR,CRITICAL

[EMAIL]
enabled = true
smtp_server = smtp.gmail.com
smtp_port = 587
username = your_email@gmail.com
password = your_app_password
use_tls = true
from_email = your_email@gmail.com
from_name = HaruPyQuant
recipients = recipient1@example.com,recipient2@example.com

[TELEGRAM]
enabled = true
token = YOUR_BOT_TOKEN
chat_ids = CHAT_ID_1,CHAT_ID_2
parse_mode = HTML
disable_web_page_preview = true

[SMS]
enabled = true
account_sid = YOUR_TWILIO_ACCOUNT_SID
auth_token = YOUR_TWILIO_AUTH_TOKEN
from_number = +1234567890
recipients = +1234567891,+1234567892
```

Load configuration:
```python
from apps.notifications.config import NotificationConfig

config = NotificationConfig.from_ini("config.ini")
```

### Method 2: From Environment Variables

```bash
# Email
export NOTIFICATION_EMAIL_ENABLED=true
export NOTIFICATION_EMAIL_SMTP_SERVER=smtp.gmail.com
export NOTIFICATION_EMAIL_SMTP_PORT=587
export NOTIFICATION_EMAIL_USERNAME=your_email@gmail.com
export NOTIFICATION_EMAIL_PASSWORD=your_app_password
export NOTIFICATION_EMAIL_FROM_EMAIL=your_email@gmail.com
export NOTIFICATION_EMAIL_RECIPIENTS=recipient1@example.com,recipient2@example.com

# Telegram
export NOTIFICATION_TELEGRAM_ENABLED=true
export NOTIFICATION_TELEGRAM_BOT_TOKEN=YOUR_BOT_TOKEN
export NOTIFICATION_TELEGRAM_CHAT_IDS=CHAT_ID_1,CHAT_ID_2

# SMS
export NOTIFICATION_SMS_ENABLED=true
export NOTIFICATION_SMS_ACCOUNT_SID=YOUR_TWILIO_ACCOUNT_SID
export NOTIFICATION_SMS_AUTH_TOKEN=YOUR_TWILIO_AUTH_TOKEN
export NOTIFICATION_SMS_FROM_NUMBER=+1234567890
export NOTIFICATION_SMS_RECIPIENTS=+1234567891,+1234567892
```

Load configuration:
```python
from apps.notifications.config import NotificationConfig

config = NotificationConfig.from_env()
```

### Method 3: Programmatic Configuration

```python
from apps.notifications.config import NotificationConfig, NotificationPresets
from apps.notifications.email import EmailProviders

# Use presets
config = NotificationPresets.gmail_setup(
    email="your_email@gmail.com",
    password="your_app_password",
    recipients=["recipient@example.com"]
)

# Or build manually
config = NotificationConfig()
config.email_enabled = True
config.email_smtp_server = "smtp.gmail.com"
config.email_smtp_port = 587
config.email_username = "your_email@gmail.com"
config.email_password = "your_app_password"
config.email_from_email = "your_email@gmail.com"
config.email_default_recipients = ["recipient@example.com"]
```

## Usage

### Quick Start

```python
from apps.notifications import NotificationManager, NotificationManagerConfig
from apps.notifications.config import NotificationConfig

# Load configuration
config = NotificationConfig.from_ini("config.ini")

# Create manager configuration
manager_config = NotificationManagerConfig(
    email_config=config.get_email_config(),
    telegram_config=config.get_telegram_config(),
    sms_config=config.get_sms_config(),
    default_levels=config.get_default_levels()
)

# Initialize notification manager
notifier = NotificationManager(manager_config)

# Test all services
results = notifier.test_all_services()
print(f"Email: {results.get('email', False)}")
print(f"Telegram: {results.get('telegram', False)}")
print(f"SMS: {results.get('sms', False)}")
```

### Trading Alerts

```python
# Send trading alert
notifier.send_trading_alert(
    symbol="EURUSD",
    action="BUY",
    price=1.0850,
    reason="RSI oversold condition detected",
    account="Live Account",
    strategy="RSI Mean Reversion",
    risk_level="Medium"
)
```

### System Alerts

```python
# Send system alert
notifier.send_system_alert(
    level="WARNING",
    message="MT5 connection lost",
    details="Attempting to reconnect...",
    component="MT5 Client",
    status="Reconnecting"
)
```

### Position Updates

```python
# Send position update
notifier.send_position_update(
    symbol="EURUSD",
    position_type="BUY",
    size=1.0,
    entry_price=1.0850,
    current_price=1.0875,
    pnl=250.00,
    pnl_percent=2.30
)
```

### Error Alerts

```python
# Send error alert
notifier.send_error_alert(
    error_type="ConnectionError",
    message="Failed to connect to data feed",
    component="DataFeedClient",
    stack_trace="Traceback (most recent call last):\n..."
)
```

### Custom Messages

```python
# Send custom message
notifier.send_custom_message(
    title="Custom Alert",
    body="This is a custom notification message",
    level="INFO",
    metadata={"key": "value"},
    services=["telegram", "email"]  # Specific services
)
```

## Notification Templates

The module includes pre-defined templates for common scenarios:

### Trading Templates
- `trading_alert` - General trading signals
- `trading_signal` - Detailed trade signals with entry/SL/TP
- `position_opened` - Position entry notifications
- `position_closed` - Position exit notifications
- `position_update` - Position status updates

### System Templates
- `system_alert` - General system alerts
- `system_startup` - System startup notifications
- `system_shutdown` - System shutdown notifications
- `connection_lost` - Connection failure alerts
- `connection_restored` - Connection recovery alerts

### Error Templates
- `error_alert` - General error notifications
- `strategy_error` - Strategy-specific errors

### Risk Templates
- `risk_alert` - Risk management alerts
- `margin_alert` - Margin level warnings
- `drawdown_alert` - Drawdown notifications

### Market Templates
- `market_alert` - Market event alerts
- `news_alert` - News and economic event alerts
- `performance_alert` - Performance metrics alerts

### Custom Templates

```python
# Add custom template
notifier.add_template(
    name="my_custom_template",
    title_template="Custom: {event_name}",
    body_template="""
    Event: {event_name}
    Value: {value}
    Time: {timestamp}
    """
)

# Render template
from apps.notifications.templates import NotificationTemplate

template = NotificationTemplate()
message = template.render(
    "my_custom_template",
    event_name="Test Event",
    value="123"
)

# Send rendered message
notifier.send_notification(message)
```

## Email Service

### Supported Providers

```python
from apps.notifications.email import EmailProviders

# Gmail
email_config = EmailProviders.gmail(
    username="your_email@gmail.com",
    password="your_app_password"
)

# Outlook
email_config = EmailProviders.outlook(
    username="your_email@outlook.com",
    password="your_password"
)

# Yahoo
email_config = EmailProviders.yahoo(
    username="your_email@yahoo.com",
    password="your_app_password"
)

# Custom SMTP
email_config = EmailProviders.custom(
    smtp_server="smtp.example.com",
    smtp_port=587,
    username="user@example.com",
    password="password",
    use_tls=True
)
```

### Gmail Setup

1. Enable 2-factor authentication
2. Generate app password at https://myaccount.google.com/apppasswords
3. Use app password in configuration

## Telegram Service

### Bot Setup

1. Create bot via [@BotFather](https://t.me/botfather)
2. Get bot token
3. Get chat ID:
   - Send message to your bot
   - Visit: `https://api.telegram.org/bot<YOUR_BOT_TOKEN>/getUpdates`
   - Find `"chat":{"id":...}` in response

```python
from apps.notifications.telegram import TelegramNotifier, TelegramConfig

config = TelegramConfig(
    bot_token="YOUR_BOT_TOKEN",
    chat_ids=["CHAT_ID_1", "CHAT_ID_2"],
    parse_mode="HTML"
)

notifier = TelegramNotifier(config)

# Send test message
result = notifier.send_test_message("CHAT_ID")

# Send photo
notifier.send_photo("CHAT_ID", "/path/to/chart.png", "Trade Chart")

# Send document
notifier.send_document("CHAT_ID", "/path/to/report.pdf", "Daily Report")
```

## SMS Service (Twilio)

### Twilio Setup

1. Sign up at [Twilio](https://www.twilio.com/)
2. Get Account SID and Auth Token
3. Get a Twilio phone number

```python
from apps.notifications.sms import SMSNotifier, SMSConfig

config = SMSConfig(
    account_sid="YOUR_ACCOUNT_SID",
    auth_token="YOUR_AUTH_TOKEN",
    from_number="+1234567890",
    default_recipients=["+1234567891"]
)

notifier = SMSNotifier(config)

# Send test SMS
result = notifier.send_test_sms("+1234567891")

# Get account info
account_info = notifier.get_account_info()

# Get message history
history = notifier.get_message_history(limit=50)
```

## Service Management

```python
# Check service status
status = notifier.get_service_status()
for service, info in status.items():
    print(f"{service}: {'Enabled' if info['enabled'] else 'Disabled'}")

# Enable/disable services
notifier.disable_service("email")
notifier.enable_service("telegram")

# Get statistics
stats = notifier.get_statistics()
print(f"Total sent: {stats['total_sent']}")
print(f"Total failed: {stats['total_failed']}")
print(f"By service: {stats['by_service']}")
print(f"By level: {stats['by_level']}")

# Reset statistics
notifier.reset_statistics()

# List available services
services = notifier.list_services()  # ['email', 'telegram', 'sms']

# List available templates
templates = notifier.list_templates()
```

## Rate Limiting

Each service has built-in rate limiting to prevent spam:

- **Email**: 5 messages per minute
- **Telegram**: 20 messages per minute
- **SMS**: 3 messages per minute

Rate limits are enforced automatically with exponential backoff retry logic.

## Error Handling

```python
from apps.notifications.base import NotificationError

try:
    result = notifier.send_trading_alert(
        symbol="EURUSD",
        action="BUY",
        price=1.0850,
        reason="Test"
    )

    for service, res in result.items():
        if res.success:
            print(f"{service}: Sent successfully (ID: {res.message_id})")
        else:
            print(f"{service}: Failed - {res.error_message}")

except NotificationError as e:
    print(f"Notification error: {e}")
```

## Advanced Usage

### Custom Notification Levels

```python
from apps.notifications.base import NotificationLevel, NotificationMessage

# Create custom message
message = NotificationMessage(
    title="Custom Alert",
    body="This is a custom message",
    level=NotificationLevel.WARNING,
    metadata={"custom_field": "value"}
)

# Send to specific services
results = notifier.send_notification(message, services=["telegram"])
```

### Template Preview

```python
from apps.notifications.templates import NotificationTemplate

template = NotificationTemplate()

# Preview template
preview = template.preview_template(
    "trading_alert",
    symbol="EURUSD",
    action="BUY",
    price="1.0850",
    reason="Test signal"
)
print(preview)

# Get template info
info = template.get_template_info("trading_alert")
print(f"Required variables: {info['required_variables']}")
```

### Configuration Validation

```python
from apps.notifications.config import NotificationConfig

config = NotificationConfig.from_ini("config.ini")

# Validate configuration
errors = config.validate()
if errors:
    for error in errors:
        print(f"Configuration error: {error}")
else:
    print("Configuration is valid")

# Print configuration (debug)
config.print_configuration(show_passwords=False)
```

## Complete Example

```python
from apps.notifications import NotificationManager, NotificationManagerConfig
from apps.notifications.config import NotificationConfig

# Load configuration
config = NotificationConfig.from_ini("config.ini")

# Validate
errors = config.validate()
if errors:
    print("Configuration errors:", errors)
    exit(1)

# Create manager
manager_config = NotificationManagerConfig(
    email_config=config.get_email_config(),
    telegram_config=config.get_telegram_config(),
    sms_config=config.get_sms_config()
)

notifier = NotificationManager(manager_config)

# Test services
print("Testing services...")
test_results = notifier.test_all_services()
for service, result in test_results.items():
    print(f"  {service}: {'OK' if result else 'FAILED'}")

# Send trading alert
print("\nSending trading alert...")
results = notifier.send_trading_alert(
    symbol="EURUSD",
    action="BUY",
    price=1.0850,
    reason="RSI oversold + support level",
    account="Demo",
    strategy="Mean Reversion",
    risk_level="Low",
    services=["telegram"]  # Send only via Telegram
)

for service, result in results.items():
    if result.success:
        print(f"  {service}: Sent (ID: {result.message_id}, Time: {result.delivery_time_ms}ms)")
    else:
        print(f"  {service}: Failed - {result.error_message}")

# Get statistics
stats = notifier.get_statistics()
print(f"\nStatistics:")
print(f"  Total sent: {stats['total_sent']}")
print(f"  Total failed: {stats['total_failed']}")
```

## Notification Levels

The module supports five notification levels:

- **DEBUG**: Detailed diagnostic information
- **INFO**: General informational messages
- **WARNING**: Warning messages (default level)
- **ERROR**: Error messages (default level)
- **CRITICAL**: Critical error messages (default level)

Configure which levels trigger notifications in your configuration file.

## Security Best Practices

1. **Never commit credentials** to version control
2. Use **environment variables** or secure config files
3. Use **app passwords** for Gmail (not account password)
4. Restrict **file permissions** on config files: `chmod 600 config.ini`
5. Use **secure SMTP** connections (TLS/SSL)
6. Store **Twilio credentials** securely
7. Keep **Telegram bot token** private

## Troubleshooting

### Email Issues

**Problem**: Gmail authentication fails
**Solution**: Enable 2FA and use app password, not account password

**Problem**: Connection timeout
**Solution**: Check firewall rules for SMTP ports (587, 465, 25)

### Telegram Issues

**Problem**: Invalid bot token
**Solution**: Verify token from BotFather, ensure no extra spaces

**Problem**: Can't get chat ID
**Solution**: Send message to bot first, then call `/getUpdates`

### SMS Issues

**Problem**: Twilio authentication fails
**Solution**: Verify Account SID and Auth Token from Twilio console

**Problem**: Invalid phone number
**Solution**: Use E.164 format: +[country code][number]

## API Reference

### NotificationManager

Main interface for sending notifications.

#### Methods

- `send_notification(message, services=None)` - Send notification through specified services
- `send_trading_alert(...)` - Send trading alert using template
- `send_system_alert(...)` - Send system alert using template
- `send_position_update(...)` - Send position update using template
- `send_error_alert(...)` - Send error alert using template
- `send_custom_message(...)` - Send custom formatted message
- `test_all_services()` - Test all configured services
- `enable_service(service_name)` - Enable a notification service
- `disable_service(service_name)` - Disable a notification service
- `get_service_status()` - Get status of all services
- `get_statistics()` - Get notification statistics
- `reset_statistics()` - Reset statistics counters
- `list_services()` - List available services
- `list_templates()` - List available templates

### NotificationConfig

Configuration management.

#### Class Methods

- `from_ini(config_file)` - Load from INI file
- `from_env()` - Load from environment variables
- `from_file(file_path)` - Load from JSON file

#### Methods

- `validate()` - Validate configuration
- `save_to_file(file_path)` - Save to JSON file
- `get_email_config()` - Get EmailConfig instance
- `get_telegram_config()` - Get TelegramConfig instance
- `get_sms_config()` - Get SMSConfig instance
- `print_configuration(show_passwords=False)` - Print configuration

## Contributing

When adding new features:

1. Extend `BaseNotifier` for new notification services
2. Add new templates to `templates.py`
3. Update configuration classes as needed
4. Add tests for new functionality
5. Update this README

## License

Part of HaruPyQuant trading platform.

## Version

Version: 1.0.0
