"""
Unit tests for MT5 client.
"""

import unittest
from unittest.mock import patch, MagicMock, PropertyMock
from pathlib import Path

import MetaTrader5 as mt5

from app.mt5.client import MT5Client, MT5Error

class TestMT5Client(unittest.TestCase):
    """Test cases for MT5Client."""
    
    def setUp(self):
        """Set up test environment."""
        self.terminal_path = "C:/Program Files/Pepperstone MetaTrader 5/terminal64.exe"
        self.server = "Pepperstone-Demo"
        self.login = 61344744
        self.password = "uy+reDvhs1"
        self.client = MT5Client(
            terminal_path=self.terminal_path,
            server=self.server,
            login=self.login,
            password=self.password
        )
        
    @patch('MetaTrader5.initialize')
    def test_initialization(self, mock_initialize):
        """Test MT5 initialization."""
        # Test successful initialization
        mock_initialize.return_value = True
        self.client.initialize()
        mock_initialize.assert_called_once_with(
            path=self.terminal_path,
            login=self.login,
            server=self.server,
            password=self.password
        )

        # Test failed initialization
        mock_initialize.reset_mock()
        mock_initialize.return_value = False
        with self.assertRaises(MT5Error):
            self.client.initialize()

        # Test missing terminal
        mock_initialize.reset_mock()
        mock_initialize.side_effect = Exception("Terminal not found")
        with self.assertRaises(MT5Error):
            self.client.initialize()
        
    @patch('MetaTrader5.login')
    def test_login(self, mock_login):
        """Test MT5 login."""
        # Test successful login
        mock_login.return_value = True
        self.client.login()
        mock_login.assert_called_once_with(
            login=self.login,
            password=self.password,
            server=self.server
        )

        # Test failed login
        mock_login.reset_mock()
        mock_login.return_value = False
        with self.assertRaises(MT5Error):
            self.client.login()
        
    @patch('MetaTrader5.terminal_info')
    def test_connection_status(self, mock_terminal_info):
        """Test connection status checking."""
        # Test connected
        mock_terminal_info.return_value = MagicMock(connected=True)
        self.assertTrue(self.client.is_connected())

        # Test not connected
        mock_terminal_info.return_value = MagicMock(connected=False)
        self.assertFalse(self.client.is_connected())
        
    @patch('MetaTrader5.shutdown')
    def test_disconnect(self, mock_shutdown):
        """Test MT5 disconnection."""
        self.client.disconnect()
        mock_shutdown.assert_called_once()
        self.assertFalse(self.client._initialized)
        
    @patch('MetaTrader5.initialize')
    @patch('MetaTrader5.shutdown')
    def test_context_manager(self, mock_shutdown, mock_initialize):
        """Test context manager functionality."""
        mock_initialize.return_value = True
        with self.client:
            mock_initialize.assert_called_once()
        mock_shutdown.assert_called_once()
        
    @patch('MetaTrader5.account_info')
    def test_get_account_info(self, mock_account_info):
        """Test getting account information."""
        # Test successful retrieval
        expected_info = MagicMock(
            login=self.login,
            server=self.server,
            balance=10000.0,
            equity=10000.0
        )
        mock_account_info.return_value = expected_info
        account_info = self.client.get_account_info()
        self.assertEqual(account_info, expected_info)

        # Test failed retrieval
        mock_account_info.return_value = None
        with self.assertRaises(MT5Error):
            self.client.get_account_info()
        
    @patch('MetaTrader5.terminal_info')
    def test_get_terminal_info(self, mock_terminal_info):
        """Test getting terminal information."""
        # Test successful retrieval
        expected_info = MagicMock(
            path=self.terminal_path,
            connected=True,
            dlls_allowed=True,
            trade_allowed=True,
            tradeapi_disabled=False
        )
        mock_terminal_info.return_value = expected_info
        terminal_info = self.client.get_terminal_info()
        self.assertEqual(terminal_info, expected_info)

        # Test failed retrieval
        mock_terminal_info.return_value = None
        with self.assertRaises(MT5Error):
            self.client.get_terminal_info()

if __name__ == '__main__':
    unittest.main() 