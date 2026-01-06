# Logger Module

A production-ready, Loguru-inspired logging library built with Python standard library only, providing simple, intuitive logging with powerful features for the HaruQuant trading platform.

## Overview

The `logger` module provides a comprehensive logging solution with automatic frame inspection, flexible formatting, multiple output handlers, log rotation, retention policies, and beautiful colored console output. It's designed to be simple to use while offering advanced features for production environments.

## Key Features

- **Simple API**: Intuitive interface inspired by Loguru
- **Multiple Log Levels**: TRACE, DEBUG, INFO, SUCCESS, WARNING, ERROR, CRITICAL
- **Flexible Formatting**: Positional and named argument formatting
- **Multiple Handlers**: File, stream, and callable handlers
- **Log Rotation**: Size-based and time-based rotation
- **Log Retention**: Automatic cleanup of old logs
- **Colored Output**: Beautiful colored console output
- **Exception Formatting**: Detailed exception tracebacks
- **Thread-Safe**: Safe for concurrent logging
- **Context Management**: Temporary context for log calls
- **Async Support**: Asynchronous logging handlers

## Architecture

The module consists of multiple components working together:

```
┌──────────────────┐
│  Logger          │  ← Main logging interface
├──────────────────┤
│  Handlers        │  ← File, Stream, Callable
├──────────────────┤
│  Formatters      │  ← Message formatting
├──────────────────┤
│  Rotation        │  ← Size/time-based rotation
├──────────────────┤
│  Retention       │  ← Automatic cleanup
├──────────────────┤
│  Exception       │  ← Exception formatting
└──────────────────┘
```

---

## 1. Basic Usage

The logger module provides a pre-configured global logger instance ready to use.

### Quick Start

**Import and Use:**

```python
from apps.logger import logger

# Simple logging
logger.info("Application started")
logger.success("Operation completed successfully")
logger.warning("Low disk space")
logger.error("Failed to connect to database")
logger.critical("System shutdown initiated")
```

**With Arguments:**

```python
from apps.logger import logger

# Positional arguments
logger.info("User {} logged in", "john_doe")
logger.info("Processing {} items in {} seconds", 100, 2.5)

# Named arguments
logger.info("User {user} logged in from {city}", user="john_doe", city="NYC")
logger.error("Failed to process order {order_id}", order_id=12345)
```

**With Context:**

```python
from apps.logger import logger

# Add extra context
logger.info("Trade executed", symbol="EURUSD", price=1.0950, volume=1.0)
logger.error("Order failed", order_id=123, reason="Insufficient margin")
```

---

## 2. Log Levels

Seven log levels from most to least verbose.

### Available Levels

- **TRACE (5)**: Very detailed debugging information
- **DEBUG (10)**: Detailed debugging information
- **INFO (20)**: General informational messages
- **SUCCESS (25)**: Success messages (custom level)
- **WARNING (30)**: Warning messages
- **ERROR (40)**: Error messages
- **CRITICAL (50)**: Critical error messages

### Using Log Levels

```python
from apps.logger import logger

# Different log levels
logger.trace("Entering function calculate_profit()")
logger.debug("Variable state: balance={}, equity={}", 10000, 10500)
logger.info("Starting backtest for EURUSD")
logger.success("Backtest completed successfully")
logger.warning("High CPU usage detected: 85%")
logger.error("Failed to fetch market data")
logger.critical("Database connection lost")
```

### Custom Log Level

```python
from apps.logger import logger

# Log at specific level
logger.log("INFO", "This is an info message")
logger.log(20, "This is also an info message")
logger.log("SUCCESS", "Custom success message")
```

---

## 3. Handlers

Handlers control where log messages are sent (files, console, custom functions).

### Adding Handlers

#### Console Handler (stderr)

```python
from apps.logger import logger
import sys

# Add colored console output
handler_id = logger.add(
    sys.stderr,
    level="INFO",
    colorize=True,
    format="<green>{time:YYYY-MM-DD HH:mm:ss}</green> | <level>{level: <8}</level> | <cyan>{name}</cyan>:<cyan>{function}</cyan>:<cyan>{line}</cyan> - <level>{message}</level>"
)
```

#### File Handler

```python
from apps.logger import logger

# Add file handler
handler_id = logger.add(
    "logs/app.log",
    level="DEBUG",
    format="{time:YYYY-MM-DD HH:mm:ss} | {level: <8} | {name}:{function}:{line} - {message}",
    rotation="500 MB",  # Rotate when file reaches 500 MB
    retention="10 days",  # Keep logs for 10 days
    compression="zip"  # Compress rotated logs
)
```

#### Callable Handler

```python
from apps.logger import logger

# Custom handler function
def send_to_monitoring(message):
    # Send to monitoring service
    print(f"MONITORING: {message}")

handler_id = logger.add(
    send_to_monitoring,
    level="ERROR",
    format="{time} | {level} | {message}"
)
```

### Removing Handlers

```python
from apps.logger import logger

# Add handler and get ID
handler_id = logger.add("logs/app.log")

# Remove specific handler
logger.remove(handler_id)

# Remove all handlers
logger.remove()
```

---

## 4. Formatting

Customize log message format with placeholders.

### Format Placeholders

**Time Placeholders:**

- `{time}` - Full timestamp
- `{time:YYYY-MM-DD}` - Date only
- `{time:HH:mm:ss}` - Time only
- `{time:YYYY-MM-DD HH:mm:ss.SSS}` - With milliseconds

**Record Placeholders:**

- `{level}` - Log level name
- `{level.no}` - Log level number
- `{message}` - Log message
- `{name}` - Logger name
- `{function}` - Function name
- `{line}` - Line number
- `{file}` - File name
- `{file.path}` - Full file path
- `{process}` - Process ID
- `{process.name}` - Process name
- `{thread}` - Thread ID
- `{thread.name}` - Thread name

**Exception Placeholders:**

- `{exception}` - Exception traceback

### Format Examples

**Simple Format:**

```python
from apps.logger import logger

logger.add(
    "logs/simple.log",
    format="{time} | {level} | {message}"
)
```

**Detailed Format:**

```python
from apps.logger import logger

logger.add(
    "logs/detailed.log",
    format="{time:YYYY-MM-DD HH:mm:ss.SSS} | {level: <8} | {process}:{thread} | {name}:{function}:{line} - {message}"
)
```

**Colored Console Format:**

```python
from apps.logger import logger
import sys

logger.add(
    sys.stderr,
    colorize=True,
    format="<green>{time:HH:mm:ss}</green> | <level>{level: <8}</level> | <cyan>{name}</cyan> - <level>{message}</level>"
)
```

---

## 5. Rotation and Retention

Automatic log file rotation and cleanup.

### Rotation

Rotate log files based on size or time.

**Size-Based Rotation:**

```python
from apps.logger import logger

# Rotate when file reaches 10 MB
logger.add("logs/app.log", rotation="10 MB")

# Rotate when file reaches 500 MB
logger.add("logs/app.log", rotation="500 MB")

# Rotate when file reaches 1 GB
logger.add("logs/app.log", rotation="1 GB")
```

**Time-Based Rotation:**

```python
from apps.logger import logger

# Rotate daily at midnight
logger.add("logs/app.log", rotation="00:00")

# Rotate daily at 12:00
logger.add("logs/app.log", rotation="12:00")

# Rotate weekly on Monday
logger.add("logs/app.log", rotation="1 week")

# Rotate monthly
logger.add("logs/app.log", rotation="1 month")
```

### Retention

Automatically delete old log files.

```python
from apps.logger import logger

# Keep logs for 7 days
logger.add("logs/app.log", retention="7 days")

# Keep logs for 30 days
logger.add("logs/app.log", retention="30 days")

# Keep last 10 files
logger.add("logs/app.log", retention=10)
```

### Compression

Compress rotated log files.

```python
from apps.logger import logger

# Compress with zip
logger.add("logs/app.log", rotation="500 MB", compression="zip")

# Compress with gzip
logger.add("logs/app.log", rotation="1 GB", compression="gz")
```

---

## 6. Exception Logging

Detailed exception logging with tracebacks.

### Basic Exception Logging

```python
from apps.logger import logger

try:
    result = 10 / 0
except Exception as e:
    logger.exception("Division error occurred")
```

### Exception with Context

```python
from apps.logger import logger

try:
    process_order(order_id=123)
except Exception as e:
    logger.exception("Failed to process order", order_id=123, user_id=456)
```

### Manual Exception Logging

```python
from apps.logger import logger
import sys

try:
    risky_operation()
except Exception:
    exc_info = sys.exc_info()
    logger.error("Operation failed", exc_info=exc_info)
```

---

## 7. Advanced Features

### Context Manager

Temporarily modify logger behavior.

```python
from apps.logger import logger

# Temporarily change options
with logger.contextualize(user_id=123, session_id="abc"):
    logger.info("User action")  # Includes user_id and session_id
    logger.info("Another action")  # Also includes context
```

### Options

Modify behavior for a single log call.

```python
from apps.logger import logger

# Skip frame inspection (faster)
logger.opt(depth=0).info("Fast log message")

# Include exception info
logger.opt(exception=True).error("Error occurred")

# Custom depth for frame inspection
logger.opt(depth=2).info("Message from caller's caller")
```

### Binding

Create a logger with permanent context.

```python
from apps.logger import logger

# Create bound logger
user_logger = logger.bind(user_id=123, username="john_doe")

# All logs from this logger include context
user_logger.info("User logged in")  # Includes user_id and username
user_logger.info("User logged out")  # Also includes context
```

---

## Common Patterns

### Application Logging

```python
from apps.logger import logger
import sys

# Configure logger for application
logger.remove()  # Remove default handler

# Console output (INFO and above)
logger.add(
    sys.stderr,
    level="INFO",
    colorize=True,
    format="<green>{time:HH:mm:ss}</green> | <level>{level: <8}</level> | <level>{message}</level>"
)

# File output (DEBUG and above)
logger.add(
    "logs/app.log",
    level="DEBUG",
    format="{time:YYYY-MM-DD HH:mm:ss} | {level: <8} | {name}:{function}:{line} - {message}",
    rotation="500 MB",
    retention="30 days",
    compression="zip"
)

# Error file (ERROR and above)
logger.add(
    "logs/errors.log",
    level="ERROR",
    format="{time:YYYY-MM-DD HH:mm:ss} | {level: <8} | {name}:{function}:{line} - {message}\n{exception}",
    rotation="100 MB",
    retention="90 days"
)

logger.info("Application started")
```

### Trading Strategy Logging

```python
from apps.logger import logger

# Create strategy-specific logger
strategy_logger = logger.bind(strategy="MA_Crossover", version="1.0.0")

# Log strategy events
strategy_logger.info("Strategy initialized", symbol="EURUSD", timeframe="H1")
strategy_logger.debug("Calculating indicators", fast_ma=12, slow_ma=26)
strategy_logger.success("Buy signal generated", price=1.0950, confidence=0.85)
strategy_logger.warning("High volatility detected", atr=0.0015)
strategy_logger.error("Order execution failed", order_id=123, reason="Insufficient margin")
```

### Backtest Logging

```python
from apps.logger import logger

# Configure for backtest
logger.remove()
logger.add(
    "logs/backtest_{time:YYYY-MM-DD}.log",
    level="INFO",
    format="{time:HH:mm:ss} | {level: <8} | {message}",
    rotation="1 day"
)

# Log backtest progress
logger.info("Backtest started", symbol="EURUSD", start="2024-01-01", end="2024-12-31")
logger.info("Processing data", bars=10000, progress=0.25)
logger.success("Backtest completed", total_trades=150, win_rate=0.62, profit=2500)
```

### Error Monitoring

```python
from apps.logger import logger

def send_to_slack(message):
    # Send critical errors to Slack
    # Implementation here
    pass

# Add Slack handler for critical errors
logger.add(
    send_to_slack,
    level="CRITICAL",
    format="{time} | {level} | {message}"
)

# Critical errors will be sent to Slack
logger.critical("Database connection lost")
logger.critical("System out of memory")
```

### Multi-Process Logging

```python
from apps.logger import logger
from multiprocessing import Process

def worker(worker_id):
    worker_logger = logger.bind(worker_id=worker_id)
    worker_logger.info("Worker started")
    # Do work...
    worker_logger.info("Worker finished")

# Configure logger
logger.add("logs/workers.log", enqueue=True)  # Thread-safe

# Start workers
processes = [Process(target=worker, args=(i,)) for i in range(4)]
for p in processes:
    p.start()
for p in processes:
    p.join()
```

---

## Best Practices

### General

1. **Remove default handler**: Call `logger.remove()` before adding custom handlers
2. **Use appropriate levels**: INFO for normal operations, DEBUG for development
3. **Include context**: Add relevant context to log messages
4. **Rotate logs**: Always configure rotation to prevent disk space issues
5. **Set retention**: Automatically clean up old logs

### Performance

1. **Use lazy formatting**: Let the logger format messages only when needed
2. **Filter at handler level**: Set appropriate log levels for each handler
3. **Avoid excessive logging**: Don't log in tight loops
4. **Use async handlers**: Enable `enqueue=True` for high-throughput scenarios
5. **Disable in production**: Set higher log levels in production

### Security

1. **Sanitize sensitive data**: Don't log passwords, API keys, or tokens
2. **Limit log retention**: Don't keep logs indefinitely
3. **Secure log files**: Set appropriate file permissions
4. **Rotate frequently**: Prevent logs from growing too large
5. **Monitor log access**: Track who accesses log files

### Debugging

1. **Use TRACE level**: For very detailed debugging
2. **Include stack traces**: Use `logger.exception()` for errors
3. **Add context**: Bind relevant variables to logger
4. **Temporary verbosity**: Increase log level temporarily for debugging
5. **Use opt()**: Customize individual log calls as needed

## Configuration Examples

### Development Configuration

```python
from apps.logger import logger
import sys

logger.remove()

# Verbose console output
logger.add(
    sys.stderr,
    level="DEBUG",
    colorize=True,
    format="<green>{time:HH:mm:ss.SSS}</green> | <level>{level: <8}</level> | <cyan>{name}:{function}:{line}</cyan> - <level>{message}</level>"
)

# Detailed file log
logger.add(
    "logs/dev.log",
    level="TRACE",
    format="{time:YYYY-MM-DD HH:mm:ss.SSS} | {level: <8} | {process}:{thread} | {name}:{function}:{line} - {message}",
    rotation="10 MB",
    retention="3 days"
)
```

### Production Configuration

```python
from apps.logger import logger
import sys

logger.remove()

# Minimal console output
logger.add(
    sys.stderr,
    level="WARNING",
    format="{time:HH:mm:ss} | {level: <8} | {message}"
)

# Application log
logger.add(
    "logs/app.log",
    level="INFO",
    format="{time:YYYY-MM-DD HH:mm:ss} | {level: <8} | {message}",
    rotation="500 MB",
    retention="30 days",
    compression="zip",
    enqueue=True  # Thread-safe
)

# Error log
logger.add(
    "logs/error.log",
    level="ERROR",
    format="{time:YYYY-MM-DD HH:mm:ss} | {level: <8} | {name}:{function}:{line} - {message}\n{exception}",
    rotation="100 MB",
    retention="90 days",
    compression="zip"
)
```

## License

Copyright 2025, HaruQuant
