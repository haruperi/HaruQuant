"""
System-wide constants for the HaruQuant trading bot.

This module contains all constant values used throughout the application,
organized by their respective domains. Values that can be configured via
config.ini are not duplicated here - only their defaults when not specified
in the configuration file.
"""

from pathlib import Path
from typing import Dict, List

# File System Paths
PROJECT_ROOT = Path(__file__).parent.parent.parent
DATA_DIR = PROJECT_ROOT / "data"
LOGS_DIR = PROJECT_ROOT / "logs"
HISTORICAL_DATA_DIR = DATA_DIR / "historical"
BACKTEST_RESULTS_DIR = DATA_DIR / "backtest_results"
OPTIMIZATION_RESULTS_DIR = DATA_DIR / "optimization_results"

# Logging Configuration
LOG_FORMAT = "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
LOG_DATE_FORMAT = "%Y-%m-%d %H:%M:%S"
LOG_FILE_MAX_BYTES = 10 * 1024 * 1024  # 10MB
LOG_FILE_BACKUP_COUNT = 5

# MT5 Trading Configuration
TIMEFRAME_MAP: Dict[str, int] = {
    "M1": 1,
    "M5": 5,
    "M15": 15,
    "M30": 30,
    "H1": 60,
    "H4": 240,
    "D1": 1440,
    "W1": 10080,
    "MN1": 43200
}

# Trading Parameters
RISK_PER_TRADE = 0.02  # 2% risk per trade
MAX_OPEN_TRADES = 3  # Maximum number of open trades
STOP_LOSS_PIPS = 50  # Default stop loss in pips
TAKE_PROFIT_PIPS = 100  # Default take profit in pips
MAX_SLIPPAGE_POINTS = 3  # Maximum allowed slippage in points
MAX_SPREAD_POINTS = 10  # Maximum allowed spread in points
MAX_VOLUME = 10.0  # Maximum trade volume
MIN_VOLUME = 0.01  # Minimum trade volume
VOLUME_STEP = 0.01  # Volume step size

# Backtesting Configuration
BACKTEST_START_DATE = "2024-01-01"  # Default backtest start date
BACKTEST_END_DATE = "2024-12-31"  # Default backtest end date
INITIAL_BALANCE = 10000  # Initial balance for backtesting
COMMISSION_RATE = 0.0001  # Commission rate per trade

# Strategy Parameters
TREND_MA_PERIOD = 200
SIGNAL_MA_PERIOD = 50
RSI_PERIOD = 14
RSI_OVERBOUGHT = 70
RSI_OVERSOLD = 30
MACD_FAST = 12
MACD_SLOW = 26
MACD_SIGNAL = 9

# Database Configuration
DB_POOL_SIZE = 5
DB_MAX_OVERFLOW = 10
DB_TIMEOUT = 30  # seconds

# API Rate Limits
MAX_REQUESTS_PER_MINUTE = 60
MAX_REQUESTS_PER_HOUR = 1000
REQUEST_TIMEOUT = 30  # seconds

# Error Handling
MAX_RETRY_ATTEMPTS = 3
RETRY_DELAY = 5  # seconds
ERROR_COOLDOWN = 300  # 5 minutes

# Performance Optimization
CACHE_TTL = 300  # 5 minutes
BATCH_SIZE = 1000
MAX_WORKERS = 4

# Notification Settings
TELEGRAM_MESSAGE_LENGTH = 4096
EMAIL_RETRY_COUNT = 3
NOTIFICATION_COOLDOWN = 300  # 5 minutes 