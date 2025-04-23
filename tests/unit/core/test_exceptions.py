"""
Unit tests for error handling framework.
"""

import unittest
from unittest.mock import patch, MagicMock
import logging

from app.core.exceptions import (
    ErrorCode,
    ErrorContext,
    HaruQuantError,
    ConfigurationError,
    MT5Error,
    ConnectionError,
    handle_errors,
    log_error,
    create_error_response
)

class TestErrorHandling(unittest.TestCase):
    """Test cases for error handling framework."""
    
    def test_error_context(self):
        """Test ErrorContext initialization and attributes."""
        context = ErrorContext(
            error_code=ErrorCode.INVALID_CONFIGURATION,
            message="Test error",
            details={'key': 'value'},
            original_error=ValueError("Original error")
        )
        
        self.assertEqual(context.error_code, ErrorCode.INVALID_CONFIGURATION)
        self.assertEqual(context.message, "Test error")
        self.assertEqual(context.details, {'key': 'value'})
        self.assertIsInstance(context.original_error, ValueError)
        self.assertIsNotNone(context.traceback)
        
    def test_haru_quant_error(self):
        """Test HaruQuantError initialization and string representation."""
        error = HaruQuantError(
            message="Test error",
            error_code=ErrorCode.UNKNOWN,
            details={'key': 'value'}
        )
        
        self.assertEqual(str(error), "UNKNOWN: Test error")
        self.assertEqual(error.context.details, {'key': 'value'})
        
    def test_specific_errors(self):
        """Test specific error types."""
        # Test ConfigurationError
        config_error = ConfigurationError("Config error")
        self.assertEqual(config_error.context.error_code, ErrorCode.INVALID_CONFIGURATION)
        
        # Test ConnectionError
        conn_error = ConnectionError("Connection error")
        self.assertEqual(conn_error.context.error_code, ErrorCode.MT5_CONNECTION_ERROR)
        
    @patch('app.core.exceptions.logger')
    def test_handle_errors_decorator(self, mock_logger):
        """Test handle_errors decorator."""
        error_map = {
            ValueError: ConfigurationError,
            ConnectionError: MT5Error
        }
        
        @handle_errors(error_map)
        def test_function(raise_error=True):
            if raise_error:
                raise ValueError("Test error")
            return "Success"
            
        # Test successful execution
        self.assertEqual(test_function(raise_error=False), "Success")
        
        # Test error handling
        with self.assertRaises(ConfigurationError) as cm:
            test_function(raise_error=True)
            
        error = cm.exception
        self.assertEqual(error.context.error_code, ErrorCode.INVALID_CONFIGURATION)
        self.assertTrue(mock_logger.log.called)
        
    @patch('app.core.exceptions.logger')
    def test_log_error(self, mock_logger):
        """Test error logging function."""
        error = HaruQuantError(
            message="Test error",
            error_code=ErrorCode.UNKNOWN,
            details={'key': 'value'}
        )
        
        log_error(error, log_level=logging.WARNING)
        
        mock_logger.log.assert_called_once_with(
            logging.WARNING,
            "UNKNOWN: Test error",
            exc_info=True,
            extra={
                'error_code': 'UNKNOWN',
                'details': {'key': 'value'}
            }
        )
        
    def test_create_error_response(self):
        """Test error response creation."""
        error = HaruQuantError(
            message="Test error",
            error_code=ErrorCode.UNKNOWN,
            details={'key': 'value'}
        )
        
        response = create_error_response(error)
        
        self.assertEqual(response, {
            'error_code': 'UNKNOWN',
            'message': 'Test error',
            'details': {'key': 'value'}
        })
        
    def test_error_inheritance(self):
        """Test error class inheritance relationships."""
        # Test that MT5Error inherits from HaruQuantError
        self.assertTrue(issubclass(MT5Error, HaruQuantError))
        
        # Test that ConnectionError inherits from MT5Error
        self.assertTrue(issubclass(ConnectionError, MT5Error))
        
    def test_error_code_values(self):
        """Test error code enumeration values."""
        # Test general error codes
        self.assertEqual(ErrorCode.UNKNOWN.value, 1)
        self.assertEqual(ErrorCode.INVALID_CONFIGURATION.value, 2)
        
        # Test MT5 error codes
        self.assertEqual(ErrorCode.MT5_CONNECTION_ERROR.value, 100)
        self.assertEqual(ErrorCode.MT5_AUTHENTICATION_ERROR.value, 101)
        
        # Test trading error codes
        self.assertEqual(ErrorCode.INSUFFICIENT_MARGIN.value, 200)
        self.assertEqual(ErrorCode.INVALID_ORDER.value, 201) 