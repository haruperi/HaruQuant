"""
Custom exception classes for the trading bot
"""

class HaruQuantError(Exception):
    """Base exception class for HaruQuant."""
    pass

class ConfigurationError(HaruQuantError):
    """Raised when there is a configuration error."""
    pass

class MT5Error(HaruQuantError):
    """Raised when there is an MT5-related error."""
    pass

class ConnectionError(MT5Error):
    """Raised when there is a connection error with MT5."""
    pass

class AuthenticationError(MT5Error):
    """Raised when there is an authentication error with MT5."""
    pass

class DataError(HaruQuantError):
    """Raised when there is a data-related error."""
    pass

class TradingError(HaruQuantError):
    """Raised when there is a trading-related error."""
    pass

class OrderError(TradingError):
    """Raised when there is an order-related error."""
    pass

class RiskError(TradingError):
    """Raised when there is a risk management error."""
    pass

class StrategyError(HaruQuantError):
    """Raised when there is a strategy-related error."""
    pass

class BacktestError(HaruQuantError):
    """Raised when there is a backtesting error."""
    pass

class DatabaseError(HaruQuantError):
    """Raised when there is a database error."""
    pass

class NotificationError(HaruQuantError):
    """Raised when there is a notification error."""
    pass 