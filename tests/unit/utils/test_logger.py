"""
Unit tests for the logger module.
"""

import os
import logging
import tempfile
from pathlib import Path
import pytest
from app.utils.logger import get_logger, setup_root_logger, _cleanup_handlers

@pytest.fixture
def temp_log_dir():
    """Create a temporary directory for log files."""
    with tempfile.TemporaryDirectory() as temp_dir:
        yield temp_dir
        # Clean up any remaining log files
        _cleanup_handlers()

@pytest.fixture(autouse=True)
def reset_logging():
    """Reset logging configuration before each test."""
    root_logger = logging.getLogger()
    for handler in root_logger.handlers[:]:
        root_logger.removeHandler(handler)
    yield
    # Cleanup after test
    for handler in root_logger.handlers[:]:
        root_logger.removeHandler(handler)

def test_get_logger_creation(temp_log_dir):
    """Test logger creation with custom configuration."""
    logger = get_logger('test_logger', 
                       log_level=logging.DEBUG,
                       log_dir=temp_log_dir)
    
    assert logger.name == 'test_logger'
    assert logger.level == logging.DEBUG
    assert len(logger.handlers) == 2  # File and console handlers

def test_logger_reuse():
    """Test that the same logger instance is returned for the same name."""
    logger1 = get_logger('test_reuse')
    logger2 = get_logger('test_reuse')
    
    assert logger1 is logger2

def test_log_file_creation(temp_log_dir):
    """Test that log files are created in the specified directory."""
    logger = get_logger('test_file', log_dir=temp_log_dir)
    logger.info("Test message")
    
    log_files = list(Path(temp_log_dir).glob('*.log'))
    assert len(log_files) == 1
    assert log_files[0].name.startswith('test_file_')

def test_root_logger_setup(temp_log_dir):
    """Test root logger setup."""
    setup_root_logger(log_level=logging.INFO, log_dir=temp_log_dir)
    root_logger = logging.getLogger('root')
    
    assert root_logger.level == logging.INFO
    # Count only our handlers (file and console), not pytest's
    our_handlers = [h for h in root_logger.handlers if isinstance(h, (logging.FileHandler, logging.StreamHandler))]
    assert len(our_handlers) == 2

def test_log_levels(temp_log_dir):
    """Test different log levels."""
    logger = get_logger('test_levels', log_level=logging.DEBUG, log_dir=temp_log_dir)
    
    logger.debug("Debug message")
    logger.info("Info message")
    logger.warning("Warning message")
    logger.error("Error message")
    logger.critical("Critical message")
    
    # Verify log file contains messages
    log_file = next(Path(temp_log_dir).glob('*.log'))
    with open(log_file) as f:
        content = f.read()
        assert "Debug message" in content
        assert "Info message" in content
        assert "Warning message" in content
        assert "Error message" in content
        assert "Critical message" in content 