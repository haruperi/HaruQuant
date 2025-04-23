"""
Custom exception classes and error handling utilities for the trading bot.

This module provides a comprehensive error handling framework including:
- Base exception classes
- Specific error types for different components
- Error codes and messages
- Error handling utilities
"""

from enum import Enum
from typing import Optional, Dict, Any, Type
from functools import wraps
import logging
import traceback

from app.utils.logger import get_logger

logger = get_logger(__name__)

class ErrorCode(Enum):
    """Error codes for different types of errors."""
    # General errors (1-99)
    UNKNOWN = 1
    INVALID_CONFIGURATION = 2
    INITIALIZATION_ERROR = 3
    VALIDATION_ERROR = 4
    
    # MT5 errors (100-199)
    MT5_CONNECTION_ERROR = 100
    MT5_AUTHENTICATION_ERROR = 101
    MT5_DATA_ERROR = 102
    MT5_ORDER_ERROR = 103
    
    # Trading errors (200-299)
    INSUFFICIENT_MARGIN = 200
    INVALID_ORDER = 201
    POSITION_NOT_FOUND = 202
    RISK_LIMIT_EXCEEDED = 203
    
    # Strategy errors (300-399)
    INVALID_STRATEGY = 300
    STRATEGY_EXECUTION_ERROR = 301
    SIGNAL_ERROR = 302
    
    # Data errors (400-499)
    INVALID_DATA = 400
    DATA_NOT_FOUND = 401
    DATA_PROCESSING_ERROR = 402
    
    # Database errors (500-599)
    DB_CONNECTION_ERROR = 500
    DB_QUERY_ERROR = 501
    DB_INTEGRITY_ERROR = 502

class ErrorContext:
    """Context information for errors."""
    
    def __init__(self, 
                 error_code: ErrorCode,
                 message: str,
                 details: Optional[Dict[str, Any]] = None,
                 original_error: Optional[Exception] = None):
        """
        Initialize error context.
        
        Args:
            error_code: Specific error code
            message: Error message
            details: Additional error details
            original_error: Original exception if any
        """
        self.error_code = error_code
        self.message = message
        self.details = details or {}
        self.original_error = original_error
        self.traceback = traceback.format_exc() if original_error else None

class HaruQuantError(Exception):
    """Base exception class for HaruQuant."""
    
    def __init__(self, 
                 message: str,
                 error_code: ErrorCode = ErrorCode.UNKNOWN,
                 details: Optional[Dict[str, Any]] = None,
                 original_error: Optional[Exception] = None):
        """
        Initialize base exception.
        
        Args:
            message: Error message
            error_code: Specific error code
            details: Additional error details
            original_error: Original exception if any
        """
        super().__init__(message)
        self.context = ErrorContext(
            error_code=error_code,
            message=message,
            details=details,
            original_error=original_error
        )
        
    def __str__(self) -> str:
        """Return string representation of the error."""
        return f"{self.context.error_code.name}: {self.context.message}"

class ConfigurationError(HaruQuantError):
    """Raised when there is a configuration error."""
    def __init__(self, message: str, **kwargs):
        super().__init__(message, error_code=ErrorCode.INVALID_CONFIGURATION, **kwargs)

class MT5Error(HaruQuantError):
    """Base class for MT5-related errors."""
    pass

class ConnectionError(MT5Error):
    """Raised when there is a connection error with MT5."""
    def __init__(self, message: str, **kwargs):
        super().__init__(message, error_code=ErrorCode.MT5_CONNECTION_ERROR, **kwargs)

class AuthenticationError(MT5Error):
    """Raised when there is an authentication error with MT5."""
    def __init__(self, message: str, **kwargs):
        super().__init__(message, error_code=ErrorCode.MT5_AUTHENTICATION_ERROR, **kwargs)

class DataError(HaruQuantError):
    """Raised when there is a data-related error."""
    def __init__(self, message: str, **kwargs):
        super().__init__(message, error_code=ErrorCode.INVALID_DATA, **kwargs)

class TradingError(HaruQuantError):
    """Base class for trading-related errors."""
    pass

class OrderError(TradingError):
    """Raised when there is an order-related error."""
    def __init__(self, message: str, **kwargs):
        super().__init__(message, error_code=ErrorCode.INVALID_ORDER, **kwargs)

class RiskError(TradingError):
    """Raised when there is a risk management error."""
    def __init__(self, message: str, **kwargs):
        super().__init__(message, error_code=ErrorCode.RISK_LIMIT_EXCEEDED, **kwargs)

class StrategyError(HaruQuantError):
    """Raised when there is a strategy-related error."""
    def __init__(self, message: str, **kwargs):
        super().__init__(message, error_code=ErrorCode.INVALID_STRATEGY, **kwargs)

class BacktestError(HaruQuantError):
    """Raised when there is a backtesting error."""
    def __init__(self, message: str, **kwargs):
        super().__init__(message, error_code=ErrorCode.STRATEGY_EXECUTION_ERROR, **kwargs)

class DatabaseError(HaruQuantError):
    """Raised when there is a database error."""
    def __init__(self, message: str, **kwargs):
        super().__init__(message, error_code=ErrorCode.DB_CONNECTION_ERROR, **kwargs)

class NotificationError(HaruQuantError):
    """Raised when there is a notification error."""
    def __init__(self, message: str, **kwargs):
        super().__init__(message, error_code=ErrorCode.UNKNOWN, **kwargs)

def handle_errors(error_map: Optional[Dict[Type[Exception], Type[HaruQuantError]]] = None,
                 reraise: bool = True,
                 log_level: int = logging.ERROR):
    """
    Decorator for handling exceptions and converting them to HaruQuant exceptions.
    
    Args:
        error_map: Mapping of external exceptions to HaruQuant exceptions
        reraise: Whether to reraise the exception after handling
        log_level: Logging level for the error
        
    Example:
        @handle_errors({
            ValueError: ConfigurationError,
            ConnectionError: MT5Error
        })
        def some_function():
            pass
    """
    error_map = error_map or {}
    
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            try:
                return func(*args, **kwargs)
            except Exception as e:
                # Get the appropriate error type
                error_type = error_map.get(type(e), HaruQuantError)
                
                # Create error details
                details = {
                    'function': func.__name__,
                    'args': str(args),
                    'kwargs': str(kwargs),
                    'error_type': type(e).__name__
                }
                
                # Create the error
                error = error_type(
                    str(e),
                    details=details,
                    original_error=e
                )
                
                # Log the error
                logger.log(log_level, str(error), exc_info=True,
                          extra={'error_code': error.context.error_code.name,
                                'details': error.context.details})
                
                if reraise:
                    raise error
                
        return wrapper
    return decorator

def log_error(error: HaruQuantError,
              log_level: int = logging.ERROR,
              include_traceback: bool = True) -> None:
    """
    Log an error with context information.
    
    Args:
        error: The error to log
        log_level: Logging level
        include_traceback: Whether to include traceback in the log
    """
    logger.log(log_level, str(error),
              exc_info=include_traceback,
              extra={'error_code': error.context.error_code.name,
                    'details': error.context.details})

def create_error_response(error: HaruQuantError) -> Dict[str, Any]:
    """
    Create a standardized error response dictionary.
    
    Args:
        error: The error to create response for
        
    Returns:
        Dictionary containing error information
    """
    return {
        'error_code': error.context.error_code.name,
        'message': error.context.message,
        'details': error.context.details
    } 