"""
Unit tests for crash recovery mechanisms.
"""

import json
import os
import signal
import sys
import tempfile
import unittest
from datetime import datetime, timedelta
from pathlib import Path
from unittest.mock import patch, MagicMock

from app.core.crash_recovery import BotState, CrashRecovery

class TestBotState(unittest.TestCase):
    """Test BotState class."""
    
    def setUp(self):
        """Set up test environment."""
        self.temp_dir = tempfile.mkdtemp()
        self.state_file = Path(self.temp_dir) / "bot_state.json"
        self.bot_state = BotState(str(self.state_file))
        
    def tearDown(self):
        """Clean up test environment."""
        if self.state_file.exists():
            os.remove(self.state_file)
        os.rmdir(self.temp_dir)
        
    def test_initial_state(self):
        """Test initial state creation."""
        expected_state = {
            'last_start_time': None,
            'last_stop_time': None,
            'crash_count': 0,
            'last_crash_time': None,
            'last_crash_reason': None,
            'last_known_state': None
        }
        self.assertEqual(self.bot_state.state, expected_state)
        
    def test_update_state(self):
        """Test state updates."""
        self.bot_state.update_state('test_key', 'test_value')
        self.assertEqual(self.bot_state.state['test_key'], 'test_value')
        
        # Verify file was written
        with open(self.state_file, 'r') as f:
            saved_state = json.load(f)
        self.assertEqual(saved_state['test_key'], 'test_value')
        
    def test_record_crash(self):
        """Test crash recording."""
        self.bot_state.record_crash("Test crash")
        self.assertEqual(self.bot_state.state['crash_count'], 1)
        self.assertIsNotNone(self.bot_state.state['last_crash_time'])
        self.assertEqual(self.bot_state.state['last_crash_reason'], "Test crash")
        
    def test_should_restart_no_crashes(self):
        """Test restart decision with no crashes."""
        self.assertTrue(self.bot_state.should_restart())
        
    def test_should_restart_within_window(self):
        """Test restart decision within crash window."""
        self.bot_state.record_crash("Test crash")
        self.assertTrue(self.bot_state.should_restart(max_crashes=3))
        self.assertFalse(self.bot_state.should_restart(max_crashes=0))
        
    def test_should_restart_outside_window(self):
        """Test restart decision outside crash window."""
        self.bot_state.record_crash("Test crash")
        self.bot_state.state['last_crash_time'] = (
            datetime.now() - timedelta(hours=25)
        ).isoformat()
        self.assertTrue(self.bot_state.should_restart(crash_window_hours=24))
        
class TestCrashRecovery(unittest.TestCase):
    """Test CrashRecovery class."""
    
    def setUp(self):
        """Set up test environment."""
        self.bot_state = MagicMock(spec=BotState)
        self.crash_recovery = CrashRecovery(self.bot_state)
        
    def test_setup_signal_handlers(self):
        """Test signal handler setup."""
        with patch('signal.signal') as mock_signal:
            self.crash_recovery.setup_signal_handlers()
            self.assertEqual(mock_signal.call_count, 2)
            mock_signal.assert_any_call(signal.SIGINT, unittest.mock.ANY)
            mock_signal.assert_any_call(signal.SIGTERM, unittest.mock.ANY)
            
    def test_restore_signal_handlers(self):
        """Test signal handler restoration."""
        self.crash_recovery.original_sigint = MagicMock()
        self.crash_recovery.original_sigterm = MagicMock()
        
        with patch('signal.signal') as mock_signal:
            self.crash_recovery.restore_signal_handlers()
            self.assertEqual(mock_signal.call_count, 2)
            mock_signal.assert_any_call(signal.SIGINT, 
                                      self.crash_recovery.original_sigint)
            mock_signal.assert_any_call(signal.SIGTERM, 
                                      self.crash_recovery.original_sigterm)
            
    def test_handle_crash(self):
        """Test crash handling."""
        exception = Exception("Test exception")
        self.crash_recovery.handle_crash(exception)
        self.bot_state.record_crash.assert_called_once_with(str(exception))
        
    def test_should_restart(self):
        """Test restart decision."""
        self.bot_state.should_restart.return_value = True
        self.assertTrue(self.crash_recovery.should_restart())
        self.bot_state.should_restart.assert_called_once()
        
    def test_cleanup(self):
        """Test cleanup."""
        with patch.object(self.crash_recovery, 'restore_signal_handlers') as mock_restore:
            self.crash_recovery.cleanup()
            mock_restore.assert_called_once()
            self.bot_state.update_state.assert_called_once_with(
                'last_stop_time', unittest.mock.ANY
            ) 