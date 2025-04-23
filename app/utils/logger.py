"""
System-wide logging service implementation.
This module provides a centralized logging service for the entire application.
"""

import logging
import logging.handlers
import os
from pathlib import Path
from typing import Optional
from datetime import datetime
import atexit

# Constants for logging configuration
DEFAULT_LOG_FORMAT = '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
DEFAULT_LOG_LEVEL = logging.INFO
DEFAULT_LOG_DIR = 'logs'
MAX_LOG_FILE_SIZE = 10 * 1024 * 1024  # 10MB
BACKUP_COUNT = 5

# Store handlers to ensure proper cleanup
_log_handlers = []

def _cleanup_handlers():
    """Clean up all log handlers."""
    for handler in _log_handlers:
        handler.close()
    _log_handlers.clear()

# Register cleanup function
atexit.register(_cleanup_handlers)

def get_logger(name: str, 
               log_level: Optional[int] = None,
               log_format: Optional[str] = None,
               log_dir: Optional[str] = None) -> logging.Logger:
    """
    Get or create a logger with the specified configuration.
    
    Args:
        name: The name of the logger (typically __name__)
        log_level: The logging level (default: DEFAULT_LOG_LEVEL)
        log_format: The log message format (default: DEFAULT_LOG_FORMAT)
        log_dir: Directory to store log files (default: DEFAULT_LOG_DIR)
    
    Returns:
        logging.Logger: Configured logger instance
    """
    # Create logger
    logger = logging.getLogger(name)
    
    # Return existing logger if already configured
    if logger.handlers:
        return logger
    
    # Set log level
    logger.setLevel(log_level or DEFAULT_LOG_LEVEL)
    
    # Create log directory if it doesn't exist
    log_dir = log_dir or DEFAULT_LOG_DIR
    os.makedirs(log_dir, exist_ok=True)
    
    # Create file handler
    log_file = Path(log_dir) / f"{name.replace('.', '_')}_{datetime.now().strftime('%Y%m%d')}.log"
    file_handler = logging.handlers.RotatingFileHandler(
        log_file,
        maxBytes=MAX_LOG_FILE_SIZE,
        backupCount=BACKUP_COUNT
    )
    
    # Create console handler
    console_handler = logging.StreamHandler()
    
    # Set formatter
    formatter = logging.Formatter(log_format or DEFAULT_LOG_FORMAT)
    file_handler.setFormatter(formatter)
    console_handler.setFormatter(formatter)
    
    # Add handlers to logger
    logger.addHandler(file_handler)
    logger.addHandler(console_handler)
    
    # Store handlers for cleanup
    _log_handlers.extend([file_handler, console_handler])
    
    return logger

def setup_root_logger(log_level: Optional[int] = None,
                     log_format: Optional[str] = None,
                     log_dir: Optional[str] = None) -> None:
    """
    Set up the root logger with the specified configuration.
    
    Args:
        log_level: The logging level (default: DEFAULT_LOG_LEVEL)
        log_format: The log message format (default: DEFAULT_LOG_FORMAT)
        log_dir: Directory to store log files (default: DEFAULT_LOG_DIR)
    """
    root_logger = get_logger('root', log_level, log_format, log_dir)
    root_logger.setLevel(log_level or DEFAULT_LOG_LEVEL)  # Ensure root logger level is set correctly
    root_logger.info("Root logger initialized")

# Example usage:
# from app.utils.logger import get_logger
# logger = get_logger(__name__)
# logger.info("This is an info message")
# logger.error("This is an error message", exc_info=True) 