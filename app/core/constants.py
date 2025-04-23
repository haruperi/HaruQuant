"""
System-wide constants and configuration
"""

from enum import Enum
from pathlib import Path

# Project paths
PROJECT_ROOT = Path(__file__).parent.parent.parent
DATA_DIR = PROJECT_ROOT / "data"
LOGS_DIR = PROJECT_ROOT / "logs"
CONFIG_DIR = PROJECT_ROOT / "config"

# Timeframes
class Timeframe(Enum):
    M1 = 1
    M5 = 5
    M15 = 15
    M30 = 30
    H1 = 60
    H4 = 240
    D1 = 1440
    W1 = 10080
    MN1 = 43200

# Order types
class OrderType(Enum):
    MARKET = "MARKET"
    LIMIT = "LIMIT"
    STOP = "STOP"
    STOP_LIMIT = "STOP_LIMIT"

# Order sides
class OrderSide(Enum):
    BUY = "BUY"
    SELL = "SELL"

# Position status
class PositionStatus(Enum):
    OPEN = "OPEN"
    CLOSED = "CLOSED"
    PENDING = "PENDING"

# Default values
DEFAULT_TIMEFRAME = Timeframe.M15
DEFAULT_SYMBOL = "EURUSD"
DEFAULT_RISK_PER_TRADE = 0.02  # 2%
DEFAULT_MAX_OPEN_POSITIONS = 5

# Logging
LOG_LEVEL = "INFO"
LOG_FORMAT = "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
LOG_FILE = LOGS_DIR / "haruquant.log"

# API endpoints
DASHBOARD_HOST = "0.0.0.0"
DASHBOARD_PORT = 8000

# MT5
MT5_PATH = r"C:\Program Files\MetaTrader 5\terminal64.exe"
MT5_TIMEOUT = 10000  # milliseconds
MT5_RETRY_DELAY = 5  # seconds
MT5_MAX_RETRIES = 3 