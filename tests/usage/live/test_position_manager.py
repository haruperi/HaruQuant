import logging
import unittest
from unittest.mock import MagicMock, patch
import sys
import os

# Adjust path to allow imports if running as script from root or tests folder
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "../../../")))

# Mock MetaTrader5 module globally before importing modules that depend on it
sys.modules["MetaTrader5"] = MagicMock()

from apps.live.position_manager import PositionManager
from apps.trading import OrderType

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("test_position_manager")

class TestPositionManager(unittest.TestCase):
    def setUp(self):
        self.mock_client = MagicMock()
        self.magic_number = 123456
        
        # Patch MT5TradeProvider inside PositionManager to avoid needing real initialization
        with patch('apps.live.position_manager.MT5TradeProvider'), \
             patch('apps.live.position_manager.Trade'):
            self.manager = PositionManager(self.mock_client, self.magic_number)
        
        # Mock the internal Trade instance
        self.manager.trade = MagicMock()

    def test_refresh_positions(self):
        # Setup mock return values
        mock_positions = [
            {"ticket": 1, "magic": 123456, "type": 0, "symbol": "EURUSD", "volume": 0.1},
            {"ticket": 2, "magic": 123456, "type": 1, "symbol": "GBPUSD", "volume": 0.2},
            {"ticket": 3, "magic": 999999, "type": 0, "symbol": "USDJPY", "volume": 0.1}, # Different magic
        ]
        self.mock_client.get_positions.return_value = mock_positions
        
        # Execute
        self.manager.refresh_positions()
        
        # Verify
        self.assertEqual(self.manager.total_positions(), 2)
        self.assertEqual(len(self.manager.get_positions_by_type("buy")), 1)
        self.assertEqual(len(self.manager.get_positions_by_type("sell")), 1)
        self.assertTrue(self.manager.has_position_for_symbol("EURUSD"))
        self.assertFalse(self.manager.has_position_for_symbol("USDJPY")) # Filtered out (wrong magic)
        
    def test_close_position(self):
        # Setup position
        mock_pos = {"ticket": 100, "magic": 123456, "type": 0, "symbol": "EURUSD"}
        self.manager._positions = [mock_pos]
        
        # Mock trade success
        self.manager.trade.position_close.return_value = True
        
        # Execute
        result = self.manager.close_position(100)
        
        # Verify
        self.assertTrue(result)
        self.manager.trade.position_close.assert_called_with(symbol="EURUSD", ticket=100)
        
    def test_close_all_positions(self):
        # Setup positions
        positions = [
            {"ticket": 1, "magic": 123456, "type": 0, "symbol": "EURUSD"}, # Buy
            {"ticket": 2, "magic": 123456, "type": 1, "symbol": "GBPUSD"}, # Sell
        ]
        # Mock refresh to return these positions
        self.mock_client.get_positions.return_value = positions
        
        self.manager.trade.position_close.return_value = True
        
        # Execute close all
        count = self.manager.close_all_positions()
        
        # Verify
        self.assertEqual(count, 2)
        self.assertEqual(self.manager.trade.position_close.call_count, 2)
        
    def test_close_filtered(self):
        # Setup positions
        positions = [
            {"ticket": 1, "magic": 123456, "type": 0, "symbol": "EURUSD"}, # Buy
            {"ticket": 2, "magic": 123456, "type": 1, "symbol": "GBPUSD"}, # Sell
        ]
        self.mock_client.get_positions.return_value = positions
        
        self.manager.trade.position_close.return_value = True
        
        # Execute close buys
        count = self.manager.close_all_positions(position_type="buy")
        
        # Verify
        self.assertEqual(count, 1) # Only 1 buy
        # Should have called close for ticket 1 only
        self.manager.trade.position_close.assert_called_with(symbol="EURUSD", ticket=1)

if __name__ == '__main__':
    unittest.main()
