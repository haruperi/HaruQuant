"""
Simple integration test for MT5 connection.
"""

import unittest
import MetaTrader5 as mt5
from pathlib import Path
import time
from app.mt5.mt5_client import MT5Client
from app.utils.logger import get_logger

logger = get_logger(__name__)

class TestMT5Connection(unittest.TestCase):
    """Test cases for basic MT5 connection."""
    
    @classmethod
    def setUpClass(cls):
        """Set up test environment."""
        # Skip tests if config.ini doesn't exist
        if not Path('config.ini').exists():
            raise unittest.SkipTest("config.ini not found")
    
    def setUp(self):
        """Set up test case."""
        self.client = MT5Client()
    
    def tearDown(self):
        """Clean up after test."""
        if hasattr(self, 'client'):
            self.client.disconnect()
    
    def test_mt5_initialization(self):
        """Test MT5 initialization."""
        # Initialize MT5
        self.client._initialize()
        self.assertTrue(self.client._initialized)
        logger.info("MT5 initialized successfully")
    
    def test_terminal_info(self):
        """Test terminal info retrieval."""
        # Initialize MT5 first
        self.client._initialize()
        
        # Get terminal info
        terminal_info = mt5.terminal_info()
        self.assertIsNotNone(terminal_info)
        logger.info(f"Terminal info: {terminal_info}")
        
        # Verify key terminal properties
        self.assertTrue(terminal_info.connected)
        self.assertTrue(terminal_info.trade_allowed)
        self.assertEqual(terminal_info.company, "Pepperstone Group Limited")
        self.assertEqual(terminal_info.name, "Pepperstone MetaTrader 5")
    
    def test_account_info(self):
        """Test account info retrieval."""
        # Initialize MT5 first
        self.client._initialize()
        
        # Get account info
        account_info = mt5.account_info()
        self.assertIsNotNone(account_info)
        logger.info(f"Account info: {account_info}")
        
        # Verify key account properties
        self.assertEqual(account_info.login, 61344744)
        self.assertEqual(account_info.server, "Pepperstone-Demo")
        self.assertTrue(account_info.trade_allowed)
        self.assertEqual(account_info.currency, "USD")
        self.assertGreater(account_info.balance, 0)
    
    def test_connection_state(self):
        """Test connection state tracking."""
        # Test initial state
        self.assertFalse(self.client._initialized)
        self.assertFalse(self.client._connected)
        
        # Test after initialization
        self.client._initialize()
        self.assertTrue(self.client._initialized)
        self.assertTrue(self.client._connected)
        
        # Test after disconnect
        self.client.disconnect()
        self.assertFalse(self.client._initialized)
        self.assertFalse(self.client._connected)
    
    def test_login_successful(self):
        """Test successful login verification."""
        # Initialize MT5
        self.client._initialize()
        
        # Get account info to verify login
        account_info = mt5.account_info()
        self.assertIsNotNone(account_info)
        
        # Verify login was successful
        self.assertTrue(account_info.trade_allowed)
        self.assertTrue(account_info.trade_expert)
        self.assertEqual(account_info.login, 61344744)
        self.assertEqual(account_info.server, "Pepperstone-Demo")
        self.assertEqual(account_info.currency, "USD")
        
        # Log successful login details
        logger.info(f"Successfully logged in as {account_info.name}")
        logger.info(f"Account balance: {account_info.balance} {account_info.currency}")
        logger.info(f"Leverage: {account_info.leverage}")
    
    def test_connection_stability(self):
        """Test connection stability over time."""
        # Initialize MT5
        self.client._initialize()
        
        # Test connection stability for 30 seconds
        start_time = time.time()
        test_duration = 30  # seconds
        check_interval = 5  # seconds
        
        while time.time() - start_time < test_duration:
            # Check terminal connection
            terminal_info = mt5.terminal_info()
            self.assertTrue(terminal_info.connected, "Terminal connection lost")
            
            # Check account connection
            account_info = mt5.account_info()
            self.assertIsNotNone(account_info, "Account connection lost")
            
            # Log connection status
            logger.info(f"Connection stable for {int(time.time() - start_time)} seconds")
            logger.info(f"Ping: {terminal_info.ping_last}ms")
            
            # Wait for next check
            time.sleep(check_interval)
        
        logger.info("Connection stability test completed successfully") 